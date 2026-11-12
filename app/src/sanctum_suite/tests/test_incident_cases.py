import pytest
from fastapi.testclient import TestClient

from sanctum_suite.api import server
from sanctum_suite.core.incident_cases import IncidentCaseStore


def test_case_store_persists_assignment_notes_evidence_and_timeline(tmp_path):
    database = tmp_path / "cases.sqlite3"
    store = IncidentCaseStore(database)
    created = store.create_case(
        title="Unusual privilege change",
        summary="Review the correlated identity events.",
        created_by="analyst-1",
        priority="HIGH",
        correlation_id="LOCAL-CORR-12345678",
        priority_reasons=["Source-reported HIGH severity."],
        timeline=[
            {
                "event_id": "evt-2",
                "event_type": "privilege-change",
                "source": "identity-provider",
                "observed_at": "2026-10-18T10:02:00Z",
                "reported_severity": "HIGH",
            },
            {
                "event_id": "evt-1",
                "event_type": "login",
                "source": "gateway",
                "observed_at": "2026-10-18T10:00:00Z",
                "reported_severity": None,
            },
        ],
    )

    store.update_case(
        created["case_id"], status="in_progress", assigned_to="analyst-2"
    )
    store.add_note(created["case_id"], author="analyst-2", body="Review started.")
    store.add_evidence(
        created["case_id"],
        source="identity-provider",
        reference="artifact://case-123/audit",
        added_by="analyst-2",
        sha256="a" * 64,
    )

    reopened = IncidentCaseStore(database).get_case(created["case_id"])
    assert reopened is not None
    assert reopened["status"] == "in_progress"
    assert reopened["assigned_to"] == "analyst-2"
    assert [event["event_id"] for event in reopened["timeline"]] == ["evt-1", "evt-2"]
    assert reopened["notes"][0]["body"] == "Review started."
    assert reopened["evidence"][0]["sha256"] == "a" * 64
    assert "raw" not in reopened["evidence"][0]


def test_case_store_rejects_duplicate_correlation_and_invalid_updates(tmp_path):
    store = IncidentCaseStore(tmp_path / "cases.sqlite3")
    store.create_case(
        title="Case one",
        summary="Review this case.",
        created_by="analyst",
        correlation_id="correlation-1",
    )

    with pytest.raises(ValueError, match="already exists"):
        store.create_case(
            title="Duplicate",
            summary="Duplicate correlation.",
            created_by="analyst",
            correlation_id="correlation-1",
        )
    with pytest.raises(ValueError, match="At least one"):
        store.update_case("missing")
    with pytest.raises(ValueError, match="sha256"):
        store.add_evidence(
            "missing",
            source="test",
            reference="artifact://test",
            added_by="analyst",
            sha256="not-a-digest",
        )


def test_case_api_requires_authentication_and_supports_case_workflow(
    monkeypatch, tmp_path
):
    api_key = "case-management-test-key-" + "x" * 32
    monkeypatch.setenv("SANCTUM_API_KEY", api_key)
    monkeypatch.setattr(
        server, "incident_case_store", IncidentCaseStore(tmp_path / "api-cases.sqlite3")
    )
    client = TestClient(server.app)
    headers = {"X-API-Key": api_key}
    payload = {
        "title": "Suspicious sign-in sequence",
        "summary": "Investigate the reported identity events.",
        "created_by": "analyst-1",
        "priority": "HIGH",
        "correlation_id": "LOCAL-CORR-ABCDEF12",
        "priority_reasons": ["Two events share the correlation key."],
        "timeline": [
            {
                "event_id": "evt-1",
                "event_type": "login",
                "source": "gateway",
                "observed_at": "2026-10-18T10:00:00Z",
                "reported_severity": "MEDIUM",
            },
            {
                "event_id": "evt-2",
                "event_type": "privilege-change",
                "source": "identity-provider",
                "observed_at": "2026-10-18T10:01:00Z",
                "reported_severity": "HIGH",
            },
        ],
    }

    assert client.get("/api/v1/cases").status_code == 401
    created = client.post("/api/v1/cases", headers=headers, json=payload)
    assert created.status_code == 201
    case_id = created.json()["case_id"]
    assert created.json()["event_count"] == 2
    assert client.post("/api/v1/cases", headers=headers, json=payload).status_code == 409

    updated = client.patch(
        f"/api/v1/cases/{case_id}",
        headers=headers,
        json={"status": "in_progress", "assigned_to": "analyst-2"},
    )
    assert updated.status_code == 200
    assert updated.json()["assigned_to"] == "analyst-2"
    assert client.patch(
        f"/api/v1/cases/{case_id}", headers=headers, json={}
    ).status_code == 422

    note = client.post(
        f"/api/v1/cases/{case_id}/notes",
        headers=headers,
        json={"author": "analyst-2", "body": "Reviewing source evidence."},
    )
    assert note.status_code == 201
    evidence = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        headers=headers,
        json={
            "source": "identity-provider",
            "reference": "artifact://case-1/audit",
            "added_by": "analyst-2",
            "sha256": "b" * 64,
        },
    )
    assert evidence.status_code == 201

    fetched = client.get(f"/api/v1/cases/{case_id}", headers=headers)
    assert fetched.json()["notes"][0]["body"] == "Reviewing source evidence."
    assert fetched.json()["evidence"][0]["reference"] == "artifact://case-1/audit"
    assert len(client.get("/api/v1/cases?status=in_progress", headers=headers).json()["cases"]) == 1
    assert client.get("/api/v1/cases/missing", headers=headers).status_code == 404


def test_case_api_rejects_invalid_timeline_and_evidence(monkeypatch, tmp_path):
    api_key = "case-validation-test-key-" + "x" * 32
    monkeypatch.setenv("SANCTUM_API_KEY", api_key)
    monkeypatch.setattr(
        server, "incident_case_store", IncidentCaseStore(tmp_path / "validation-cases.sqlite3")
    )
    client = TestClient(server.app)
    headers = {"X-API-Key": api_key}
    payload = {
        "title": "Case",
        "summary": "Summary",
        "created_by": "analyst",
        "correlation_id": "correlation-1",
        "timeline": [
            {
                "event_id": "evt-1",
                "event_type": "login",
                "observed_at": "2026-10-18T10:00:00",
            }
        ],
    }
    assert client.post("/api/v1/cases", headers=headers, json=payload).status_code == 422

    payload["timeline"][0]["observed_at"] = "2026-10-18T10:00:00Z"
    created = client.post("/api/v1/cases", headers=headers, json=payload)
    assert created.status_code == 201
    evidence = client.post(
        f"/api/v1/cases/{created.json()['case_id']}/evidence",
        headers=headers,
        json={
            "source": "test",
            "reference": "artifact://test",
            "added_by": "analyst",
            "sha256": "bad",
        },
    )
    assert evidence.status_code == 422


def test_correlated_event_result_can_be_saved_as_a_case(monkeypatch, tmp_path):
    api_key = "correlation-case-test-key-" + "x" * 32
    monkeypatch.setenv("SANCTUM_API_KEY", api_key)
    monkeypatch.setattr(
        server,
        "incident_case_store",
        IncidentCaseStore(tmp_path / "correlated-cases.sqlite3"),
    )
    client = TestClient(server.app)
    headers = {"X-API-Key": api_key}
    correlation_response = client.post(
        "/api/v1/events/correlate",
        headers=headers,
        json={
            "events": [
                {
                    "event_id": "evt-1",
                    "event_type": "login",
                    "correlation_key": "case-key",
                    "observed_at": "2026-10-18T10:00:00Z",
                },
                {
                    "event_id": "evt-2",
                    "event_type": "privilege-change",
                    "correlation_key": "case-key",
                    "observed_at": "2026-10-18T10:01:00+01:00",
                    "severity": "HIGH",
                },
            ]
        },
    )

    correlation = correlation_response.json()["correlations"][0]
    case_response = client.post(
        "/api/v1/cases",
        headers=headers,
        json={
            "title": "Correlated identity activity",
            "summary": "Review source-reported events.",
            "created_by": "analyst",
            "priority": correlation["priority"],
            "correlation_id": correlation["correlation_id"],
            "priority_reasons": correlation["priority_reasons"],
            "timeline": correlation["timeline"],
        },
    )

    assert case_response.status_code == 201
    assert case_response.json()["correlation_id"] == correlation["correlation_id"]
    assert [event["event_id"] for event in case_response.json()["timeline"]] == [
        "evt-2",
        "evt-1",
    ]
