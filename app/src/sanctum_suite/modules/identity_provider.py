from __future__ import annotations

import base64
import hashlib
import json
from typing import Any
from urllib.parse import urlencode


class KeycloakOIDCProvider:
    """Simple identity-provider abstraction supporting OIDC, OAuth2, and SAML metadata discovery."""

    def __init__(self, *, issuer: str, client_id: str, client_secret: str | None = None, realm: str = "master") -> None:
        self.issuer = issuer.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.realm = realm

    def supported_protocols(self) -> set[str]:
        return {"openid_connect", "oauth2", "saml2"}

    def discovery_document(self) -> dict[str, Any]:
        return {
            "issuer": self.issuer,
            "authorization_endpoint": f"{self.issuer}/protocol/openid-connect/auth",
            "token_endpoint": f"{self.issuer}/protocol/openid-connect/token",
            "userinfo_endpoint": f"{self.issuer}/protocol/openid-connect/userinfo",
            "jwks_uri": f"{self.issuer}/protocol/openid-connect/certs",
            "end_session_endpoint": f"{self.issuer}/protocol/openid-connect/logout",
            "saml_metadata_uri": f"{self.issuer}/protocol/saml",
        }

    def oauth_authorization_url(self, *, redirect_uri: str, scopes: list[str] | tuple[str, ...] | None = None, state: str | None = None) -> str:
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes or ["openid", "profile", "email"]),
            "state": state or hashlib.sha256(self.client_id.encode("utf-8")).hexdigest()[:16],
        }
        return f"{self.issuer}/protocol/openid-connect/auth?{urlencode(params)}"

    def validate_token_claims(self, claims: dict[str, Any], *, audience: str) -> dict[str, Any]:
        if not isinstance(claims, dict):
            raise ValueError("Claims must be a JSON object")
        if claims.get("iss") != self.issuer:
            raise ValueError("issuer mismatch")
        audiences = claims.get("aud")
        if isinstance(audiences, list):
            if audience not in audiences:
                raise ValueError("audience mismatch")
        elif claims.get("aud") != audience:
            raise ValueError("audience mismatch")
        if not claims.get("sub"):
            raise ValueError("token missing sub")
        return claims

    @staticmethod
    def parse_saml_assertion(assertion_xml: str) -> dict[str, Any]:
        if not assertion_xml or "<Assertion" not in assertion_xml:
            raise ValueError("SAML assertion is invalid")
        digest = hashlib.sha256(assertion_xml.encode("utf-8")).hexdigest()
        return {"assertion_sha256": digest, "issuer": "unknown", "status": "valid"}


KeycloakIdentityProvider = KeycloakOIDCProvider
