import json
from datetime import datetime, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from sanctum_suite.api import server
from sanctum_suite.core.incident_governance import IncidentGovernanceStore
from sanctum_suite.core.tee_attestation import (
    TEEAttestation,
    TEEAttestationConfigurationError,
    TEEAttestationUnavailable,
    TrusteeClaimsClient,
)


class AsyncMockTransport(httpx.AsyncBaseTransport):
    def __init__(self, handler):
        self.handler = handler

    async def handle_async_request(self, request):
        return await self.handler(request)


def _allowlist():
    return {
        "snp": {
            "measurement_sha384": ["aa" * 48],
            "workload_digest_sha256": ["bb" * 32],
        },
        "tdx": {
            "measurement_sha384": ["cc" * 48],
            "workload_digest_sha256": ["dd" * 32],
        },
        "sgx": {
            "measurement_sha256": ["ee" * 32],
            "workload_digest_sha256": ["ff" * 32],
        },
    }


def configure_trustee_environment(monkeypatch, tmp_path):
    cert = tmp_path / "client.crt"
    key = tmp_path / "client.key"
    ca = tmp_path / "ca.crt"
    allowlist = tmp_path / "expected-claims.json"
    for path in (cert, key, ca):
        path.write_text("test certificate material", encoding="utf-8")
    allowlist.write_text(json.dumps(_allowlist()), encoding="utf-8")
    monkeypatch.setenv(
        "SANCTUM_TEE_VERIFIER_URL",
        "https://trustee-gateway.internal/api/v1/attestation/verify",
    )
    monkeypatch.setenv("SANCTUM_TEE_WORKLOAD_ID", "sanctum-api-prod")
    monkeypatch.setenv("SANCTUM_TEE_CA_CERT_FILE", str(ca))
    monkeypatch.setenv("SANCTUM_TEE_CLIENT_CERT_FILE", str(cert))
    monkeypatch.setenv("SANCTUM_TEE_CLIENT_KEY_FILE", str(key))
    monkeypatch.setenv("SANCTUM_TEE_EXPECTED_CLAIMS_FILE", str(allowlist))
    return cert, key, ca


def _valid_claims(tee_type="snp", now=1_700_000_000):
    baseline = _allowlist()[tee_type]
    measurement_field = (
        "measurement_sha256" if tee_type == "sgx" else "measurement_sha384"
    )
    return {
        "status": "PASS",
        "tee_type": tee_type,
        "workload_id": "sanctum-api-prod",
        "challenge": "fresh-challenge",
        "measurement": baseline[measurement_field][0],
        "workload_digest": baseline["workload_digest_sha256"][0],
        "debug_enabled": False,
        "verified_at": datetime.fromtimestamp(
            now, timezone.utc
        ).isoformat().replace("+00:00", "Z"),
        "evidence_sig": "valid",
    }


def _client(cert, key, ca, *, tee_type="snp", response=None):
    now = 1_700_000_000
    claims = response if response is not None else _valid_claims(tee_type, now)
    requests = []

    async def respond(request):
        requests.append(request)
        return httpx.Response(200, json=claims)

    client = TrusteeClaimsClient(
        endpoint="https://trustee-gateway.internal/api/v1/attestation/verify",
        workload_id="sanctum-api-prod",
        ca_cert_file=str(ca),
        client_cert_file=str(cert),
        client_key_file=str(key),
        max_age_seconds=120,
        expected_claims={
            name: {
                ("measurement_sha256" if name == "sgx" else "measurement_sha384"): frozenset(
                    values["measurement_sha256" if name == "sgx" else "measurement_sha384"]
                ),
                "workload_digest_sha256": frozenset(
                    values["workload_digest_sha256"]
                ),
            }
            for name, values in _allowlist().items()
        },
        transport=AsyncMockTransport(respond),
        clock=lambda: now,
        nonce_factory=lambda: "fresh-challenge",
    )
    client.test_requests = requests
    return client


def test_trustee_client_is_optional_only_outside_production(monkeypatch):
    for name in (
        "SANCTUM_TEE_VERIFIER_URL",
        "SANCTUM_TEE_WORKLOAD_ID",
        "SANCTUM_TEE_CA_CERT_FILE",
        "SANCTUM_TEE_CLIENT_CERT_FILE",
        "SANCTUM_TEE_CLIENT_KEY_FILE",
        "SANCTUM_TEE_EXPECTED_CLAIMS_FILE",
        "SANCTUM_TEE_MAX_ATTESTATION_AGE_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)

    assert TrusteeClaimsClient.from_environment(required=False) is None
    with pytest.raises(TEEAttestationConfigurationError, match="requires"):
        TrusteeClaimsClient.from_environment(required=True)


def test_trustee_client_validates_mtls_and_both_tee_baselines(
    monkeypatch, tmp_path
):
    configure_trustee_environment(monkeypatch, tmp_path)
    client = TrusteeClaimsClient.from_environment(required=True)
    assert client is not None
    assert client._endpoint.endswith("/api/v1/attestation/verify")
    assert set(client._expected_claims) == {"snp", "tdx", "sgx"}

    monkeypatch.setenv(
        "SANCTUM_TEE_VERIFIER_URL",
        "http://trustee-gateway.internal/api/v1/attestation/verify",
    )
    with pytest.raises(TEEAttestationConfigurationError, match="HTTPS"):
        TrusteeClaimsClient.from_environment(required=True)

    monkeypatch.setenv(
        "SANCTUM_TEE_VERIFIER_URL",
        "https://trustee-gateway.internal/api/v1/attestation/verify",
    )
    monkeypatch.setenv("SANCTUM_TEE_MAX_ATTESTATION_AGE_SECONDS", "9")
    with pytest.raises(TEEAttestationConfigurationError, match="between"):
        TrusteeClaimsClient.from_environment(required=True)

    monkeypatch.delenv("SANCTUM_TEE_MAX_ATTESTATION_AGE_SECONDS")
    (tmp_path / "expected-claims.json").write_text(
        json.dumps({"snp": _allowlist()["snp"]}), encoding="utf-8"
    )
    with pytest.raises(TEEAttestationConfigurationError, match="must define"):
        TrusteeClaimsClient.from_environment(required=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("tee_type", ["snp", "tdx", "sgx"])
async def test_trustee_client_accepts_challenge_bound_approved_claims(
    tee_type, tmp_path
):
    cert = tmp_path / "client.crt"
    key = tmp_path / "client.key"
    ca = tmp_path / "ca.crt"
    for path in (cert, key, ca):
        path.write_text("test certificate material", encoding="utf-8")

    requests = []

    async def respond(request):
        requests.append(request)
        return httpx.Response(200, json=_valid_claims(tee_type))

    client = TrusteeClaimsClient(
        endpoint="https://trustee-gateway.internal/api/v1/attestation/verify",
        workload_id="sanctum-api-prod",
        ca_cert_file=str(ca),
        client_cert_file=str(cert),
        client_key_file=str(key),
        max_age_seconds=120,
        expected_claims={
            name: {
                ("measurement_sha256" if name == "sgx" else "measurement_sha384"): frozenset(
                    values["measurement_sha256" if name == "sgx" else "measurement_sha384"]
                ),
                "workload_digest_sha256": frozenset(
                    values["workload_digest_sha256"]
                ),
            }
            for name, values in _allowlist().items()
        },
        transport=AsyncMockTransport(respond),
        clock=lambda: 1_700_000_000,
        nonce_factory=lambda: "fresh-challenge",
    )

    result = await client.verify_readiness()

    assert result == TEEAttestation(
        workload_id="sanctum-api-prod",
        tee_type=tee_type,
        measurement=_allowlist()[tee_type][
            "measurement_sha256" if tee_type == "sgx" else "measurement_sha384"
        ][0],
        workload_digest=_allowlist()[tee_type]["workload_digest_sha256"][0],
        verified_at=datetime.fromtimestamp(1_700_000_000, timezone.utc),
    )
    request = requests[0]
    assert request.method == "POST"
    assert json.loads(request.content) == {
        "workload_id": "sanctum-api-prod",
        "challenge": "fresh-challenge",
    }
    assert "authorization" not in request.headers


@pytest.mark.asyncio
async def test_tee_client_requires_attestation_to_bind_requested_operation(
    tmp_path,
):
    cert = tmp_path / "client.crt"
    key = tmp_path / "client.key"
    ca = tmp_path / "ca.crt"
    for path in (cert, key, ca):
        path.write_text("test certificate material", encoding="utf-8")
    operation_digest = "12" * 32
    claims = _valid_claims()
    claims["operation_digest"] = operation_digest
    client = _client(cert, key, ca, response=claims)

    attestation = await client.verify_readiness(
        operation_digest=operation_digest.upper()
    )

    assert attestation.operation_digest == operation_digest
    assert json.loads(client.test_requests[0].content)["operation_digest"] == operation_digest
    claims["operation_digest"] = "34" * 32
    with pytest.raises(TEEAttestationUnavailable, match="identity, signature"):
        await _client(cert, key, ca, response=claims).verify_readiness(
            operation_digest=operation_digest
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changes",
    [
        {"status": "FAIL"},
        {"evidence_sig": "invalid"},
        {"workload_id": "other-workload"},
        {"challenge": "replayed-challenge"},
        {"tee_type": "snp_tdx"},
        {"debug_enabled": True},
        {"measurement": "ee" * 48},
        {"workload_digest": "ff" * 32},
        {"verified_at": "2020-01-01T00:00:00Z"},
        {"verified_at": "2023-11-14T22:13:26Z"},
    ],
)
async def test_trustee_client_fails_closed_on_unapproved_claims(
    changes, tmp_path
):
    cert = tmp_path / "client.crt"
    key = tmp_path / "client.key"
    ca = tmp_path / "ca.crt"
    for path in (cert, key, ca):
        path.write_text("test certificate material", encoding="utf-8")
    claims = _valid_claims()
    claims.update(changes)

    with pytest.raises(TEEAttestationUnavailable):
        await _client(cert, key, ca, response=claims).verify_readiness()


@pytest.mark.asyncio
async def test_trustee_client_rejects_unavailable_and_oversized_responses(
    tmp_path,
):
    cert = tmp_path / "client.crt"
    key = tmp_path / "client.key"
    ca = tmp_path / "ca.crt"
    for path in (cert, key, ca):
        path.write_text("test certificate material", encoding="utf-8")

    async def unavailable(_request):
        return httpx.Response(503)

    client = _client(cert, key, ca)
    client._transport = AsyncMockTransport(unavailable)
    with pytest.raises(TEEAttestationUnavailable, match="HTTP 503"):
        await client.verify_readiness()

    async def oversized(_request):
        return httpx.Response(200, content=b"x" * (33 * 1024))

    client._transport = AsyncMockTransport(oversized)
    with pytest.raises(TEEAttestationUnavailable, match="size limit"):
        await client.verify_readiness()


def test_readyz_fails_closed_without_trustee_claims_in_production(monkeypatch):
    monkeypatch.setenv("SANCTUM_ENVIRONMENT", "air-gapped")
    monkeypatch.delenv("SANCTUM_TEE_VERIFIER_URL", raising=False)
    monkeypatch.delenv("SANCTUM_TEE_WORKLOAD_ID", raising=False)
    monkeypatch.delenv("SANCTUM_TEE_CA_CERT_FILE", raising=False)
    monkeypatch.delenv("SANCTUM_TEE_CLIENT_CERT_FILE", raising=False)
    monkeypatch.delenv("SANCTUM_TEE_CLIENT_KEY_FILE", raising=False)
    monkeypatch.delenv("SANCTUM_TEE_EXPECTED_CLAIMS_FILE", raising=False)
    monkeypatch.delenv("SANCTUM_TEE_MAX_ATTESTATION_AGE_SECONDS", raising=False)
    monkeypatch.setattr(
        server,
        "get_tee_attestation_client",
        lambda *, required: (_ for _ in ()).throw(
            TEEAttestationConfigurationError("not configured")
        ),
    )

    response = TestClient(server.app).get("/readyz")

    assert response.status_code == 503
    assert response.json()["components"]["confidential_computing"] is False


def test_protected_api_fails_closed_when_trustee_claims_fail(monkeypatch):
    api_key = "trustee-gate-test-key-" + "x" * 32
    monkeypatch.delenv("SANCTUM_ENVIRONMENT", raising=False)
    monkeypatch.setenv("SANCTUM_API_KEY", api_key)
    monkeypatch.delenv("SANCTUM_OPA_URL", raising=False)

    class FailedVerifier:
        async def verify_readiness(self):
            raise TEEAttestationUnavailable("unapproved measurement")

    monkeypatch.setattr(
        server,
        "get_tee_attestation_client",
        lambda *, required: FailedVerifier(),
    )
    response = TestClient(server.app).get(
        "/api/v1/detection-rules",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Confidential-computing attestation is unavailable or stale"
    )


def test_protected_api_audits_both_hardware_attestation_gates(
    monkeypatch, tmp_path
):
    api_key = "tee-audit-test-key-" + "x" * 32
    monkeypatch.delenv("SANCTUM_ENVIRONMENT", raising=False)
    monkeypatch.setenv("SANCTUM_API_KEY", api_key)
    monkeypatch.delenv("SANCTUM_OPA_URL", raising=False)
    governance = IncidentGovernanceStore(tmp_path / "audit.sqlite3")
    monkeypatch.setattr(server, "incident_governance_store", governance)

    class PassingVerifier:
        async def verify_readiness(self):
            return object()

    monkeypatch.setattr(
        server, "get_tpm_attestation_client", lambda *, required: PassingVerifier()
    )
    monkeypatch.setattr(
        server, "get_tee_attestation_client", lambda *, required: PassingVerifier()
    )
    response = TestClient(server.app).get(
        "/api/v1/detection-rules",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    audit_record = governance.list_access()[0]
    assert audit_record["authorization_engine"] == (
        "keylime+tee_verifier+local_rbac"
    )
    assert audit_record["authorization_decision"] == "allow"
