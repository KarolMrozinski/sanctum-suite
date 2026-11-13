from fastapi.testclient import TestClient

from sanctum_suite.api import server
from sanctum_suite.core.incident_governance import IncidentGovernanceStore
from sanctum_suite.core.synthetic_incident_lab import SyntheticIncidentLab


def test_scenarios_are_fictional_and_return_correlated_in_memory_events():
    lab = SyntheticIncidentLab()

    scenarios = lab.list_scenarios()
    assert len(scenarios) >= 2
    assert all(scenario["data_classification"] == "SYNTHETIC" for scenario in scenarios)
    assert all(scenario["external_connections"] is False for scenario in scenarios)
    assert all(scenario["writes_case_data"] is False for scenario in scenarios)

    result = lab.run("identity-change-review")

    assert result is not None
    assert result["status"] == "SYNTHETIC_DEMO_ONLY"
    assert result["persisted"] is False
    assert result["external_connections"] is False
    assert len(result["events"]) == 3
    assert len(result["correlations"]) == 1
    assert result["correlations"][0]["synthetic"] is True
    assert all(event["source"].startswith("synthetic-") for event in result["events"])
    assert all(event["event_id"].startswith("SYN-") for event in result["events"])
    assert all(
        event["correlation_key"].startswith("SYNTHETIC-identity-change-review-")
        for event in result["events"]
    )
    assert lab.run("unknown-scenario") is None


def test_synthetic_scenario_run_data_is_not_persisted(tmp_path):
    audit_store = IncidentGovernanceStore(tmp_path / "empty-lab.sqlite3")
    lab = SyntheticIncidentLab()

    first_run = lab.run("service-configuration-review")
    second_run = lab.run("service-configuration-review")

    assert first_run is not None and second_run is not None
    assert first_run["run_id"] != second_run["run_id"]
    assert first_run["events"][0]["event_id"] != second_run["events"][0]["event_id"]
    assert audit_store.list_access() == []


def test_synthetic_lab_api_is_authenticated_and_audited(monkeypatch, tmp_path):
    api_key = "synthetic-lab-test-key-" + "x" * 32
    monkeypatch.setenv("SANCTUM_API_KEY", api_key)
    monkeypatch.delenv("SANCTUM_CASE_RETENTION_DAYS", raising=False)
    monkeypatch.delenv("SANCTUM_ACCESS_AUDIT_RETENTION_DAYS", raising=False)
    governance = IncidentGovernanceStore(tmp_path / "lab-api.sqlite3")
    monkeypatch.setattr(server, "incident_case_store", None)
    monkeypatch.setattr(server, "incident_governance_store", governance)
    client = TestClient(server.app)

    assert client.get("/api/v1/lab/scenarios").status_code == 401
    headers = {"X-API-Key": api_key}
    catalog = client.get("/api/v1/lab/scenarios", headers=headers)
    assert catalog.status_code == 200
    assert catalog.json()["status"] == "SYNTHETIC_DEMO_ONLY"

    result = client.post(
        "/api/v1/lab/scenarios/identity-change-review/run",
        headers=headers,
    )
    assert result.status_code == 200
    assert result.json()["persisted"] is False
    assert client.post(
        "/api/v1/lab/scenarios/not-a-scenario/run",
        headers=headers,
    ).status_code == 404

    audit = client.get("/api/v1/governance/access-log", headers=headers)
    actions = [record["action"] for record in audit.json()["records"]]
    assert "GET /api/v1/lab/scenarios" in actions
    assert "POST /api/v1/lab/scenarios/{scenario_id}/run" in actions
