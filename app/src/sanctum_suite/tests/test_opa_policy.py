import json

import httpx
import pytest
from fastapi.testclient import TestClient

from sanctum_suite.api import server
from sanctum_suite.core.opa_policy import (
    OPAPolicyClient,
    OPAPolicyConfigurationError,
    OPAPolicyDecision,
    OPAPolicyUnavailable,
)
from sanctum_suite.core.incident_governance import IncidentGovernanceStore


class AsyncMockTransport(httpx.AsyncBaseTransport):
    def __init__(self, handler):
        self.handler = handler

    async def handle_async_request(self, request):
        return await self.handler(request)


def test_opa_is_optional_only_outside_production(monkeypatch):
    monkeypatch.delenv("SANCTUM_OPA_URL", raising=False)
    monkeypatch.delenv("SANCTUM_OPA_BEARER_TOKEN_FILE", raising=False)
    monkeypatch.delenv("SANCTUM_OPA_CA_CERT", raising=False)

    assert OPAPolicyClient.from_environment(required=False) is None
    with pytest.raises(OPAPolicyConfigurationError, match="requires"):
        OPAPolicyClient.from_environment(required=True)


def test_opa_configuration_requires_https_and_valid_secret_files(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("SANCTUM_OPA_URL", "http://opa.internal")
    with pytest.raises(OPAPolicyConfigurationError, match="HTTPS"):
        OPAPolicyClient.from_environment(required=False)

    token_file = tmp_path / "opa-token"
    token_file.write_text("operator-token\n", encoding="utf-8")
    monkeypatch.setenv("SANCTUM_OPA_URL", "https://opa.internal")
    monkeypatch.setenv("SANCTUM_OPA_BEARER_TOKEN_FILE", str(token_file))
    client = OPAPolicyClient.from_environment(required=True)

    assert client is not None
    assert client._endpoint == (
        "https://opa.internal/v1/data/sanctum/api/authz/decision"
    )
    token_file.write_text("invalid token", encoding="utf-8")
    with pytest.raises(OPAPolicyConfigurationError, match="printable"):
        OPAPolicyClient.from_environment(required=False)


@pytest.mark.asyncio
async def test_opa_client_sends_minimal_input_and_validates_decision(monkeypatch):
    requests = []

    async def respond(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "result": {
                    "allow": True,
                    "policy_version": "1.2.3",
                }
            },
        )

    client = OPAPolicyClient(
        endpoint="https://opa.internal/v1/data/sanctum/api/authz/decision",
        verify=True,
        bearer_token="operator-token",
        transport=AsyncMockTransport(respond),
    )
    policy_input = {
        "identity": {
            "authentication_method": "oidc",
            "tenant_id": "tenant-a",
            "roles": ["AUDITOR"],
        },
        "request": {"method": "POST", "route": "/api/v1/cases"},
    }

    decision = await client.evaluate(policy_input)

    assert decision == OPAPolicyDecision(allow=True, policy_version="1.2.3")
    assert requests[0].headers["Authorization"] == "Bearer operator-token"
    assert json.loads(requests[0].content) == {"input": policy_input}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(503),
        httpx.Response(200, json={"result": {"allow": 1, "policy_version": "1"}}),
        httpx.Response(200, json={"result": {"allow": True}}),
    ],
)
async def test_opa_client_fails_closed_on_unusable_responses(response):
    async def respond(_request):
        return response

    client = OPAPolicyClient(
        endpoint="https://opa.internal/v1/data/sanctum/api/authz/decision",
        verify=True,
        bearer_token=None,
        transport=AsyncMockTransport(respond),
    )

    with pytest.raises(OPAPolicyUnavailable):
        await client.evaluate({"identity": {}, "request": {}})


@pytest.mark.asyncio
async def test_opa_readiness_requires_a_denied_probe():
    async def respond(_request):
        return httpx.Response(
            200,
            json={"result": {"allow": False, "policy_version": "1.2.3"}},
        )

    client = OPAPolicyClient(
        endpoint="https://opa.internal/v1/data/sanctum/api/authz/decision",
        verify=True,
        bearer_token=None,
        transport=AsyncMockTransport(respond),
    )

    assert await client.verify_readiness() == "1.2.3"


def test_all_versioned_routes_use_authenticated_dependencies():
    for route in server.app.routes:
        if not getattr(route, "path", "").startswith("/api/v1/"):
            continue
        dependency_names = {
            getattr(dependency.call, "__name__", "")
            for dependency in route.dependant.dependencies
        }
        assert dependency_names & {"verify_api_key", "verify_event_source"}, (
            route.path,
            dependency_names,
        )


def test_readyz_reports_the_verified_opa_policy_version(monkeypatch):
    monkeypatch.delenv("SANCTUM_ENVIRONMENT", raising=False)
    monkeypatch.setenv("SANCTUM_API_KEY", "opa-readyz-test-key-" + "x" * 32)
    monkeypatch.setenv("SANCTUM_OPA_URL", "https://opa.internal")

    class ReadyPolicyClient:
        async def verify_readiness(self):
            return "1.2.3"

    monkeypatch.setattr(
        server,
        "get_opa_policy_client",
        lambda *, required: ReadyPolicyClient(),
    )
    response = TestClient(server.app).get("/readyz")

    assert response.status_code == 200
    assert response.json()["opa_policy_configured"] is True
    assert response.json()["opa_policy_version"] == "1.2.3"


def test_api_uses_opa_and_audits_decisions(monkeypatch, tmp_path):
    api_key = "opa-api-test-key-" + "x" * 32
    monkeypatch.setenv("SANCTUM_API_KEY", api_key)
    monkeypatch.setenv("SANCTUM_OPA_URL", "https://opa.internal")
    governance = IncidentGovernanceStore(tmp_path / "audit.sqlite3")
    monkeypatch.setattr(server, "incident_governance_store", governance)

    class FakePolicyClient:
        def __init__(self, allow):
            self.allow = allow
            self.inputs = []

        async def evaluate(self, policy_input):
            self.inputs.append(policy_input)
            return OPAPolicyDecision(self.allow, "1.2.3")

    policy_client = FakePolicyClient(False)
    monkeypatch.setattr(
        server, "get_opa_policy_client", lambda *, required: policy_client
    )
    client = TestClient(server.app)
    headers = {"X-API-Key": api_key}

    denied = client.get("/api/v1/frameworks", headers=headers)

    assert denied.status_code == 403
    assert policy_client.inputs[0]["request"] == {
        "method": "GET",
        "route": "/api/v1/frameworks",
    }
    denied_audit = governance.list_access()[0]
    assert denied_audit["authorization_engine"] == "opa"
    assert denied_audit["authorization_decision"] == "deny"
    assert denied_audit["authorization_policy_version"] == "1.2.3"

    policy_client.allow = True
    allowed = client.get("/api/v1/frameworks", headers=headers)

    assert allowed.status_code == 200
    allowed_audit = governance.list_access()[0]
    assert allowed_audit["authorization_engine"] == "opa+rbac"
    assert allowed_audit["authorization_decision"] == "allow"
    assert allowed_audit["authorization_policy_version"] == "1.2.3"


def test_api_fails_closed_and_audits_opa_outage(monkeypatch, tmp_path):
    api_key = "opa-api-test-key-" + "y" * 32
    monkeypatch.setenv("SANCTUM_API_KEY", api_key)
    governance = IncidentGovernanceStore(tmp_path / "audit.sqlite3")
    monkeypatch.setattr(server, "incident_governance_store", governance)

    class UnavailablePolicyClient:
        async def evaluate(self, _policy_input):
            raise OPAPolicyUnavailable("OPA timed out")

    monkeypatch.setattr(
        server,
        "get_opa_policy_client",
        lambda *, required: UnavailablePolicyClient(),
    )
    response = TestClient(server.app).get(
        "/api/v1/frameworks",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 503
    audit = governance.list_access()[0]
    assert audit["authorization_engine"] == "opa"
    assert audit["authorization_decision"] == "error"
    assert audit["authorization_policy_version"] is None


def test_opa_also_checks_source_key_telemetry_ingestion(monkeypatch, tmp_path):
    source_key = "event-source-key-" + "z" * 32
    monkeypatch.setenv("SANCTUM_EVENT_SOURCE_KEYS", json.dumps({"idp-1": source_key}))
    monkeypatch.setenv("SANCTUM_EVENT_RETENTION_DAYS", "30")
    governance = IncidentGovernanceStore(tmp_path / "audit.sqlite3")
    monkeypatch.setattr(server, "incident_governance_store", governance)

    class DenyPolicyClient:
        def __init__(self):
            self.policy_input = None

        async def evaluate(self, policy_input):
            self.policy_input = policy_input
            return OPAPolicyDecision(False, "1.2.3")

    policy_client = DenyPolicyClient()
    monkeypatch.setattr(
        server, "get_opa_policy_client", lambda *, required: policy_client
    )
    response = TestClient(server.app).post(
        "/api/v1/telemetry/ingest",
        headers={
            "X-Sanctum-Source-ID": "idp-1",
            "X-Sanctum-Source-Key": source_key,
        },
        json={
            "events": [
                {
                    "source_event_id": "event-1",
                    "event_type": "login_success",
                    "observed_at": "2026-10-19T12:00:00Z",
                }
            ]
        },
    )

    assert response.status_code == 403
    assert policy_client.policy_input["identity"]["authentication_method"] == (
        "event_source"
    )
    assert policy_client.policy_input["request"]["route"] == (
        "/api/v1/telemetry/ingest"
    )
    audit = governance.list_access()[0]
    assert audit["authorization_engine"] == "opa"
    assert audit["authorization_decision"] == "deny"
