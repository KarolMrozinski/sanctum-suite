"""Provider-neutral OIDC JWT validation and tenant-scoped storage identity."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import re
import time
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa, utils


_TENANT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_CACHE_SECONDS = 300
_REQUEST_TIMEOUT = 5.0
_CLOCK_SKEW_SECONDS = 30


class OIDCAuthenticationError(ValueError):
    """Raised when OIDC configuration or a bearer token cannot be trusted."""


@dataclass(frozen=True)
class AuthenticatedIdentity:
    subject: str
    tenant_id: str
    roles: frozenset[str]
    credential_fingerprint: str
    authentication_method: str


current_identity: ContextVar[AuthenticatedIdentity | None] = ContextVar(
    "sanctum_current_identity", default=None
)


def oidc_configuration() -> tuple[str, str] | None:
    issuer = os.environ.get("SANCTUM_OIDC_ISSUER", "").strip()
    audience = os.environ.get("SANCTUM_OIDC_AUDIENCE", "").strip()
    if not issuer and not audience:
        return None
    parsed_issuer = urlparse(issuer)
    if (
        not issuer
        or not audience
        or parsed_issuer.scheme != "https"
        or not parsed_issuer.netloc
        or parsed_issuer.username is not None
        or parsed_issuer.password is not None
        or parsed_issuer.query
        or parsed_issuer.fragment
    ):
        raise OIDCAuthenticationError(
            "Configure SANCTUM_OIDC_ISSUER as an HTTPS issuer and set SANCTUM_OIDC_AUDIENCE"
        )
    _oidc_tls_verify()
    return issuer, audience


def _oidc_tls_verify() -> bool | str:
    ca_bundle = os.environ.get("SANCTUM_OIDC_CA_CERT", "").strip()
    if not ca_bundle:
        return True
    path = Path(ca_bundle).expanduser()
    if not path.is_file():
        raise OIDCAuthenticationError(
            "SANCTUM_OIDC_CA_CERT must reference an existing CA bundle"
        )
    return str(path)


def tenant_database_path(namespace: str) -> str | None:
    identity = current_identity.get()
    if identity is None:
        return None
    if identity.authentication_method == "event_source" and oidc_configuration() is None:
        return None
    if identity.authentication_method not in {"oidc", "event_source"}:
        return None
    configured_directory = os.environ.get("SANCTUM_TENANT_DATA_DIR", "").strip()
    if configured_directory:
        root = Path(configured_directory).expanduser()
    else:
        root = Path.home() / ".sanctum-suite" / "tenants"
    tenant_digest = hashlib.sha256(identity.tenant_id.encode("utf-8")).hexdigest()
    return str(root / f"{tenant_digest}-{namespace}.sqlite3")


class OIDCTokenVerifier:
    """Validates RS256/ES256 access tokens using HTTPS discovery and rotating JWKS."""

    def __init__(self) -> None:
        self._cached_issuer: str | None = None
        self._cached_jwks: dict[str, dict[str, Any]] = {}
        self._cached_until = 0.0
        self._refresh_lock = asyncio.Lock()

    async def authenticate(self, token: str) -> AuthenticatedIdentity:
        configured = oidc_configuration()
        if configured is None:
            raise OIDCAuthenticationError("OIDC authentication is not configured")
        issuer, audience = configured
        header, signing_input, signature = self._parse_compact_token(token)
        algorithm = header.get("alg")
        key_id = header.get("kid")
        if algorithm not in {"RS256", "ES256"} or not isinstance(key_id, str) or not key_id:
            raise OIDCAuthenticationError("Unsupported or incomplete JWT signing header")

        jwks = await self._get_jwks(issuer)
        key = jwks.get(key_id)
        if key is None:
            jwks = await self._get_jwks(issuer, force_refresh=True)
            key = jwks.get(key_id)
        if key is None:
            raise OIDCAuthenticationError("JWT signing key was not found in the issuer JWKS")
        self._verify_signature(algorithm, key, signing_input, signature)
        claims = self._parse_claims(token)
        self._validate_claims(claims, issuer, audience)
        return self._identity_from_claims(claims, token)

    @staticmethod
    def _parse_compact_token(token: str) -> tuple[dict[str, Any], bytes, bytes]:
        if not token or len(token) > 32_768:
            raise OIDCAuthenticationError("Bearer token is missing or too large")
        segments = token.split(".")
        if len(segments) != 3:
            raise OIDCAuthenticationError("Bearer token is not a compact JWT")

        def decode(segment: str) -> bytes:
            try:
                return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))
            except (ValueError, base64.binascii.Error) as error:
                raise OIDCAuthenticationError("Bearer token has invalid base64url encoding") from error

        try:
            header = json.loads(decode(segments[0]))
            signature = decode(segments[2])
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise OIDCAuthenticationError("Bearer token header is invalid") from error
        if not isinstance(header, dict):
            raise OIDCAuthenticationError("Bearer token header is invalid")
        return header, f"{segments[0]}.{segments[1]}".encode("ascii"), signature

    @staticmethod
    def _parse_claims(token: str) -> dict[str, Any]:
        try:
            encoded_claims = token.split(".")[1]
            claims = json.loads(
                base64.urlsafe_b64decode(
                    encoded_claims + "=" * (-len(encoded_claims) % 4)
                )
            )
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise OIDCAuthenticationError("Bearer token claims are invalid") from error
        if not isinstance(claims, dict):
            raise OIDCAuthenticationError("Bearer token claims must be an object")
        return claims

    @staticmethod
    def _verify_signature(
        algorithm: str,
        jwk: dict[str, Any],
        signing_input: bytes,
        signature: bytes,
    ) -> None:
        try:
            if algorithm == "RS256":
                if jwk.get("kty") != "RSA" or jwk.get("alg") not in {None, "RS256"}:
                    raise OIDCAuthenticationError("JWT key type does not match RS256")
                public_key = rsa.RSAPublicNumbers(
                    int.from_bytes(_decode_jwk_integer(jwk["e"]), "big"),
                    int.from_bytes(_decode_jwk_integer(jwk["n"]), "big"),
                ).public_key()
                if public_key.key_size < 2_048:
                    raise OIDCAuthenticationError("OIDC RSA signing key is smaller than 2048 bits")
                public_key.verify(
                    signature,
                    signing_input,
                    padding.PKCS1v15(),
                    hashes.SHA256(),
                )
                return
            if (
                algorithm == "ES256"
                and jwk.get("kty") == "EC"
                and jwk.get("crv") == "P-256"
                and jwk.get("alg") in {None, "ES256"}
                and len(signature) == 64
            ):
                public_key = ec.EllipticCurvePublicNumbers(
                    int.from_bytes(_decode_jwk_integer(jwk["x"]), "big"),
                    int.from_bytes(_decode_jwk_integer(jwk["y"]), "big"),
                    ec.SECP256R1(),
                ).public_key()
                der_signature = utils.encode_dss_signature(
                    int.from_bytes(signature[:32], "big"),
                    int.from_bytes(signature[32:], "big"),
                )
                public_key.verify(
                    der_signature, signing_input, ec.ECDSA(hashes.SHA256())
                )
                return
        except (KeyError, TypeError, ValueError, InvalidSignature) as error:
            raise OIDCAuthenticationError("Bearer token signature is invalid") from error
        raise OIDCAuthenticationError("JWT key type does not match the allowed algorithm")

    @staticmethod
    def _validate_claims(
        claims: dict[str, Any],
        issuer: str,
        audience: str,
    ) -> None:
        now = time.time()
        if claims.get("iss") != issuer:
            raise OIDCAuthenticationError("Bearer token issuer does not match configuration")
        token_audience = claims.get("aud")
        if not (
            token_audience == audience
            or isinstance(token_audience, list)
            and audience in token_audience
        ):
            raise OIDCAuthenticationError("Bearer token audience does not match configuration")
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject.strip() or len(subject) > 255:
            raise OIDCAuthenticationError("Bearer token subject is missing or invalid")
        expires = claims.get("exp")
        issued = claims.get("iat")
        not_before = claims.get("nbf", 0)
        if (
            isinstance(expires, bool)
            or not isinstance(expires, (int, float))
            or isinstance(issued, bool)
            or not isinstance(issued, (int, float))
            or isinstance(not_before, bool)
            or not isinstance(not_before, (int, float))
            or expires <= issued
            or now >= expires + _CLOCK_SKEW_SECONDS
            or issued > now + _CLOCK_SKEW_SECONDS
            or not_before > now + _CLOCK_SKEW_SECONDS
        ):
            raise OIDCAuthenticationError("Bearer token is expired or not yet valid")

    @staticmethod
    def _identity_from_claims(
        claims: dict[str, Any],
        token: str,
    ) -> AuthenticatedIdentity:
        role_claim = os.environ.get("SANCTUM_OIDC_ROLES_CLAIM", "roles").strip()
        tenant_claim = os.environ.get("SANCTUM_OIDC_TENANT_CLAIM", "tenant_id").strip()
        role_values = claims.get(role_claim)
        if isinstance(role_values, str):
            roles = {role_values.upper()}
        elif isinstance(role_values, list) and all(
            isinstance(role, str) for role in role_values
        ):
            roles = {role.upper() for role in role_values}
        else:
            raise OIDCAuthenticationError(
                f"Bearer token must contain a string or string-list '{role_claim}' claim"
            )
        allowed_roles = {"ADMIN", "AUDITOR", "VIEWER"}
        roles &= allowed_roles
        tenant_id = claims.get(tenant_claim)
        if (
            not isinstance(tenant_id, str)
            or not _TENANT_ID.fullmatch(tenant_id)
            or not roles
        ):
            raise OIDCAuthenticationError(
                f"Bearer token must contain a valid '{tenant_claim}' claim and a supported role"
            )
        fingerprint = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
        return AuthenticatedIdentity(
            subject=claims["sub"],
            tenant_id=tenant_id,
            roles=frozenset(roles),
            credential_fingerprint=fingerprint,
            authentication_method="oidc",
        )

    async def _get_jwks(
        self,
        issuer: str,
        *,
        force_refresh: bool = False,
    ) -> dict[str, dict[str, Any]]:
        if (
            not force_refresh
            and self._cached_issuer == issuer
            and self._cached_until > time.monotonic()
        ):
            return self._cached_jwks
        async with self._refresh_lock:
            if (
                not force_refresh
                and self._cached_issuer == issuer
                and self._cached_until > time.monotonic()
            ):
                return self._cached_jwks
            try:
                async with httpx.AsyncClient(
                    timeout=_REQUEST_TIMEOUT,
                    follow_redirects=False,
                    verify=_oidc_tls_verify(),
                ) as client:
                    metadata_response = await client.get(
                        f"{issuer.rstrip('/')}/.well-known/openid-configuration"
                    )
                    metadata_response.raise_for_status()
                    metadata = metadata_response.json()
                    if (
                        not isinstance(metadata, dict)
                        or metadata.get("issuer") != issuer
                    ):
                        raise OIDCAuthenticationError(
                            "OIDC discovery document issuer does not match configuration"
                        )
                    jwks_uri = metadata.get("jwks_uri")
                    parsed_jwks_uri = urlparse(jwks_uri) if isinstance(jwks_uri, str) else None
                    if (
                        parsed_jwks_uri is None
                        or parsed_jwks_uri.scheme != "https"
                        or not parsed_jwks_uri.netloc
                    ):
                        raise OIDCAuthenticationError(
                            "OIDC discovery document must provide an HTTPS JWKS URI"
                        )
                    jwks_response = await client.get(jwks_uri)
                    jwks_response.raise_for_status()
                    jwks_document = jwks_response.json()
            except OIDCAuthenticationError:
                raise
            except (httpx.HTTPError, ValueError) as error:
                raise OIDCAuthenticationError(
                    "Unable to retrieve trusted OIDC discovery keys"
                ) from error
            keys = jwks_document.get("keys") if isinstance(jwks_document, dict) else None
            if not isinstance(keys, list) or not keys:
                raise OIDCAuthenticationError("OIDC JWKS document contains no keys")
            indexed_keys = {
                key["kid"]: key
                for key in keys
                if isinstance(key, dict)
                and isinstance(key.get("kid"), str)
                and key.get("use", "sig") == "sig"
                and key.get("alg", "RS256") in {"RS256", "ES256"}
            }
            if not indexed_keys:
                raise OIDCAuthenticationError("OIDC JWKS has no supported signing keys")
            self._cached_issuer = issuer
            self._cached_jwks = indexed_keys
            self._cached_until = time.monotonic() + _CACHE_SECONDS
            return indexed_keys


def _decode_jwk_integer(value: Any) -> bytes:
    if not isinstance(value, str) or not value:
        raise ValueError("JWK integer is missing")
    decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    if not decoded:
        raise ValueError("JWK integer is empty")
    return decoded



class KeycloakOIDCProvider:
    """Compatibility adapter exposing integration-friendly OIDC and OAuth2 metadata."""

    def __init__(self, *, issuer: str | None = None, audience: str | None = None) -> None:
        configured = oidc_configuration()
        self.issuer = issuer or (configured[0] if configured else "https://identity.example.test")
        self.audience = audience or (configured[1] if configured else "sanctum-api")
        self.verifier = OIDCTokenVerifier()

    def supported_protocols(self) -> set[str]:
        return {"openid_connect", "oauth2", "saml2"}

    @staticmethod
    def validate_claims(claims: dict[str, Any], *, audience: str) -> dict[str, Any]:
        issuer = claims.get("iss")
        if not isinstance(issuer, str):
            raise OIDCAuthenticationError("issuer is missing")
        if not claims.get("sub"):
            raise OIDCAuthenticationError("subject is missing")
        token_audience = claims.get("aud")
        if token_audience != audience and not (
            isinstance(token_audience, list) and audience in token_audience
        ):
            raise OIDCAuthenticationError("audience mismatch")
        return claims


KeycloakIdentityProvider = KeycloakOIDCProvider
oidc_token_verifier = OIDCTokenVerifier()
