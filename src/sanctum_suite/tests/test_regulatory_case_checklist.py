import sqlite3

import pytest
from fastapi.testclient import TestClient

from sanctum_suite.api import server
from sanctum_suite.core.incident_cases import IncidentCaseStore
from sanctum_suite.core.regulatory_case_checklist import (
    CONTROLS,
    RegulatoryCaseChecklistStore,
)


def create_case(store: IncidentCaseStore, title: str = "AML/MiCA case") -> str:
    case = store.create_case(
        title=title,
        summary="Review regulatory applicability and retain evidence references.",
        created_by="analyst",
    )
    return case["case_id"]


def test_checklist_is_case_scoped_starts_unassessed_and_tracks_evidence(tmp_path):
    database = tmp_path / "cases.sqlite3"
    cases = IncidentCaseStore(database)
    case_id = create_case(cases)
    other_case_id = create_case(cases, "Separate regulatory case")
    checklist_store = RegulatoryCaseChecklistStore(database)

    checklist = checklist_store.get_checklist(case_id)
    assert checklist["profile"] == "EU_CASP"
    assert checklist["overall_status"] == "NOT_ASSESSED"
    assert {control["control_id"] for control in checklist["controls"]} == {
        control.control_id for control in CONTROLS
    }
    assert all(
        control["applicability"] == "not_assessed"
        and control["review_state"] == "not_assessed"
        for control in checklist["controls"]
    )

    with pytest.raises(ValueError, match="requires at least one evidence reference"):
        checklist_store.update_control(
            case_id,
            "EU-MICA-PERIMETER",
            updated_by="analyst",
            review_state="evidence_recorded",
        )
    with pytest.raises(ValueError, match="rationale"):
        checklist_store.update_control(
            case_id,
            "EU-MICA-PERIMETER",
            updated_by="analyst",
            applicability="out_of_scope",
        )

    updated = checklist_store.update_control(
        case_id,
        "EU-MICA-PERIMETER",
        updated_by="analyst",
        applicability="out_of_scope",
        summary="Qualified counsel determined this entity is outside the CASP perimeter.",
    )
    assert updated["overall_status"] == "NOT_ASSESSED"
    perimeter = next(
        item for item in updated["controls"] if item["control_id"] == "EU-MICA-PERIMETER"
    )
    assert perimeter["applicability"] == "out_of_scope"
    assert perimeter["review_state"] == "not_assessed"

    evidence = checklist_store.add_evidence(
        case_id,
        "EU-MICA-PERIMETER",
        source="legal-review",
        reference="artifact://case/legal-memo",
        sha256="a" * 64,
        recorded_by="analyst",
    )
    perimeter_with_evidence = next(
        item for item in evidence["controls"] if item["control_id"] == "EU-MICA-PERIMETER"
    )
    assert perimeter_with_evidence["review_state"] == "evidence_recorded"
    assert perimeter_with_evidence["evidence"][0]["sha256"] == "a" * 64

    other_case = checklist_store.get_checklist(other_case_id)
    other_perimeter = next(
        item
        for item in other_case["controls"]
        if item["control_id"] == "EU-MICA-PERIMETER"
    )
    assert other_perimeter["evidence"] == []
    assert other_perimeter["applicability"] == "not_assessed"

    checklist_store.update_control(
        case_id,
        "EU-MICA-PERIMETER",
        updated_by="reviewer",
        review_state="needs_review",
    )
    checklist_store.add_evidence(
        case_id,
        "EU-MICA-PERIMETER",
        source="additional-review",
        reference="artifact://case/follow-up",
        sha256="b" * 64,
        recorded_by="reviewer",
    )
    final = checklist_store.get_checklist(case_id)
    perimeter_final = next(
        item for item in final["controls"] if item["control_id"] == "EU-MICA-PERIMETER"
    )
    assert perimeter_final["review_state"] == "needs_review"
    assert len(perimeter_final["evidence"]) == 2

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("DELETE FROM incident_cases WHERE case_id = ?", (case_id,))
        evidence_left = connection.execute(
            "SELECT COUNT(*) FROM regulatory_case_evidence WHERE case_id = ?",
            (case_id,),
        ).fetchone()[0]
        controls_left = connection.execute(
            "SELECT COUNT(*) FROM regulatory_case_controls WHERE case_id = ?",
            (case_id,),
        ).fetchone()[0]
    assert evidence_left == 0
    assert controls_left == 0


def test_aml_mica_case_checklist_api_requires_auth_and_keeps_evidence_refs_only(
    monkeypatch,
    tmp_path,
):
    api_key = "regulatory-checklist-test-key-" + "x" * 32
    monkeypatch.setenv("SANCTUM_API_KEY", api_key)
    monkeypatch.setattr(
        server,
        "incident_case_store",
        IncidentCaseStore(tmp_path / "cases.sqlite3"),
    )
    monkeypatch.setattr(server, "regulatory_case_checklist_store", None)
    monkeypatch.setattr(server, "_tenant_regulatory_case_checklist_stores", {})
    monkeypatch.delenv("SANCTUM_TENANT_DATABASE_ROOT", raising=False)
    case_id = create_case(server.get_incident_case_store())
    client = TestClient(server.app)
    checklist_url = f"/api/v1/cases/{case_id}/aml-mica-checklist"

    assert client.get(checklist_url).status_code == 401
    headers = {"X-API-Key": api_key}
    checklist = client.get(checklist_url, headers=headers)
    assert checklist.status_code == 200, checklist.text
    assert checklist.json()["overall_status"] == "NOT_ASSESSED"
    assert len(checklist.json()["controls"]) == len(CONTROLS)

    evidence_response = client.post(
        f"{checklist_url}/EU-TFR-TRANSFER-INFO/evidence",
        headers=headers,
        json={
            "source": "transfer-rule-review",
            "reference": "artifact://case/tfr-control-review",
            "sha256": "c" * 64,
            "recorded_by": "analyst",
        },
    )
    assert evidence_response.status_code == 201, evidence_response.text
    result = evidence_response.json()
    tfr = next(
        item for item in result["controls"] if item["control_id"] == "EU-TFR-TRANSFER-INFO"
    )
    assert tfr["review_state"] == "evidence_recorded"
    assert tfr["evidence"][0]["reference"] == "artifact://case/tfr-control-review"
    assert "uploaded_content" not in tfr["evidence"][0]
    assert result["overall_status"] == "NOT_ASSESSED"

    out_of_scope = client.patch(
        f"{checklist_url}/PL-AML-SCOPE",
        headers=headers,
        json={
            "updated_by": "analyst",
            "applicability": "out_of_scope",
            "summary": "Written applicability rationale attached for qualified review.",
        },
    )
    assert out_of_scope.status_code == 200, out_of_scope.text

    invalid = client.post(
        f"{checklist_url}/EU-AMLR-APPLICABILITY/evidence",
        headers=headers,
        json={
            "source": "source",
            "reference": "private reference",
            "sha256": "NOT-A-DIGEST",
            "recorded_by": "analyst",
        },
    )
    assert invalid.status_code == 422
    assert "private reference" not in invalid.text

    missing_case = client.get(
        "/api/v1/cases/not-a-case/aml-mica-checklist",
        headers=headers,
    )
    assert missing_case.status_code == 404
    unknown_control = client.patch(
        f"{checklist_url}/UNKNOWN",
        headers=headers,
        json={"updated_by": "analyst", "review_state": "needs_review"},
    )
    assert unknown_control.status_code == 404
