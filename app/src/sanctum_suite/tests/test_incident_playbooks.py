import pytest
from fastapi.testclient import TestClient

from sanctum_suite.api import server
from sanctum_suite.core.incident_cases import IncidentCaseStore
from sanctum_suite.core.incident_playbooks import IncidentPlaybookStore


def test_simulated_playbook_is_persisted_without_executing_actions(tmp_path):
    database = tmp_path / "cases.sqlite3"
    cases = IncidentCaseStore(database)
    case = cases.create_case(
        title="Privilege change review",
        summary="Review the reported access activity.",
        created_by="analyst-1",
        priority="HIGH",
        timeline=[
            {
                "event_id": "evt-1",
                "event_type": "privilege-change",
                "source": "identity-provider",
                "observed_at": "2026-10-18T10:00:00Z",
                "reported_severity": "HIGH",
            }
        ],
    )

    store = IncidentPlaybookStore(database)
    plan = store.simulate(case["case_id"], simulated_by="analyst-1")
    reopened = IncidentPlaybookStore(database).get_plan(plan["plan_id"])

    assert reopened is not None
    assert reopened["status"] == "simulated"
    assert reopened["execution_status"] == "NOT_EXECUTED"
    assert reopened["case_snapshot"]["priority"] == "HIGH"
    assert any(step["step_id"] == "review-access-records" for step in reopened["steps"])
    assert all("command" not in step for step in reopened["steps"])
    assert reopened["decisions"] == []


def test_playbook_decisions_are_append_only_and_never_execute(tmp_path):
    database = tmp_path / "cases.sqlite3"
    case = IncidentCaseStore(database).create_case(
        title="Case",
        summary="Review the case.",
        created_by="analyst",
    )
    store = IncidentPlaybookStore(database)
    plan = store.simulate(case["case_id"], simulated_by="analyst")

    approved = store.record_decision(
        plan["plan_id"],
        decision="approve",
        reviewer="reviewer-1",
        rationale="Approved for manual review under the change process.",
    )
    rejected = store.record_decision(
        plan["plan_id"],
        decision="reject",
        reviewer="reviewer-2",
        rationale="Re-review rejected pending additional evidence.",
    )

    assert approved["status"] == "approved_for_manual_review"
    assert rejected["status"] == "rejected"
    assert rejected["execution_status"] == "NOT_EXECUTED"
    assert [item["decision"] for item in rejected["decisions"]] == ["approve", "reject"]
    with pytest.raises(ValueError, match="rationale"):
        store.record_decision(
            plan["plan_id"],
            decision="approve",
            reviewer="reviewer-1",
            rationale=" ",
        )
    with pytest.raises(ValueError, match="decision"):
        store.record_decision(
            plan["plan_id"],
            decision="execute",
            reviewer="reviewer-1",
            rationale="Attempted execution is not a supported decision.",
        )


def test_playbook_api_requires_authentication_and_records_operator_decisions(
    monkeypatch, tmp_path
):
    api_key = "playbook-test-key-" + "x" * 32
    monkeypatch.setenv("SANCTUM_API_KEY", api_key)
    database = tmp_path / "api-cases.sqlite3"
    monkeypatch.setattr(server, "incident_case_store", IncidentCaseStore(database))
    monkeypatch.setattr(
        server, "incident_playbook_store", IncidentPlaybookStore(database)
    )
    client = TestClient(server.app)
    headers = {"X-API-Key": api_key}
    case = client.post(
        "/api/v1/cases",
        headers=headers,
        json={
            "title": "Login review",
            "summary": "Review the sign-in timeline.",
            "created_by": "analyst",
            "priority": "MEDIUM",
            "timeline": [
                {
                    "event_id": "evt-1",
                    "event_type": "login",
                    "observed_at": "2026-10-18T10:00:00Z",
                }
            ],
        },
    ).json()
    path = f"/api/v1/cases/{case['case_id']}/playbooks"

    assert client.post(f"{path}/simulate", json={"simulated_by": "analyst"}).status_code == 401
    simulated = client.post(
        f"{path}/simulate",
        headers=headers,
        json={"simulated_by": "analyst"},
    )
    assert simulated.status_code == 201
    plan = simulated.json()
    assert plan["status"] == "simulated"
    assert plan["execution_status"] == "NOT_EXECUTED"

    listed = client.get(path, headers=headers)
    assert listed.status_code == 200
    assert [item["plan_id"] for item in listed.json()["playbooks"]] == [plan["plan_id"]]

    decision = client.post(
        f"/api/v1/playbooks/{plan['plan_id']}/decisions",
        headers=headers,
        json={
            "decision": "approve",
            "reviewer": "incident-lead",
            "rationale": "Approved for manual review only.",
        },
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "approved_for_manual_review"
    assert decision.json()["execution_status"] == "NOT_EXECUTED"
    assert decision.json()["decisions"][0]["reviewer"] == "incident-lead"

    assert client.get("/api/v1/playbooks/missing", headers=headers).status_code == 404
    assert client.post(
        f"/api/v1/playbooks/{plan['plan_id']}/execute",
        headers=headers,
    ).status_code == 404
    assert client.post(
        f"/api/v1/playbooks/{plan['plan_id']}/decisions",
        headers=headers,
        json={"decision": "approve", "reviewer": "lead", "rationale": ""},
    ).status_code == 422
