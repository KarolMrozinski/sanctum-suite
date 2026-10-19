"""Fail-closed client for an operator-managed Trustee claims gateway."""

from __future__ import annotations

import json
import os
import re
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import httpx


_MAX_RESPONSE_BYTES = 32 * 1024
_MAX_ALLOWLIST_BYTES = 64 * 1024
_CLOCK_SKEW_SECONDS = 5
_DEFAULT_MAX_AGE_SECONDS = 120
_TEE_TYPES = {"snp", "tdx"}
_MEASUREMENT_SHA384 = re.compile(r"^[0-9a-fA-F]{96}$")
_WORKLOAD_DIGEST_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
_WORKLOAD_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class TEEAttestationConfigurationError(ValueError):
    """Raised when the Trustee claims gateway configuration is invalid."""


class TEEAttestationUnavailable(RuntimeError):
    """Raised when fresh, trusted confidential-computing evidence is unavailable."""


@dataclass(frozen=True)
class TEEAttestation:
    workload_id: str
    tee_type: str
    measurement: str
    workload_digest: str
    verified_at: datetime


def _validated_allowlist(path: Path) -> dict[str, dict[str, frozenset[str]]]:
    try:
        if path.stat().st_size > _MAX_ALLOWLIST_BYTES:
            raise TEEAttestationConfigurationError(
                "SANCTUM_TEE_EXPECTED_CLAIMS_FILE exceeds its size limit"
            )
        document = json.loads(path.read_text(encoding="utf-8"))
    except TEEAttestationConfigurationError:
        raise
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise TEEAttestationConfigurationError(
            "SANCTUM_TEE_EXPECTED_CLAIMS_FILE is unreadable or invalid JSON"
        ) from error
    if not isinstance(document, dict) or set(document) != _TEE_TYPES:
        raise TEEAttestationConfigurationError(
            "TEE claims allowlist must define exactly the snp and tdx platforms"
        )

    validated: dict[str, dict[str, frozenset[str]]] = {}
    for tee_type in _TEE_TYPES:
        platform = document[tee_type]
        if not isinstance(platform, dict) or set(platform) != {
            "measurement_sha384",
            "workload_digest_sha256",
        }:
            raise TEEAttestationConfigurationError(
                f"TEE claims allowlist entry for {tee_type} has an invalid schema"
            )

        measurements = platform["measurement_sha384"]
        workload_digests = platform["workload_digest_sha256"]
        if (
            not isinstance(measurements, list)
            or not measurements
            or any(
                not isinstance(value, str)
                or not _MEASUREMENT_SHA384.fullmatch(value)
                for value in measurements
            )
        ):
            raise TEEAttestationConfigurationError(
                f"TEE claims allowlist has invalid {tee_type} SHA-384 measurements"
            )
        if (
            not isinstance(workload_digests, list)
            or not workload_digests
            or any(
                not isinstance(value, str)
                or not _WORKLOAD_DIGEST_SHA256.fullmatch(value)
                for value in workload_digests
            )
        ):
            raise TEEAttestationConfigurationError(
                f"TEE claims allowlist has invalid {tee_type} workload digests"
            )
        validated[tee_type] = {
            "measurement_sha384": frozenset(
                value.lower() for value in measurements
            ),
            "workload_digest_sha256": frozenset(
                value.lower() for value in workload_digests
            ),
        }
    return validated

class TrusteeClaimsClient:
    def __init__(
        self,
        *,
        endpoint: str,
        workload_id: str,
        ca_cert_file: str,
        client_cert_file: str,
        client_key_file: str,
        max_age_seconds: int,
        expected_claims: dict[str, dict[str, frozenset[str]]],
        transport: httpx.AsyncBaseTransport | None = None,
        clock: Callable[[], float] = time.time,
        nonce_factory: Callable[[], str] = lambda: secrets.token_urlsafe(32),
    ) -> None:
        self._endpoint = endpoint
        self._workload_id = workload_id
        self._ca_cert_file = ca_cert_file
        self._client_cert_file = client_cert_file
        self._client_key_file = client_key_file
        self._max_age_seconds = max_age_seconds
        self._expected_claims = expected_claims
        self._transport = transport
        self._clock = clock
        self._nonce_factory = nonce_factory

    @classmethod
    def from_environment(cls, *, required: bool) -> TrusteeClaimsClient | None:
        values = {
            "SANCTUM_TEE_VERIFIER_URL": os.environ.get(
                "SANCTUM_TEE_VERIFIER_URL", ""
            ).strip(),
            "SANCTUM_TEE_WORKLOAD_ID": os.environ.get(
                "SANCTUM_TEE_WORKLOAD_ID", ""
            ).strip(),
            "SANCTUM_TEE_CA_CERT_FILE": os.environ.get(
                "SANCTUM_TEE_CA_CERT_FILE", ""
            ).strip(),
            "SANCTUM_TEE_CLIENT_CERT_FILE": os.environ.get(
                "SANCTUM_TEE_CLIENT_CERT_FILE", ""
            ).strip(),
            "SANCTUM_TEE_CLIENT_KEY_FILE": os.environ.get(
                "SANCTUM_TEE_CLIENT_KEY_FILE", ""
            ).strip(),
            "SANCTUM_TEE_EXPECTED_CLAIMS_FILE": os.environ.get(
                "SANCTUM_TEE_EXPECTED_CLAIMS_FILE", ""
            ).strip(),
        }
        raw_max_age = os.environ.get(
            "SANCTUM_TEE_MAX_ATTESTATION_AGE_SECONDS", ""
        ).strip()
        configured = any(values.values()) or bool(raw_max_age)
        if not configured:
            if required:
                raise TEEAttestationConfigurationError(
                    "Production requires a Trustee TEE claims verifier"
                )
            return None

        if any(not value for value in values.values()):
            raise TEEAttestationConfigurationError(
                "Trustee configuration requires SANCTUM_TEE_VERIFIER_URL, "
                "SANCTUM_TEE_WORKLOAD_ID, SANCTUM_TEE_CA_CERT_FILE, "
                "SANCTUM_TEE_CLIENT_CERT_FILE, SANCTUM_TEE_CLIENT_KEY_FILE, "
                "and SANCTUM_TEE_EXPECTED_CLAIMS_FILE"
            )

        endpoint = values["SANCTUM_TEE_VERIFIER_URL"]
        parsed = urlparse(endpoint)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise TEEAttestationConfigurationError(
                "SANCTUM_TEE_VERIFIER_URL must be an HTTPS URL without "
                "credentials, query, or fragment"
            )

        workload_id = values["SANCTUM_TEE_WORKLOAD_ID"]
        if not _WORKLOAD_ID.fullmatch(workload_id):
            raise TEEAttestationConfigurationError(
                "SANCTUM_TEE_WORKLOAD_ID has an invalid format"
            )

        max_age_seconds = _DEFAULT_MAX_AGE_SECONDS
        if raw_max_age:
            try:
                max_age_seconds = int(raw_max_age)
            except ValueError as error:
                raise TEEAttestationConfigurationError(
                    "SANCTUM_TEE_MAX_ATTESTATION_AGE_SECONDS must be an integer"
                ) from error
        if not 10 <= max_age_seconds <= 3_600:
            raise TEEAttestationConfigurationError(
                "SANCTUM_TEE_MAX_ATTESTATION_AGE_SECONDS must be between 10 and 3600"
            )

        file_values = {
            "SANCTUM_TEE_CA_CERT_FILE": values["SANCTUM_TEE_CA_CERT_FILE"],
            "SANCTUM_TEE_CLIENT_CERT_FILE": values[
                "SANCTUM_TEE_CLIENT_CERT_FILE"
            ],
            "SANCTUM_TEE_CLIENT_KEY_FILE": values[
                "SANCTUM_TEE_CLIENT_KEY_FILE"
            ],
            "SANCTUM_TEE_EXPECTED_CLAIMS_FILE": values[
                "SANCTUM_TEE_EXPECTED_CLAIMS_FILE"
            ],
        }
        resolved_files: dict[str, Path] = {}
        for name, raw_path in file_values.items():
            path = Path(raw_path).expanduser()
            if not path.is_file():
                raise TEEAttestationConfigurationError(
                    f"{name} must reference an existing file"
                )
            resolved_files[name] = path

        return cls(
            endpoint=endpoint,
            workload_id=workload_id,
            ca_cert_file=str(resolved_files["SANCTUM_TEE_CA_CERT_FILE"]),
            client_cert_file=str(
                resolved_files["SANCTUM_TEE_CLIENT_CERT_FILE"]
            ),
            client_key_file=str(resolved_files["SANCTUM_TEE_CLIENT_KEY_FILE"]),
            max_age_seconds=max_age_seconds,
            expected_claims=_validated_allowlist(
                resolved_files["SANCTUM_TEE_EXPECTED_CLAIMS_FILE"]
            ),
        )

    async def verify_readiness(self) -> TEEAttestation:
        challenge = self._nonce_factory()
        try:
            async with httpx.AsyncClient(
                verify=self._ca_cert_file,
                cert=(self._client_cert_file, self._client_key_file),
                timeout=httpx.Timeout(5.0, connect=1.0),
                follow_redirects=False,
                transport=self._transport,
            ) as client:
                async with client.stream(
                    "POST",
                    self._endpoint,
                    headers={"Accept": "application/json"},
                    json={
                        "workload_id": self._workload_id,
                        "challenge": challenge,
                    },
                ) as response:
                    if response.status_code != 200:
                        raise TEEAttestationUnavailable(
                            f"Trustee gateway returned HTTP {response.status_code}"
                        )
                    body = bytearray()
                    async for chunk in response.aiter_bytes(chunk_size=4_096):
                        body.extend(chunk)
                        if len(body) > _MAX_RESPONSE_BYTES:
                            raise TEEAttestationUnavailable(
                                "Trustee gateway response exceeded its size limit"
                            )
        except TEEAttestationUnavailable:
            raise
        except httpx.HTTPError as error:
            raise TEEAttestationUnavailable(
                "Trustee gateway request failed"
            ) from error

        try:
            document = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise TEEAttestationUnavailable(
                "Trustee gateway returned invalid JSON"
            ) from error
        if not isinstance(document, dict):
            raise TEEAttestationUnavailable(
                "Trustee gateway response must be a JSON object"
            )

        tee_type = document.get("tee_type")
        if (
            document.get("status") != "PASS"
            or document.get("evidence_sig") != "valid"
            or document.get("workload_id") != self._workload_id
            or document.get("challenge") != challenge
            or not isinstance(tee_type, str)
            or tee_type not in _TEE_TYPES
            or document.get("debug_enabled") is not False
        ):
            raise TEEAttestationUnavailable(
                "Trustee gateway claims failed identity, signature, or debug checks"
            )

        measurement = document.get("measurement")
        workload_digest = document.get("workload_digest")
        if (
            not isinstance(measurement, str)
            or not _MEASUREMENT_SHA384.fullmatch(measurement)
            or not isinstance(workload_digest, str)
            or not _WORKLOAD_DIGEST_SHA256.fullmatch(workload_digest)
        ):
            raise TEEAttestationUnavailable(
                "Trustee gateway claims contain invalid measurement digests"
            )
        normalized_measurement = measurement.lower()
        normalized_digest = workload_digest.lower()
        expected = self._expected_claims[tee_type]
        if normalized_measurement not in expected["measurement_sha384"]:
            raise TEEAttestationUnavailable(
                "Trustee gateway measurement is not in the approved baseline"
            )
        if normalized_digest not in expected["workload_digest_sha256"]:
            raise TEEAttestationUnavailable(
                "Trustee gateway workload digest is not in the approved baseline"
            )

        verified_at_raw = document.get("verified_at")
        if not isinstance(verified_at_raw, str):
            raise TEEAttestationUnavailable(
                "Trustee gateway claims have no verification timestamp"
            )
        try:
            verified_at = datetime.fromisoformat(
                verified_at_raw[:-1] + "+00:00"
                if verified_at_raw.endswith("Z")
                else verified_at_raw
            )
        except ValueError as error:
            raise TEEAttestationUnavailable(
                "Trustee gateway returned an invalid verification timestamp"
            ) from error
        if verified_at.tzinfo is None or verified_at.utcoffset() is None:
            raise TEEAttestationUnavailable(
                "Trustee gateway verification timestamp must include a timezone"
            )
        age_seconds = self._clock() - verified_at.timestamp()
        if (
            age_seconds < -_CLOCK_SKEW_SECONDS
            or age_seconds > self._max_age_seconds
        ):
            raise TEEAttestationUnavailable(
                "Trustee gateway claims are stale or have an invalid timestamp"
            )

        return TEEAttestation(
            workload_id=self._workload_id,
            tee_type=tee_type,
            measurement=normalized_measurement,
            workload_digest=normalized_digest,
            verified_at=verified_at.astimezone(timezone.utc),
        )
