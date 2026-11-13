import httpx
import pytest
from fastapi.testclient import TestClient

from sanctum_suite.api import server
from sanctum_suite.core.tpm_attestation import (
    KeylimeVerifierClient,
    TPMAttestation,
    TPMAttestationConfigurationError,
    TPMAttestationUnavailable,
)
from sanctum_suite.core.incident_governance import IncidentGovernanceStore


class AsyncMockTransport(httpx.AsyncBaseTransport):
    def __init__(self, handler):
        self.handler = handler

    async def handle_async_request(self, request):
        return await self.handler(request)


def configure_keylime_environment(monkeypatch, tmp_path):
    cert = tmp_path / "client.crt"
    key = tmp_path / "client.key"
    ca = tmp_path / "ca.crt"
    for path in (cert, key, ca):
        path.write_text("test certificate material", encoding="utf-8")
    monkeypatch.setenv("SANCTUM_TPM_VERIFIER_URL", "https://keylime.internal")
    monkeypatch.setenv(
        "SANCTUM_TPM_AGENT_ID", "3d6f0a8e-c9e2-4f71-9b48-f28aab3c6012"
    )
    monkeypatch.setenv("SANCTUM_TPM_CA_CERT_FILE", str(ca))
    monkeypatch.setenv("SANCTUM_TPM_CLIENT_CERT_FILE", str(cert))
    monkeypatch.setenv("SANCTUM_TPM_CLIENT_KEY_FILE", str(key))
    return cert, key, ca


def test_keylime_attestation_is_optional_only_outside_production(monkeypatch):
    for name in (
        "SANCTUM_TPM_VERIFIER_URL",
        "SANCTUM_TPM_AGENT_ID",
        "SANCTUM_TPM_CA_CERT_FILE",
        "SANCTUM_TPM_CLIENT_CERT_FILE",
        "SANCTUM_TPM_CLIENT_KEY_FILE",
        "SANCTUM_TPM_MAX_ATTESTATION_AGE_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)

    assert KeylimeVerifierClient.from_environment(required=False) is None
    with pytest.raises(TPMAttestationConfigurationError, match="requires"):
        KeylimeVerifierClient.from_environment(required=True)


def test_keylime_configuration_requires_https_uuid_and_all_mtls_files(
    monkeypatch, tmp_path
):
    configure_keylime_environment(monkeypatch, tmp_path)
    monkeypatch.setenv("SANCTUM_TPM_VERIFIER_URL", "http://keylime.internal")
    with pytest.raises(TPMAttestationConfigurationError, match="HTTPS"):
        KeylimeVerifierClient.from_environment(required=False)

    monkeypatch.setenv("SANCTUM_TPM_VERIFIER_URL", "https://keylime.internal")
    monkeypatch.setenv("SANCTUM_TPM_AGENT_ID", "not-a-uuid")
    with pytest.raises(TPMAttestationConfigurationError, match="UUID"):
        KeylimeVerifierClient.from_environment(required=False)

    monkeypatch.setenv(
        "SANCTUM_TPM_AGENT_ID", "3d6f0a8e-c9e2-4f71-9b48-f28aab3c6012"
    )
    monkeypatch.setenv("SANCTUM_TPM_MAX_ATTESTATION_AGE_SECONDS", "3601")
    with pytest.raises(TPMAttestationConfigurationError, match="between"):
        KeylimeVerifierClient.from_environment(required=False)

    monkeypatch.delenv("SANCTUM_TPM_CLIENT_KEY_FILE")
    with pytest.raises(TPMAttestationConfigurationError, match="requires"):
        KeylimeVerifierClient.from_environment(required=False)


@pytest.mark.asyncio
async def test_keylime_client_accepts_fresh_passing_measured_boot_attestation(
    monkeypatch, tmp_path
):
    cert, key, ca = configure_keylime_environment(monkeypatch, tmp_path)
    now = 1_700_000_000
    requests = []

    async def respond(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "code": 200,
                "status": "Success",
                "results": {
                    "attestation_status": "PASS",
                    "has_mb_refstate": 1,
                    "last_successful_attestation": now - 45,
                },
            },
        )

    client = KeylimeVerifierClient(
        endpoint=(
            "https://keylime.internal/v2.5/agents/"
            "3d6f0a8e-c9e2-4f71-9b48-f28aab3c6012"
        ),
        agent_id="3d6f0a8e-c9e2-4f71-9b48-f28aab3c6012",
        ca_cert_file=str(ca),
        client_cert_file=str(cert),
        client_key_file=str(key),
        max_age_seconds=120,
        transport=AsyncMockTransport(respond),
        clock=lambda: now,
    )

    attestation = await client.verify_readiness()

    assert attestation == TPMAttestation(
        agent_id="3d6f0a8e-c9e2-4f71-9b48-f28aab3c6012",
        last_successful_attestation=now - 45,
        measured_boot_reference_state=True,
    )
    assert requests[0].url.path.endswith(
        "/v2.5/agents/3d6f0a8e-c9e2-4f71-9b48-f28aab3c6012"
    )
    assert "authorization" not in requests[0].headers


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "result",
    [
        {
            "attestation_status": "FAIL",
            "has_mb_refstate": 1,
            "last_successful_attestation": 1_699_999_990,
        },
        {
            "attestation_status": "PASS",
            "has_mb_refstate": 0,
            "last_successful_attestation": 1_699_999_990,
        },
        {
            "attestation_status": "PASS",
            "has_mb_refstate": 1,
            "last_successful_attestation": 1_699_999_000,
        },
        {
            "attestation_status": "PASS",
            "has_mb_refstate": 1,
            "last_successful_attestation": 1_700_000_010,
        },
    ],
)
async def test_keylime_client_fails_closed_on_unacceptable_attestation(
    result, tmp_path
):
    cert = tmp_path / "client.crt"
    key = tmp_path / "client.key"
    ca = tmp_path / "ca.crt"
    for path in (cert, key, ca):
        path.write_text("test certificate material", encoding="utf-8")

    async def respond(_request):
        return httpx.Response(
            200,
            json={"code": 200, "status": "Success", "results": result},
        )

    client = KeylimeVerifierClient(
        endpoint="https://keylime.internal/v2.5/agents/agent",
        agent_id="3d6f0a8e-c9e2-4f71-9b48-f28aab3c6012",
        ca_cert_file=str(ca),
        client_cert_file=str(cert),
        client_key_file=str(key),
        max_age_seconds=120,
        transport=AsyncMockTransport(respond),
        clock=lambda: 1_700_000_000,
    )
    with pytest.raises(TPMAttestationUnavailable):
        await client.verify_readiness()


@pytest.mark.asyncio
async def test_keylime_client_rejects_unavailable_response(tmp_path):
    cert = tmp_path / "client.crt"
    key = tmp_path / "client.key"
    ca = tmp_path / "ca.crt"
    for path in (cert, key, ca):
        path.write_text("test certificate material", encoding="utf-8")

    async def respond(_request):
        return httpx.Response(503)

    client = KeylimeVerifierClient(
        endpoint="https://keylime.internal/v2.5/agents/agent",
        agent_id="3d6f0a8e-c9e2-4f71-9b48-f28aab3c6012",
        ca_cert_file=str(ca),
        client_cert_file=str(cert),
        client_key_file=str(key),
        max_age_seconds=120,
        transport=AsyncMockTransport(respond),
        clock=lambda: 1_700_000_000,
    )
    with pytest.raises(TPMAttestationUnavailable, match="HTTP 503"):
        await client.verify_readiness()


@pytest.mark.asyncio
async def test_keylime_client_rejects_oversized_response(tmp_path):
    cert = tmp_path / "client.crt"
    key = tmp_path / "client.key"
    ca = tmp_path / "ca.crt"
    for path in (cert, key, ca):
        path.write_text("test certificate material", encoding="utf-8")

    async def respond(_request):
        return httpx.Response(200, content=b"x" * (33 * 1024))

    client = KeylimeVerifierClient(
        endpoint="https://keylime.internal/v2.5/agents/agent",
        agent_id="3d6f0a8e-c9e2-4f71-9b48-f28aab3c6012",
        ca_cert_file=str(ca),
        client_cert_file=str(cert),
        client_key_file=str(key),
        max_age_seconds=120,
        transport=AsyncMockTransport(respond),
        clock=lambda: 1_700_000_000,
    )
    with pytest.raises(TPMAttestationUnavailable, match="size limit"):
        await client.verify_readiness()


def test_readyz_requires_keylime_attestation_in_production(monkeypatch):
    monkeypatch.setenv("SANCTUM_ENVIRONMENT", "air-gapped")
    monkeypatch.delenv("SANCTUM_TPM_VERIFIER_URL", raising=False)
    monkeypatch.delenv("SANCTUM_TPM_AGENT_ID", raising=False)
    monkeypatch.delenv("SANCTUM_TPM_CA_CERT_FILE", raising=False)
    monkeypatch.delenv("SANCTUM_TPM_CLIENT_CERT_FILE", raising=False)
    monkeypatch.delenv("SANCTUM_TPM_CLIENT_KEY_FILE", raising=False)
    monkeypatch.delenv("SANCTUM_TPM_MAX_ATTESTATION_AGE_SECONDS", raising=False)
    monkeypatch.setattr(
        server,
        "get_tpm_attestation_client",
        lambda *, required: (_ for _ in ()).throw(
            TPMAttestationConfigurationError("not configured")
        ),
    )

    response = TestClient(server.app).get("/readyz")

    assert response.status_code == 503
    assert response.json()["components"]["tpm_measured_boot"] is False


def test_protected_api_fails_closed_when_keylime_attestation_fails(monkeypatch):
    api_key = "tpm-gate-test-key-" + "x" * 32
    monkeypatch.delenv("SANCTUM_ENVIRONMENT", raising=False)
    monkeypatch.setenv("SANCTUM_API_KEY", api_key)
    monkeypatch.delenv("SANCTUM_OPA_URL", raising=False)

    class FailedVerifier:
        async def verify_readiness(self):
            raise TPMAttestationUnavailable("stale attestation")

    monkeypatch.setattr(
        server,
        "get_tpm_attestation_client",
        lambda *, required: FailedVerifier(),
    )
    response = TestClient(server.app).get(
        "/api/v1/detection-rules",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "TPM measured-boot attestation is unavailable or stale"
    )


def test_protected_api_audits_successful_keylime_gate(monkeypatch, tmp_path):
    api_key = "tpm-audit-test-key-" + "x" * 32
    monkeypatch.delenv("SANCTUM_ENVIRONMENT", raising=False)
    monkeypatch.setenv("SANCTUM_API_KEY", api_key)
    monkeypatch.delenv("SANCTUM_OPA_URL", raising=False)
    governance = IncidentGovernanceStore(tmp_path / "audit.sqlite3")
    monkeypatch.setattr(server, "incident_governance_store", governance)

    class PassingVerifier:
        async def verify_readiness(self):
            return TPMAttestation(
                agent_id="3d6f0a8e-c9e2-4f71-9b48-f28aab3c6012",
                last_successful_attestation=1_700_000_000,
                measured_boot_reference_state=True,
            )

    monkeypatch.setattr(
        server,
        "get_tpm_attestation_client",
        lambda *, required: PassingVerifier(),
    )
    response = TestClient(server.app).get(
        "/api/v1/detection-rules",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    audit_record = governance.list_access()[0]
    assert audit_record["authorization_engine"] == "keylime+local_rbac"
    assert audit_record["authorization_decision"] == "allow"
