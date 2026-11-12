"""Differentially private, Ed25519-signed audit credentials."""

from __future__ import annotations

import base64
import hashlib
import json
import math
import re
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING, localcontext
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.exceptions import InvalidSignature


_DATASET_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_CATEGORY = re.compile(r"^[A-Za-z][A-Za-z0-9._:-]{0,63}$")
_BASE64URL = re.compile(r"^[A-Za-z0-9_-]+$")
_ED25519_MULTICODEC = b"\xed\x01"
_VC_CONTEXT = "https://www.w3.org/ns/credentials/v2"
_DEFAULT_MAX_EPSILON = 3.0


class PrivacyBudgetExceeded(ValueError):
    """Raised when issuing a credential would exceed a dataset's privacy budget."""


def ed25519_private_key_from_base64(encoded_key: str) -> Ed25519PrivateKey:
    if not isinstance(encoded_key, str) or not encoded_key:
        raise ValueError("The Ed25519 private key must be standard base64")
    try:
        raw_key = base64.b64decode(encoded_key, validate=True)
    except (ValueError, base64.binascii.Error) as error:
        raise ValueError("The Ed25519 private key must be standard base64") from error
    if len(raw_key) != 32:
        raise ValueError("The Ed25519 private key must decode to exactly 32 bytes")
    return Ed25519PrivateKey.from_private_bytes(raw_key)


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    if not isinstance(value, str) or not _BASE64URL.fullmatch(value):
        raise ValueError("Invalid base64url value")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _base58btc_encode(value: bytes) -> str:
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    leading_zeroes = len(value) - len(value.lstrip(b"\x00"))
    number = int.from_bytes(value, "big")
    encoded = ""
    while number:
        number, remainder = divmod(number, 58)
        encoded = alphabet[remainder] + encoded
    return "1" * leading_zeroes + encoded


def _base58btc_decode(value: str) -> bytes:
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    number = 0
    for character in value:
        try:
            digit = alphabet.index(character)
        except ValueError as error:
            raise ValueError("Invalid base58btc DID key") from error
        number = number * 58 + digit
    leading_zeroes = len(value) - len(value.lstrip("1"))
    payload = (
        number.to_bytes((number.bit_length() + 7) // 8, "big")
        if number
        else b""
    )
    return b"\x00" * leading_zeroes + payload


def did_key_from_public_key(public_key: Ed25519PublicKey) -> str:
    raw_public_key = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    fingerprint = _base58btc_encode(_ED25519_MULTICODEC + raw_public_key)
    return f"did:key:z{fingerprint}"


def did_key_document(did: str) -> dict[str, Any]:
    _public_key_from_did(did)
    fingerprint = did.removeprefix("did:key:")
    verification_method = f"{did}#{fingerprint}"
    return {
        "@context": [
            "https://www.w3.org/ns/did/v1",
            "https://w3id.org/security/suites/ed25519-2020/v1",
        ],
        "id": did,
        "verificationMethod": [
            {
                "id": verification_method,
                "type": "Ed25519VerificationKey2020",
                "controller": did,
                "publicKeyMultibase": fingerprint,
            }
        ],
        "authentication": [verification_method],
        "assertionMethod": [verification_method],
    }


def _public_key_from_did(did: str) -> Ed25519PublicKey:
    prefix = "did:key:z"
    if not did.startswith(prefix):
        raise ValueError("Only Ed25519 did:key identifiers are supported")
    decoded = _base58btc_decode(did[len(prefix) :])
    if len(decoded) != len(_ED25519_MULTICODEC) + 32:
        raise ValueError("Invalid Ed25519 did:key length")
    if not decoded.startswith(_ED25519_MULTICODEC):
        raise ValueError("DID key is not an Ed25519 public key")
    return Ed25519PublicKey.from_public_bytes(decoded[len(_ED25519_MULTICODEC) :])


def verify_credential_jwt(token: str) -> dict[str, Any]:
    """Verify a VC-JWT signature using the Ed25519 public key in its did:key issuer."""
    if not isinstance(token, str) or len(token) > 1_000_000:
        raise ValueError("Credential JWT must be a string no larger than 1 MB")
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Credential JWT must contain three compact JWS parts")
    header_bytes, payload_bytes, signature = (
        _base64url_decode(part) for part in parts
    )
    try:
        header = json.loads(header_bytes)
        payload = json.loads(payload_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Credential JWT contains invalid JSON") from error
    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise ValueError("Credential JWT header and payload must be JSON objects")
    if header.get("alg") != "EdDSA" or header.get("typ") != "vc+jwt":
        raise ValueError("Credential JWT must use the vc+jwt EdDSA profile")
    issuer = payload.get("iss")
    key_id = header.get("kid")
    credential = payload.get("vc")
    if (
        not isinstance(issuer, str)
        or not isinstance(key_id, str)
        or not isinstance(credential, dict)
        or credential.get("issuer") != issuer
    ):
        raise ValueError("Credential issuer and verification method do not match")
    fingerprint = issuer.removeprefix("did:key:")
    if key_id != f"{issuer}#{fingerprint}":
        raise ValueError("Credential issuer and verification method do not match")
    public_key = _public_key_from_did(issuer)
    signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
    try:
        public_key.verify(signature, signing_input)
    except InvalidSignature as error:
        raise ValueError("Credential signature verification failed") from error
    if (
        not isinstance(credential, dict)
        or not isinstance(credential.get("@context"), list)
        or _VC_CONTEXT not in credential["@context"]
        or not isinstance(credential.get("type"), list)
        or "VerifiableCredential" not in credential["type"]
    ):
        raise ValueError("Credential does not contain the supported W3C VC profile")
    return payload


class DifferentialPrivacyCredentialIssuer:
    """Issues VC-JWTs for subject-level differentially private category counts."""

    def __init__(
        self,
        *,
        database_path: str | Path,
        signing_key: Ed25519PrivateKey,
        max_epsilon: float = _DEFAULT_MAX_EPSILON,
    ) -> None:
        if not isinstance(signing_key, Ed25519PrivateKey):
            raise ValueError("signing_key must be an Ed25519 private key")
        if (
            not isinstance(max_epsilon, (int, float))
            or isinstance(max_epsilon, bool)
            or not math.isfinite(max_epsilon)
            or max_epsilon <= 0
            or max_epsilon > 100
        ):
            raise ValueError("max_epsilon must be greater than 0 and at most 100")
        self.database_path = str(Path(database_path).expanduser())
        if self.database_path == ":memory:":
            raise ValueError("The privacy budget requires a persistent SQLite file")
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self.signing_key = signing_key
        self.max_epsilon = float(max_epsilon)
        self.issuer_did = did_key_from_public_key(signing_key.public_key())
        self._initialize_budget_store()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def _initialize_budget_store(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS privacy_dataset_budgets (
                    dataset_key_sha256 TEXT PRIMARY KEY,
                    epsilon_spent TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _dataset_key(dataset_id: str) -> str:
        if not isinstance(dataset_id, str) or not _DATASET_ID.fullmatch(dataset_id):
            raise ValueError(
                "dataset_id must match [A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
            )
        return hashlib.sha256(
            b"sanctum-dp-dataset-v1\x00" + dataset_id.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _validate_categories(categories: list[str]) -> list[str]:
        if not isinstance(categories, list) or not 1 <= len(categories) <= 32:
            raise ValueError("categories must contain between 1 and 32 public labels")
        if any(
            not isinstance(category, str) or not _CATEGORY.fullmatch(category)
            for category in categories
        ):
            raise ValueError("categories must be structured public labels")
        if len(set(categories)) != len(categories):
            raise ValueError("categories must not contain duplicates")
        return sorted(categories)

    @staticmethod
    def _validate_observations(
        observations: list[dict[str, str]],
        categories: list[str],
    ) -> dict[str, int]:
        if not isinstance(observations, list) or len(observations) > 10_000:
            raise ValueError("observations must contain at most 10000 entries")
        allowed_categories = set(categories)
        seen_subjects: set[str] = set()
        counts = dict.fromkeys(categories, 0)
        for observation in observations:
            if not isinstance(observation, dict) or set(observation) != {
                "subject_id",
                "category",
            }:
                raise ValueError("each observation requires subject_id and category")
            subject_id = observation["subject_id"]
            category = observation["category"]
            if (
                not isinstance(subject_id, str)
                or not subject_id
                or len(subject_id) > 128
            ):
                raise ValueError("subject_id must contain between 1 and 128 characters")
            if subject_id in seen_subjects:
                raise ValueError("each subject may contribute at most one observation")
            if not isinstance(category, str) or category not in allowed_categories:
                raise ValueError("observation category must be in the public categories")
            seen_subjects.add(subject_id)
            counts[category] += 1
        return counts

    def _consume_budget(self, dataset_key: str, epsilon: float) -> float:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT epsilon_spent FROM privacy_dataset_budgets "
                "WHERE dataset_key_sha256 = ?",
                (dataset_key,),
            ).fetchone()
            spent = Decimal(str(row[0])) if row else Decimal(0)
            new_spent = spent + Decimal(str(epsilon))
            if new_spent > Decimal(str(self.max_epsilon)):
                connection.rollback()
                raise PrivacyBudgetExceeded(
                    "Issuing this credential would exceed the dataset privacy budget"
                )
            connection.execute(
                """
                INSERT INTO privacy_dataset_budgets (
                    dataset_key_sha256, epsilon_spent, updated_at
                ) VALUES (?, ?, ?)
                ON CONFLICT(dataset_key_sha256) DO UPDATE SET
                    epsilon_spent = excluded.epsilon_spent,
                    updated_at = excluded.updated_at
                """,
                (dataset_key, format(new_spent, "f"), now),
            )
            connection.commit()
        return float(new_spent)

    @staticmethod
    def _discrete_laplace_parameter(epsilon: float) -> tuple[int, int]:
        denominator = 1 << 64
        with localcontext() as context:
            context.prec = 80
            scaled_parameter = (-Decimal(str(epsilon))).exp() * denominator
            numerator = int(
                scaled_parameter.to_integral_value(rounding=ROUND_CEILING)
            ) + 1
        if numerator >= denominator:
            raise ValueError("epsilon is too small for the discrete noise sampler")
        return numerator, denominator

    @staticmethod
    def _geometric_noise(parameter_numerator: int, parameter_denominator: int) -> int:
        samples = 0
        while secrets.randbelow(parameter_denominator) < parameter_numerator:
            samples += 1
        return samples

    @classmethod
    def _discrete_laplace_noise(
        cls, parameter_numerator: int, parameter_denominator: int
    ) -> int:
        return cls._geometric_noise(
            parameter_numerator, parameter_denominator
        ) - cls._geometric_noise(parameter_numerator, parameter_denominator)

    def _sign(self, payload: dict[str, Any]) -> str:
        header = {
            "alg": "EdDSA",
            "kid": f"{self.issuer_did}#{self.issuer_did.removeprefix('did:key:')}",
            "typ": "vc+jwt",
        }
        encoded_header = _base64url_encode(
            json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
        )
        encoded_payload = _base64url_encode(
            json.dumps(
                payload,
                ensure_ascii=True,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        )
        signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
        signature = self.signing_key.sign(signing_input)
        return f"{encoded_header}.{encoded_payload}.{_base64url_encode(signature)}"

    def issue(
        self,
        *,
        dataset_id: str,
        observations: list[dict[str, str]],
        categories: list[str],
        epsilon: float,
    ) -> dict[str, Any]:
        if (
            not isinstance(epsilon, (int, float))
            or isinstance(epsilon, bool)
            or not math.isfinite(epsilon)
            or epsilon < 0.01
            or epsilon > 1
        ):
            raise ValueError("epsilon must be at least 0.01 and at most 1")

        dataset_key = self._dataset_key(dataset_id)
        normalized_categories = self._validate_categories(categories)
        true_counts = self._validate_observations(observations, normalized_categories)
        cumulative_epsilon = self._consume_budget(dataset_key, float(epsilon))
        noise_numerator, noise_denominator = self._discrete_laplace_parameter(
            float(epsilon)
        )

        noisy_counts = {
            category: max(
                0,
                count
                + self._discrete_laplace_noise(noise_numerator, noise_denominator),
            )
            for category, count in true_counts.items()
        }
        issued_at = datetime.now(timezone.utc).replace(microsecond=0)
        issued_timestamp = issued_at.isoformat().replace("+00:00", "Z")
        credential_id = f"urn:uuid:{uuid.uuid4()}"
        credential_subject = {
            "id": f"urn:sha256:{dataset_key}",
            "categoryCounts": noisy_counts,
            "privacy": {
                "mechanism": "discrete_laplace",
                "epsilon": float(epsilon),
                "cumulativeEpsilon": cumulative_epsilon,
                "maximumEpsilon": self.max_epsilon,
                "delta": 0,
                "l1Sensitivity": 1,
                "noiseParameterNumerator": str(noise_numerator),
                "noiseParameterDenominator": noise_denominator,
                "adjacency": "add_remove",
                "unit": "subject",
                "contributionBound": "one category per subject",
            },
        }
        payload = {
            "iss": self.issuer_did,
            "sub": credential_subject["id"],
            "iat": int(issued_at.timestamp()),
            "nbf": int(issued_at.timestamp()),
            "jti": credential_id,
            "vc": {
                "@context": [_VC_CONTEXT],
                "id": credential_id,
                "type": ["VerifiableCredential", "PrivacyPreservingAuditCredential"],
                "issuer": self.issuer_did,
                "validFrom": issued_timestamp,
                "credentialSubject": credential_subject,
            },
        }
        credential_jwt = self._sign(payload)
        return {
            "issuer_did": self.issuer_did,
            "did_document": did_key_document(self.issuer_did),
            "credential_jwt": credential_jwt,
            "credential_sha256": hashlib.sha256(
                credential_jwt.encode("ascii")
            ).hexdigest(),
            "privacy_budget": {
                "epsilon_spent": cumulative_epsilon,
                "epsilon_remaining": max(
                    0.0, self.max_epsilon - cumulative_epsilon
                ),
                "maximum_epsilon": self.max_epsilon,
            },
            "limitations": (
                "This MVP applies a subject-level discrete Laplace mechanism to "
                "one-category histograms. Category labels and the category set "
                "must be public and "
                "fixed before inspecting the dataset. The operator must enforce a "
                "stable dataset_id and retain the privacy-budget database; resetting "
                "it resets accounting. This is not an independent privacy audit, "
                "credential revocation service, or production key-management system."
            ),
        }
