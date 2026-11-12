"""Fail-closed client for an operator-managed Keylime verifier."""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import httpx


_MAX_RESPONSE_BYTES = 32 * 1024
_CLOCK_SKEW_SECONDS = 5
_DEFAULT_MAX_AGE_SECONDS = 120


class TPMAttestationConfigurationError(ValueError):
    """Raised when the Keylime verifier configuration is invalid."""


class TPMAttestationUnavailable(RuntimeError):
    """Raised when fresh, valid TPM measured-boot evidence is unavailable."""


@dataclass(frozen=True)
class TPMAttestation:
    agent_id: str
    last_successful_attestation: int
    measured_boot_reference_state: bool


class KeylimeVerifierClient:
    def __init__(
        self,
        *,
        endpoint: str,
        agent_id: str,
        ca_cert_file: str,
        client_cert_file: str,
        client_key_file: str,
        max_age_seconds: int,
        transport: httpx.AsyncBaseTransport | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._endpoint = endpoint
        self._agent_id = agent_id
        self._ca_cert_file = ca_cert_file
        self._client_cert_file = client_cert_file
        self._client_key_file = client_key_file
        self._max_age_seconds = max_age_seconds
        self._transport = transport
        self._clock = clock

    @classmethod
    def from_environment(cls, *, required: bool) -> KeylimeVerifierClient | None:
        values = {
            "SANCTUM_TPM_VERIFIER_URL": os.environ.get(
                "SANCTUM_TPM_VERIFIER_URL", ""
            ).strip(),
            "SANCTUM_TPM_AGENT_ID": os.environ.get(
                "SANCTUM_TPM_AGENT_ID", ""
            ).strip(),
            "SANCTUM_TPM_CA_CERT_FILE": os.environ.get(
                "SANCTUM_TPM_CA_CERT_FILE", ""
            ).strip(),
            "SANCTUM_TPM_CLIENT_CERT_FILE": os.environ.get(
                "SANCTUM_TPM_CLIENT_CERT_FILE", ""
            ).strip(),
            "SANCTUM_TPM_CLIENT_KEY_FILE": os.environ.get(
                "SANCTUM_TPM_CLIENT_KEY_FILE", ""
            ).strip(),
        }
        raw_max_age = os.environ.get(
            "SANCTUM_TPM_MAX_ATTESTATION_AGE_SECONDS", ""
        ).strip()
        configured = any(values.values()) or bool(raw_max_age)
        if not configured:
            if required:
                raise TPMAttestationConfigurationError(
                    "Production requires a Keylime measured-boot verifier"
                )
            return None

        missing = [name for name, value in values.items() if not value]
        if missing:
            raise TPMAttestationConfigurationError(
                "Keylime configuration requires SANCTUM_TPM_VERIFIER_URL, "
                "SANCTUM_TPM_AGENT_ID, SANCTUM_TPM_CA_CERT_FILE, "
                "SANCTUM_TPM_CLIENT_CERT_FILE, and "
                "SANCTUM_TPM_CLIENT_KEY_FILE"
            )

        endpoint = values["SANCTUM_TPM_VERIFIER_URL"]
        parsed = urlparse(endpoint)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise TPMAttestationConfigurationError(
                "SANCTUM_TPM_VERIFIER_URL must be an HTTPS URL without "
                "credentials, query, or fragment"
            )

        try:
            agent_id = str(uuid.UUID(values["SANCTUM_TPM_AGENT_ID"]))
        except ValueError as error:
            raise TPMAttestationConfigurationError(
                "SANCTUM_TPM_AGENT_ID must be a UUID"
            ) from error

        max_age_seconds = _DEFAULT_MAX_AGE_SECONDS
        if raw_max_age:
            try:
                max_age_seconds = int(raw_max_age)
            except ValueError as error:
                raise TPMAttestationConfigurationError(
                    "SANCTUM_TPM_MAX_ATTESTATION_AGE_SECONDS must be an integer"
                ) from error
        if not 10 <= max_age_seconds <= 3_600:
            raise TPMAttestationConfigurationError(
                "SANCTUM_TPM_MAX_ATTESTATION_AGE_SECONDS must be between 10 and 3600"
            )

        file_values = {
            "SANCTUM_TPM_CA_CERT_FILE": values["SANCTUM_TPM_CA_CERT_FILE"],
            "SANCTUM_TPM_CLIENT_CERT_FILE": values[
                "SANCTUM_TPM_CLIENT_CERT_FILE"
            ],
            "SANCTUM_TPM_CLIENT_KEY_FILE": values[
                "SANCTUM_TPM_CLIENT_KEY_FILE"
            ],
        }
        resolved_files: dict[str, str] = {}
        for name, raw_path in file_values.items():
            path = Path(raw_path).expanduser()
            if not path.is_file():
                raise TPMAttestationConfigurationError(
                    f"{name} must reference an existing file"
                )
            resolved_files[name] = str(path)

        return cls(
            endpoint=f"{endpoint.rstrip('/')}/v2.5/agents/{agent_id}",
            agent_id=agent_id,
            ca_cert_file=resolved_files["SANCTUM_TPM_CA_CERT_FILE"],
            client_cert_file=resolved_files["SANCTUM_TPM_CLIENT_CERT_FILE"],
            client_key_file=resolved_files["SANCTUM_TPM_CLIENT_KEY_FILE"],
            max_age_seconds=max_age_seconds,
        )

    async def verify_readiness(self) -> TPMAttestation:
        try:
            async with httpx.AsyncClient(
                verify=self._ca_cert_file,
                cert=(self._client_cert_file, self._client_key_file),
                timeout=httpx.Timeout(3.0, connect=1.0),
                follow_redirects=False,
                transport=self._transport,
            ) as client:
                async with client.stream(
                    "GET",
                    self._endpoint,
                    headers={"Accept": "application/json"},
                ) as response:
                    if response.status_code != 200:
                        raise TPMAttestationUnavailable(
                            f"Keylime verifier returned HTTP {response.status_code}"
                        )
                    body = bytearray()
                    async for chunk in response.aiter_bytes(chunk_size=4_096):
                        body.extend(chunk)
                        if len(body) > _MAX_RESPONSE_BYTES:
                            raise TPMAttestationUnavailable(
                                "Keylime verifier response exceeded its size limit"
                            )
        except TPMAttestationUnavailable:
            raise
        except httpx.HTTPError as error:
            raise TPMAttestationUnavailable(
                "Keylime verifier request failed"
            ) from error

        try:
            document = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise TPMAttestationUnavailable(
                "Keylime verifier returned invalid JSON"
            ) from error
        if (
            not isinstance(document, dict)
            or document.get("code") != 200
            or document.get("status") != "Success"
            or not isinstance(document.get("results"), dict)
        ):
            raise TPMAttestationUnavailable(
                "Keylime verifier response has no valid agent result"
            )

        result = document["results"]
        if result.get("attestation_status") != "PASS":
            raise TPMAttestationUnavailable(
                "Keylime agent does not have a passing attestation status"
            )
        if type(result.get("has_mb_refstate")) is not int or result[
            "has_mb_refstate"
        ] != 1:
            raise TPMAttestationUnavailable(
                "Keylime agent has no measured-boot reference state"
            )
        last_successful_attestation = result.get("last_successful_attestation")
        if (
            type(last_successful_attestation) is not int
            or last_successful_attestation <= 0
        ):
            raise TPMAttestationUnavailable(
                "Keylime agent has no successful attestation timestamp"
            )

        age_seconds = self._clock() - last_successful_attestation
        if (
            age_seconds < -_CLOCK_SKEW_SECONDS
            or age_seconds > self._max_age_seconds
        ):
            raise TPMAttestationUnavailable(
                "Keylime agent attestation is stale or has an invalid timestamp"
            )

        return TPMAttestation(
            agent_id=self._agent_id,
            last_successful_attestation=last_successful_attestation,
            measured_boot_reference_state=True,
        )
