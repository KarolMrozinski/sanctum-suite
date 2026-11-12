import base64
import hashlib
import json
import os
import re
from collections.abc import Mapping, Sequence
from typing import Any

from cryptography.exceptions import InvalidTag, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import mlkem, x25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


_STANDARDIZED_PQC = {
    "ML-KEM": "NIST FIPS 203",
    "ML-DSA": "NIST FIPS 204",
    "SLH-DSA": "NIST FIPS 205",
}
_PQC_PATTERNS = (
    ("ML-KEM", re.compile(r"^ML-KEM(?:-(?:512|768|1024))?$")),
    ("ML-DSA", re.compile(r"^ML-DSA(?:-(?:44|65|87))?$")),
    (
        "SLH-DSA",
        re.compile(
            r"^SLH-DSA(?:-(?:SHA2|SHAKE)-(?:128S|128F|192S|192F|256S|256F))?$"
        ),
    ),
)
_PQC_KEY_ESTABLISHMENT_PROTOCOLS = {"PQXDH"}
_CLASSICAL_PUBLIC_KEY_PATTERN = re.compile(
    r"^(RSA|ECDH|ECDSA|ECDHE|DH|DHE|DSA|ED25519|ED448|X25519|X448)(?:[-_ ]|$)"
)
_SYMMETRIC_OR_HASH = {
    "AES",
    "AES-GCM",
    "AES-128",
    "AES-192",
    "AES-256",
    "CHACHA20",
    "CHACHA20-POLY1305",
    "SHA-256",
    "SHA-384",
    "SHA-512",
    "SHA3-256",
    "SHA3-384",
    "SHA3-512",
}
_USE_CASES = {"key_establishment", "digital_signature", "other", "unknown"}
_ENVELOPE_FORMAT = "sanctum-hybrid-encrypted-v1"
_ENVELOPE_ALGORITHMS = {
    "format",
    "kem",
    "classical_kem",
    "aead",
    "mlkem_recipient_sha256",
    "x25519_recipient_sha256",
    "mlkem_ciphertext",
    "ephemeral_x25519_public_key",
    "kdf_salt",
    "nonce",
    "ciphertext",
}
_MAX_PLAINTEXT_BYTES = 256_000_000
_MAX_ENVELOPE_BYTES = 260_000_000


def generate_hybrid_encryption_key_pair() -> dict[str, bytes]:
    """Generate recipient key material for ML-KEM-768 + X25519 hybrid encryption."""
    try:
        pq_private_key = mlkem.MLKEM768PrivateKey.generate()
    except UnsupportedAlgorithm as error:
        raise ValueError(
            "The cryptography backend does not support ML-KEM-768"
        ) from error
    classical_private_key = x25519.X25519PrivateKey.generate()
    return {
        "mlkem_private_key": pq_private_key.private_bytes_raw(),
        "mlkem_public_key": pq_private_key.public_key().public_bytes_raw(),
        "x25519_private_key": classical_private_key.private_bytes_raw(),
        "x25519_public_key": classical_private_key.public_key().public_bytes_raw(),
    }


def _canonical_envelope(document: dict[str, Any]) -> bytes:
    return json.dumps(
        document,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _decode_envelope_bytes(value: Any, field: str) -> bytes:
    if not isinstance(value, str):
        raise ValueError(f"Encrypted checkpoint field {field} is invalid")
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError(f"Encrypted checkpoint field {field} is invalid") from error


def encrypt_hybrid(
    plaintext: bytes,
    *,
    mlkem_public_key: bytes,
    x25519_public_key: bytes,
) -> bytes:
    """Encrypt bytes using ML-KEM-768 and X25519 combined into an AES-256-GCM key."""
    if not isinstance(plaintext, bytes) or len(plaintext) > _MAX_PLAINTEXT_BYTES:
        raise ValueError("Checkpoint plaintext exceeds the 256-megabyte size limit")
    try:
        pq_recipient = mlkem.MLKEM768PublicKey.from_public_bytes(mlkem_public_key)
        classical_recipient = x25519.X25519PublicKey.from_public_bytes(
            x25519_public_key
        )
    except (TypeError, ValueError, UnsupportedAlgorithm) as error:
        raise ValueError("Hybrid encryption recipient key is invalid") from error

    try:
        pq_shared_secret, pq_ciphertext = pq_recipient.encapsulate()
    except UnsupportedAlgorithm as error:
        raise ValueError(
            "The cryptography backend does not support ML-KEM-768"
        ) from error
    ephemeral_classical = x25519.X25519PrivateKey.generate()
    classical_shared_secret = ephemeral_classical.exchange(classical_recipient)
    classical_ephemeral_public = ephemeral_classical.public_key().public_bytes_raw()
    salt = os.urandom(32)
    nonce = os.urandom(12)
    pq_fingerprint = hashlib.sha256(mlkem_public_key).hexdigest()
    classical_fingerprint = hashlib.sha256(x25519_public_key).hexdigest()
    header: dict[str, Any] = {
        "format": _ENVELOPE_FORMAT,
        "kem": "ML-KEM-768",
        "classical_kem": "X25519",
        "aead": "AES-256-GCM",
        "mlkem_recipient_sha256": pq_fingerprint,
        "x25519_recipient_sha256": classical_fingerprint,
        "mlkem_ciphertext": base64.b64encode(pq_ciphertext).decode("ascii"),
        "ephemeral_x25519_public_key": base64.b64encode(
            classical_ephemeral_public
        ).decode("ascii"),
        "kdf_salt": base64.b64encode(salt).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
    }
    key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"SANCTUM-HYBRID-KEM-v1:ML-KEM-768+X25519",
    ).derive(classical_shared_secret + pq_shared_secret)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, _canonical_envelope(header))
    return _canonical_envelope(
        {**header, "ciphertext": base64.b64encode(ciphertext).decode("ascii")}
    )


def decrypt_hybrid(
    envelope_bytes: bytes,
    *,
    mlkem_private_key: bytes,
    x25519_private_key: bytes,
) -> bytes:
    """Authenticate and decrypt an ML-KEM-768 + X25519 hybrid envelope."""
    if not isinstance(envelope_bytes, bytes) or len(envelope_bytes) > _MAX_ENVELOPE_BYTES:
        raise ValueError("Encrypted checkpoint exceeds the 256-megabyte size limit")
    try:
        document = json.loads(envelope_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Encrypted checkpoint envelope is not valid JSON") from error
    if (
        not isinstance(document, dict)
        or set(document) != _ENVELOPE_ALGORITHMS
        or document.get("format") != _ENVELOPE_FORMAT
        or document.get("kem") != "ML-KEM-768"
        or document.get("classical_kem") != "X25519"
        or document.get("aead") != "AES-256-GCM"
        or _canonical_envelope(document) != envelope_bytes
    ):
        raise ValueError("Encrypted checkpoint envelope format or algorithms are invalid")
    pq_fingerprint = document["mlkem_recipient_sha256"]
    classical_fingerprint = document["x25519_recipient_sha256"]
    if (
        not isinstance(pq_fingerprint, str)
        or not re.fullmatch(r"[0-9a-f]{64}", pq_fingerprint)
        or not isinstance(classical_fingerprint, str)
        or not re.fullmatch(r"[0-9a-f]{64}", classical_fingerprint)
    ):
        raise ValueError("Encrypted checkpoint recipient fingerprints are invalid")
    try:
        pq_private = mlkem.MLKEM768PrivateKey.from_seed_bytes(mlkem_private_key)
        classical_private = x25519.X25519PrivateKey.from_private_bytes(
            x25519_private_key
        )
    except (TypeError, ValueError, UnsupportedAlgorithm) as error:
        raise ValueError("Hybrid decryption recipient key is invalid") from error
    pq_public_bytes = pq_private.public_key().public_bytes_raw()
    classical_public_bytes = classical_private.public_key().public_bytes_raw()
    if (
        hashlib.sha256(pq_public_bytes).hexdigest() != pq_fingerprint
        or hashlib.sha256(classical_public_bytes).hexdigest()
        != classical_fingerprint
    ):
        raise ValueError("Encrypted checkpoint was not addressed to these recipient keys")

    pq_ciphertext = _decode_envelope_bytes(
        document["mlkem_ciphertext"], "mlkem_ciphertext"
    )
    ephemeral_public_bytes = _decode_envelope_bytes(
        document["ephemeral_x25519_public_key"], "ephemeral_x25519_public_key"
    )
    salt = _decode_envelope_bytes(document["kdf_salt"], "kdf_salt")
    nonce = _decode_envelope_bytes(document["nonce"], "nonce")
    ciphertext = _decode_envelope_bytes(document["ciphertext"], "ciphertext")
    if len(salt) != 32 or len(nonce) != 12:
        raise ValueError("Encrypted checkpoint KDF salt or nonce has an invalid size")
    try:
        pq_shared_secret = pq_private.decapsulate(pq_ciphertext)
        ephemeral_public = x25519.X25519PublicKey.from_public_bytes(
            ephemeral_public_bytes
        )
        classical_shared_secret = classical_private.exchange(ephemeral_public)
    except (TypeError, ValueError, UnsupportedAlgorithm) as error:
        raise ValueError("Encrypted checkpoint key encapsulation is invalid") from error
    header = {key: value for key, value in document.items() if key != "ciphertext"}
    key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"SANCTUM-HYBRID-KEM-v1:ML-KEM-768+X25519",
    ).derive(classical_shared_secret + pq_shared_secret)
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, _canonical_envelope(header))
    except InvalidTag as error:
        raise ValueError("Encrypted checkpoint authentication failed") from error


class PostQuantumCryptographicAssuranceEngine:
    """Classifies an operator-supplied crypto inventory; it does not inspect runtime keys."""

    def audit_cryptographic_primitives(
        self,
        inventory: Sequence[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if inventory is None:
            return {
                "status": "NOT_ASSESSED",
                "inventory_required": True,
                "limitations": "No cryptographic primitives were discovered or supplied.",
            }

        reviewed: list[dict[str, Any]] = []
        for item in inventory:
            if not isinstance(item, Mapping):
                raise ValueError("Each inventory entry must be an object")
            algorithm_value = item.get("algorithm", "")
            location_value = item.get("location", "")
            if not isinstance(algorithm_value, str) or not isinstance(location_value, str):
                raise ValueError("Each inventory algorithm and location must be strings")
            algorithm = algorithm_value.strip()
            location = location_value.strip()
            if not algorithm or not location:
                raise ValueError("Each inventory entry requires an algorithm and location")
            normalized = algorithm.upper()
            pqc_family = next(
                (
                    family
                    for family, pattern in _PQC_PATTERNS
                    if pattern.fullmatch(normalized)
                ),
                None,
            )
            if normalized in _PQC_KEY_ESTABLISHMENT_PROTOCOLS:
                classification = "POST_QUANTUM_KEY_ESTABLISHMENT_PROTOCOL_REPORTED"
                family = normalized
                standard = ""
                migration_review = "VERIFY_PROTOCOL_SPEC_IMPLEMENTATION_AND_INTEROPERABILITY"
            elif pqc_family is not None:
                classification = "STANDARDIZED_PQC_ALGORITHM_REPORTED"
                family = pqc_family
                standard = _STANDARDIZED_PQC[family]
                migration_review = "VERIFY_PARAMETERS_IMPLEMENTATION_AND_INTEROPERABILITY"
            elif _CLASSICAL_PUBLIC_KEY_PATTERN.match(normalized):
                classification = "CLASSICAL_PUBLIC_KEY_ALGORITHM_REPORTED"
                standard = ""
                family = normalized.split("-", maxsplit=1)[0]
                migration_review = "MIGRATION_PLANNING_REQUIRED"
            elif normalized in _SYMMETRIC_OR_HASH:
                classification = "SYMMETRIC_OR_HASH_ALGORITHM_REPORTED"
                standard = ""
                family = normalized
                migration_review = "REVIEW_KEY_SIZE_HASH_USE_AND_PROTOCOL_CONTEXT"
            else:
                classification = "ALGORITHM_REQUIRES_REVIEW"
                standard = ""
                family = ""
                migration_review = "MANUAL_ALGORITHM_REVIEW_REQUIRED"

            use_case = item.get("use_case", "unknown")
            if not isinstance(use_case, str) or use_case not in _USE_CASES:
                raise ValueError(
                    "use_case must be key_establishment, digital_signature, other, or unknown"
                )
            long_term_confidentiality = item.get(
                "requires_long_term_confidentiality"
            )
            if long_term_confidentiality is not None and not isinstance(
                long_term_confidentiality, bool
            ):
                raise ValueError("requires_long_term_confidentiality must be a boolean")
            if (
                classification == "CLASSICAL_PUBLIC_KEY_ALGORITHM_REPORTED"
                and use_case == "key_establishment"
                and long_term_confidentiality is True
            ):
                migration_review = "PRIORITIZE_HARVEST_NOW_DECRYPT_LATER_REVIEW"
            reviewed.append({
                "algorithm": algorithm,
                "algorithm_family": family,
                "location": location,
                "use_case": use_case,
                "classification": classification,
                "standard": standard,
                "requires_long_term_confidentiality": long_term_confidentiality,
                "migration_review": migration_review,
            })

        return {
            "status": "INVENTORY_REVIEW_REQUIRED" if reviewed else "NOT_ASSESSED",
            "inventory_scope": "OPERATOR_SUPPLIED",
            "algorithms": reviewed,
            "review_counts": {
                "total": len(reviewed),
                "classical_public_key": sum(
                    item["classification"] == "CLASSICAL_PUBLIC_KEY_ALGORITHM_REPORTED"
                    for item in reviewed
                ),
                "standardized_pqc_reported": sum(
                    item["classification"] == "STANDARDIZED_PQC_ALGORITHM_REPORTED"
                    for item in reviewed
                ),
                "manual_review": sum(
                    item["classification"] == "ALGORITHM_REQUIRES_REVIEW"
                    for item in reviewed
                ),
                "hndl_review_prioritized": sum(
                    item["migration_review"]
                    == "PRIORITIZE_HARVEST_NOW_DECRYPT_LATER_REVIEW"
                    for item in reviewed
                ),
            },
            "limitations": (
                "This report classifies operator-supplied names and declared use cases only. "
                "It does not discover deployed cryptography, validate parameter sets, "
                "implementation, key management, protocol negotiation, or migration readiness. "
                "Migration review priorities are triage hints, not a risk assessment or certification."
            ),
        }
