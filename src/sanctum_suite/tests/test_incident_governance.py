import hashlib
import sqlite3
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from sanctum_suite.api import server
from sanctum_suite.core.incident_cases import IncidentCaseStore
from sanctum_suite.core.incident_governance import IncidentGovernanceStore
from sanctum_suite.core.incident_playbooks import IncidentPlaybookStore


def test_case_retention_only_deletes_old_resolved_cases_and_cascades(tmp_path):
    database = tmp_path / "retention.sqlite3"
    cases = IncidentCaseStore(database)
    governance = IncidentGovernanceStore(database)
    resolved = cases.create_case(
        title="Resolved case",
        summary="Eligible for configured retention.",
        created_by="analyst",
        timeline=[{"event_id": "event-1", "event_type": "login"}],
    )
    open_case = cases.create_case(
        title="Open case",
        summary="Must not be deleted by retention.",
        created_by="analyst",
    )
    cases.update_case(resolved["case_id"], status="resolved")
    playbooks = IncidentPlaybookStore(database)
    plan = playbooks.simulate(resolved["case_id"], simulated_by="analyst")
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE incident_cases SET updated_at = ? WHERE case_id IN (?, ?)",
            (
                (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
                resolved["case_id"],
                open_case["case_id"],
            ),
        )

    result = governance.apply_retention(case_retention_days=2)

    assert result == {"cases_deleted": 1, "audit_records_deleted": 0}
    assert cases.get_case(resolved["case_id"]) is None
    assert cases.get_case(open_case["case_id"]) is not None
    assert playbooks.get_plan(plan["plan_id"]) is None
    assert governance.list_access()[0]["record_type"] == "retention"


def test_audit_retention_is_disabled_by_default_and_explicit_when_configured(tmp_path):
    governance = IncidentGovernanceStore(tmp_path / "audit-retention.sqlite3")
    governance.record_access(
        credential_fingerprint="a" * 16,
        action="GET /api/v1/cases",
        outcome_code=200,
    )
    with sqlite3.connect(governance.db_path) as connection:
        connection.execute(
            "UPDATE incident_access_audit SET occurred_at = ?",
            ((datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),),
        )

    assert governance.apply_retention() == {
        "cases_deleted": 0,
        "audit_records_deleted": 0,
    }
    assert len(governance.list_access()) == 1
    assert governance.apply_retention(audit_retention_days=2) == {
        "cases_deleted": 0,
        "audit_records_deleted": 1,
    }
    assert governance.list_access() == []


def test_access_audit_records_only_credential_fingerprint_and_route_metadata(
    monkeypatch, tmp_path
):
    database = tmp_path / "audit.sqlite3"
    cases = IncidentCaseStore(database)
    governance = IncidentGovernanceStore(database)
    api_key = "governance-audit-test-key-" + "x" * 32
    monkeypatch.setenv("SANCTUM_API_KEY", api_key)
    monkeypatch.setattr(server, "incident_case_store", cases)
    monkeypatch.setattr(server, "incident_governance_store", governance)
    client = TestClient(server.app)
    headers = {"X-API-Key": api_key}
    case = client.post(
        "/api/v1/cases",
        headers=headers,
        json={
            "title": "Sensitive body must not be logged",
            "summary": "Private summary must not be logged.",
            "created_by": "unverified-label",
        },
    )
    assert case.status_code == 201
    assert client.get(
        f"/api/v1/cases/{case.json()['case_id']}",
        headers=headers,
    ).status_code == 200

    audit_response = client.get(
        "/api/v1/governance/access-log?limit=20",
        headers=headers,
    )

    assert audit_response.status_code == 200
    assert "not an individual" in audit_response.json()["limitations"]
    records = audit_response.json()["records"]
    assert any(record["action"] == "GET /api/v1/cases/{case_id}" for record in records)
    assert any(record["action"] == "POST /api/v1/cases" for record in records)
    assert all(
        record["credential_fingerprint"]
        == hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]
        for record in records
        if record["record_type"] == "api_access"
    )
    encoded_records = str(records)
    assert api_key not in encoded_records
    assert "Sensitive body" not in encoded_records
    assert "Private summary" not in encoded_records


def test_configured_retention_runs_on_authenticated_case_access(monkeypatch, tmp_path):
    database = tmp_path / "api-retention.sqlite3"
    cases = IncidentCaseStore(database)
    governance = IncidentGovernanceStore(database)
    monkeypatch.setattr(server, "incident_case_store", cases)
    monkeypatch.setattr(server, "incident_governance_store", governance)
    monkeypatch.setenv("SANCTUM_API_KEY", "retention-api-test-key-" + "x" * 32)
    monkeypatch.setenv("SANCTUM_CASE_RETENTION_DAYS", "1")
    monkeypatch.delenv("SANCTUM_ACCESS_AUDIT_RETENTION_DAYS", raising=False)
    case = cases.create_case(
        title="Old closed case",
        summary="This case should expire.",
        created_by="analyst",
    )
    cases.update_case(case["case_id"], status="closed")
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE incident_cases SET updated_at = ? WHERE case_id = ?",
            (
                (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
                case["case_id"],
            ),
        )

    response = TestClient(server.app).get(
        "/api/v1/cases",
        headers={"X-API-Key": "retention-api-test-key-" + "x" * 32},
    )

    assert response.status_code == 200
    assert cases.get_case(case["case_id"]) is None
    assert any(record["record_type"] == "retention" for record in governance.list_access())


def test_invalid_retention_configuration_fails_closed(monkeypatch, tmp_path):
    database = tmp_path / "invalid-retention.sqlite3"
    monkeypatch.setattr(server, "incident_case_store", IncidentCaseStore(database))
    monkeypatch.setattr(
        server, "incident_governance_store", IncidentGovernanceStore(database)
    )
    api_key = "invalid-retention-api-key-" + "x" * 32
    monkeypatch.setenv("SANCTUM_API_KEY", api_key)
    monkeypatch.setenv("SANCTUM_CASE_RETENTION_DAYS", "0")

    response = TestClient(server.app).get(
        "/api/v1/cases",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "SANCTUM_CASE_RETENTION_DAYS must be between 1 and 36500 days"


def test_explicit_retention_endpoint_reports_deletions_once(monkeypatch, tmp_path):
    database = tmp_path / "manual-retention.sqlite3"
    cases = IncidentCaseStore(database)
    governance = IncidentGovernanceStore(database)
    monkeypatch.setattr(server, "incident_case_store", cases)
    monkeypatch.setattr(server, "incident_governance_store", governance)
    api_key = "manual-retention-api-key-" + "x" * 32
    monkeypatch.setenv("SANCTUM_API_KEY", api_key)
    monkeypatch.setenv("SANCTUM_CASE_RETENTION_DAYS", "1")
    monkeypatch.delenv("SANCTUM_ACCESS_AUDIT_RETENTION_DAYS", raising=False)
    case = cases.create_case(
        title="Expired resolved case",
        summary="Delete according to configured retention.",
        created_by="analyst",
    )
    cases.update_case(case["case_id"], status="resolved")
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE incident_cases SET updated_at = ? WHERE case_id = ?",
            (
                (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
                case["case_id"],
            ),
        )

    response = TestClient(server.app).post(
        "/api/v1/governance/retention/purge",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    assert response.json()["deleted"]["cases_deleted"] == 1
    assert response.json()["policy"]["case_retention_days"] == 1
    assert cases.get_case(case["case_id"]) is None
