import base64
import json
import time

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi.testclient import TestClient

from sanctum_suite.api import server
from sanctum_suite.core.incident_governance import IncidentGovernanceStore
from sanctum_suite.core.oidc import (
    AuthenticatedIdentity,
    OIDCAuthenticationError,
    OIDCTokenVerifier,
    current_identity,
    tenant_database_path,
)


ISSUER = "https://identity.example.test"
AUDIENCE = "sanctum-api"


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _rsa_jwk(private_key):
    public_numbers = private_key.public_key().public_numbers()
    return {
        "kid": "test-signing-key",
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "n": _base64url(
            public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, "big")
        ),
        "e": _base64url(
            public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, "big")
        ),
    }


def _signed_token(private_key, **claim_overrides):
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "user-42",
        "tenant_id": "tenant-a",
        "roles": ["AUDITOR"],
        "iat": int(time.time()),
        "exp": int(time.time()) + 300,
    }
    claims.update(claim_overrides)
    header = {"alg": "RS256", "kid": "test-signing-key", "typ": "JWT"}
    signing_input = (
        f"{_base64url(json.dumps(header).encode())}."
        f"{_base64url(json.dumps(claims).encode())}"
    ).encode("ascii")
    signature = private_key.sign(
        signing_input,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return f"{signing_input.decode()}.{_base64url(signature)}"


@pytest.mark.asyncio
async def test_oidc_verifies_signature_claims_and_maps_identity(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setenv("SANCTUM_OIDC_ISSUER", ISSUER)
    monkeypatch.setenv("SANCTUM_OIDC_AUDIENCE", AUDIENCE)
    verifier = OIDCTokenVerifier()

    async def fake_jwks(_issuer, *, force_refresh=False):
        return {"test-signing-key": _rsa_jwk(private_key)}

    monkeypatch.setattr(verifier, "_get_jwks", fake_jwks)
    token = _signed_token(private_key)

    identity = await verifier.authenticate(token)

    assert identity.subject == "user-42"
    assert identity.tenant_id == "tenant-a"
    assert identity.roles == frozenset({"AUDITOR"})
    assert identity.authentication_method == "oidc"
    assert len(identity.credential_fingerprint) == 16
    assert token not in identity.credential_fingerprint


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("claims", "message"),
    [
        ({"iss": "https://attacker.example"}, "issuer"),
        ({"aud": "other-api"}, "audience"),
        ({"exp": int(time.time()) - 60}, "expired"),
        ({"tenant_id": "../other"}, "tenant_id"),
        ({"roles": ["UNKNOWN"]}, "tenant_id"),
    ],
)
async def test_oidc_rejects_untrusted_or_invalid_claims(
    monkeypatch, claims, message
):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setenv("SANCTUM_OIDC_ISSUER", ISSUER)
    monkeypatch.setenv("SANCTUM_OIDC_AUDIENCE", AUDIENCE)
    verifier = OIDCTokenVerifier()

    async def fake_jwks(_issuer, *, force_refresh=False):
        return {"test-signing-key": _rsa_jwk(private_key)}

    monkeypatch.setattr(verifier, "_get_jwks", fake_jwks)
    token = _signed_token(private_key, **claims)

    with pytest.raises(OIDCAuthenticationError, match=message):
        await verifier.authenticate(token)


def test_tenant_database_paths_are_distinct_and_hide_tenant_identifiers(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("SANCTUM_TENANT_DATA_DIR", str(tmp_path))
    identity_a = AuthenticatedIdentity(
        "user-a", "customer-a", frozenset({"AUDITOR"}), "a" * 16, "oidc"
    )
    identity_b = AuthenticatedIdentity(
        "user-b", "customer-b", frozenset({"AUDITOR"}), "b" * 16, "oidc"
    )
    token_a = current_identity.set(identity_a)
    path_a = tenant_database_path("cases")
    current_identity.reset(token_a)
    token_b = current_identity.set(identity_b)
    path_b = tenant_database_path("cases")
    current_identity.reset(token_b)

    assert path_a is not None and path_b is not None
    assert path_a != path_b
    assert "customer-a" not in path_a
    assert "customer-b" not in path_b


def test_oidc_api_enforces_roles_and_tenant_data_isolation(monkeypatch, tmp_path):
    monkeypatch.setenv("SANCTUM_OIDC_ISSUER", ISSUER)
    monkeypatch.setenv("SANCTUM_OIDC_AUDIENCE", AUDIENCE)
    monkeypatch.setenv("SANCTUM_TENANT_DATA_DIR", str(tmp_path / "tenant-data"))
    monkeypatch.delenv("SANCTUM_API_KEY", raising=False)
    monkeypatch.delenv("SANCTUM_ALLOW_LEGACY_API_KEY", raising=False)
    monkeypatch.setattr(server, "_tenant_case_stores", {})
    monkeypatch.setattr(server, "_tenant_governance_stores", {})
    identities = {
        "auditor-a": AuthenticatedIdentity(
            "subject-a", "tenant-a", frozenset({"AUDITOR"}), "a" * 16, "oidc"
        ),
        "auditor-b": AuthenticatedIdentity(
            "subject-b", "tenant-b", frozenset({"AUDITOR"}), "b" * 16, "oidc"
        ),
        "viewer-a": AuthenticatedIdentity(
            "viewer-a", "tenant-a", frozenset({"VIEWER"}), "c" * 16, "oidc"
        ),
    }

    class FakeVerifier:
        async def authenticate(self, token):
            if token not in identities:
                raise OIDCAuthenticationError("invalid token")
            return identities[token]

    monkeypatch.setattr(server, "oidc_token_verifier", FakeVerifier())
    client = TestClient(server.app)
    headers_a = {"Authorization": "Bearer auditor-a"}
    headers_b = {"Authorization": "Bearer auditor-b"}
    created = client.post(
        "/api/v1/cases",
        headers=headers_a,
        json={
            "title": "Tenant A case",
            "summary": "Only tenant A should read this case.",
            "created_by": "request-label",
        },
    )
    assert created.status_code == 201, created.text
    case_id = created.json()["case_id"]
    assert client.get(
        f"/api/v1/cases/{case_id}",
        headers=headers_a,
    ).status_code == 200
    assert client.get(
        f"/api/v1/cases/{case_id}",
        headers=headers_b,
    ).status_code == 404

    denied = client.post(
        "/api/v1/cases",
        headers={"Authorization": "Bearer viewer-a"},
        json={
            "title": "Viewer write attempt",
            "summary": "Viewers cannot create cases.",
            "created_by": "viewer",
        },
    )
    assert denied.status_code == 403

    audit = client.get("/api/v1/governance/access-log", headers=headers_a)
    assert audit.status_code == 200
    records = audit.json()["records"]
    assert all(record["tenant_id"] == "tenant-a" for record in records)
    assert {record["subject_id"] for record in records} == {"subject-a"}
    assert all(record["authentication_method"] == "oidc" for record in records)


def test_governance_audit_migrates_existing_table(tmp_path):
    database = tmp_path / "legacy-audit.sqlite3"
    legacy_store = IncidentGovernanceStore(database)
    legacy_store.record_access(
        credential_fingerprint="d" * 16,
        action="GET /api/v1/cases",
        outcome_code=200,
    )

    migrated = IncidentGovernanceStore(database)
    record = migrated.list_access()[0]

    assert record["subject_id"] is None
    assert record["tenant_id"] is None
    assert record["authentication_method"] is None
