"""Fail-closed client for an operator-managed Open Policy Agent service."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

import httpx


_POLICY_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,127}$")
_MAX_RESPONSE_BYTES = 16 * 1024
_DECISION_PATH = "/v1/data/sanctum/api/authz/decision"


class OPAPolicyConfigurationError(ValueError):
    """Raised when the configured OPA endpoint or credentials are invalid."""


class OPAPolicyUnavailable(RuntimeError):
    """Raised when OPA cannot return a valid authorization decision."""


@dataclass(frozen=True)
class OPAPolicyDecision:
    allow: bool
    policy_version: str


class OPAPolicyClient:
    def __init__(
        self,
        *,
        endpoint: str,
        verify: bool | str,
        bearer_token: str | None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._endpoint = endpoint
        self._verify = verify
        self._bearer_token = bearer_token
        self._transport = transport

    @classmethod
    def from_environment(cls, *, required: bool) -> OPAPolicyClient | None:
        endpoint = os.environ.get("SANCTUM_OPA_URL", "").strip()
        token_file = os.environ.get("SANCTUM_OPA_BEARER_TOKEN_FILE", "").strip()
        ca_bundle = os.environ.get("SANCTUM_OPA_CA_CERT", "").strip()
        if not endpoint:
            if token_file or ca_bundle:
                raise OPAPolicyConfigurationError(
                    "SANCTUM_OPA_URL is required when OPA credentials or CA settings are provided"
                )
            if required:
                raise OPAPolicyConfigurationError(
                    "Production requires SANCTUM_OPA_URL"
                )
            return None

        parsed = urlparse(endpoint)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise OPAPolicyConfigurationError(
                "SANCTUM_OPA_URL must be an HTTPS URL without credentials, query, or fragment"
            )

        verify: bool | str = True
        if ca_bundle:
            ca_path = Path(ca_bundle).expanduser()
            if not ca_path.is_file():
                raise OPAPolicyConfigurationError(
                    "SANCTUM_OPA_CA_CERT must reference an existing CA bundle"
                )
            verify = str(ca_path)

        bearer_token = None
        if token_file:
            try:
                bearer_token = Path(token_file).expanduser().read_text(
                    encoding="utf-8"
                ).strip()
            except OSError as error:
                raise OPAPolicyConfigurationError(
                    "Unable to read SANCTUM_OPA_BEARER_TOKEN_FILE"
                ) from error
            if (
                not bearer_token
                or len(bearer_token) > 8_192
                or any(ord(character) < 33 or ord(character) > 126 for character in bearer_token)
            ):
                raise OPAPolicyConfigurationError(
                    "SANCTUM_OPA_BEARER_TOKEN_FILE must contain a printable, non-empty token"
                )

        base_url = endpoint.rstrip("/")
        return cls(
            endpoint=f"{base_url}{_DECISION_PATH}",
            verify=verify,
            bearer_token=bearer_token,
        )

    async def evaluate(self, policy_input: dict[str, Any]) -> OPAPolicyDecision:
        headers = (
            {"Authorization": f"Bearer {self._bearer_token}"}
            if self._bearer_token is not None
            else {}
        )
        try:
            async with httpx.AsyncClient(
                verify=self._verify,
                timeout=httpx.Timeout(2.0, connect=1.0),
                follow_redirects=False,
                transport=self._transport,
            ) as client:
                async with client.stream(
                    "POST",
                    self._endpoint,
                    headers=headers,
                    json={"input": policy_input},
                ) as response:
                    if response.status_code != 200:
                        raise OPAPolicyUnavailable(
                            f"OPA returned HTTP {response.status_code}"
                        )
                    body = bytearray()
                    async for chunk in response.aiter_bytes(chunk_size=4_096):
                        body.extend(chunk)
                        if len(body) > _MAX_RESPONSE_BYTES:
                            raise OPAPolicyUnavailable(
                                "OPA decision response exceeded its size limit"
                            )
        except OPAPolicyUnavailable:
            raise
        except httpx.HTTPError as error:
            raise OPAPolicyUnavailable("OPA decision request failed") from error

        try:
            document = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise OPAPolicyUnavailable("OPA returned invalid JSON") from error
        if not isinstance(document, dict) or not isinstance(
            document.get("result"), dict
        ):
            raise OPAPolicyUnavailable("OPA response has no decision result")
        result = document["result"]
        allow = result.get("allow")
        policy_version = result.get("policy_version")
        if (
            type(allow) is not bool
            or not isinstance(policy_version, str)
            or not _POLICY_VERSION.fullmatch(policy_version)
        ):
            raise OPAPolicyUnavailable(
                "OPA decision must contain a boolean allow and a valid policy_version"
            )
        return OPAPolicyDecision(allow=allow, policy_version=policy_version)

    async def verify_readiness(self) -> str:
        decision = await self.evaluate(
            {
                "identity": {
                    "authentication_method": "readiness_probe",
                    "tenant_id": "readiness",
                    "roles": [],
                },
                "request": {
                    "method": "GET",
                    "route": "/__sanctum_opa_readiness__",
                },
            }
        )
        if decision.allow:
            raise OPAPolicyUnavailable(
                "OPA readiness probe was unexpectedly allowed"
            )
        return decision.policy_version
