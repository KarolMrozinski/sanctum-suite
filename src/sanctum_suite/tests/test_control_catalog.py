import hashlib
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from sanctum_suite.api import server
from sanctum_suite.core.control_catalog import (
    AssessmentState,
    ControlCatalog,
    EvidenceInput,
)


def test_catalog_has_versioned_framework_references():
    controls = ControlCatalog.list_controls()
    assert controls
    assert any(
        reference["framework"] == "OWASP ASVS" and reference["version"] == "5.0.0"
        for control in controls
        for reference in control["references"]
    )
    assert any(
        reference["framework"] == "NIST CSF" and reference["version"] == "2.0"
        for control in controls
        for reference in control["references"]
    )
    assert any(
        reference["framework"] == "CWE Top 25" and reference["version"] == "2025"
        for control in controls
        for reference in control["references"]
    )


def test_assessment_requires_evidence_when_verified(tmp_path):
    catalog = ControlCatalog(tmp_path / "controls.db")

    with pytest.raises(ValueError, match="requires at least one evidence reference"):
        catalog.create_assessment(
            "APP-VULN-001",
            AssessmentState.VERIFIED,
            "Verified",
            "analyst@example.test",
            [],
        )


def test_assessments_store_references_not_evidence_content(tmp_path):
    catalog = ControlCatalog(tmp_path / "controls.db")
    evidence = EvidenceInput(
        source="test-report",
        reference="artifact://audit-1/report",
        sha256=ControlCatalog.evidence_digest(b"evidence content"),
    )

    assessment = catalog.create_assessment(
        "APP-VULN-001",
        AssessmentState.VERIFIED,
        "Retest confirms the finding is fixed.",
        "analyst@example.test",
        [evidence],
    )

    assert assessment["state"] == "verified"
    assert assessment["evidence"][0]["sha256"] == evidence.sha256
    assert "evidence content" not in ControlCatalog.export_assessment(assessment)
    assert catalog.list_assessments("APP-VULN-001")[0]["assessment_id"] == assessment["assessment_id"]


def test_coverage_report_is_versioned_and_preserves_mapping_history(tmp_path):
    database = tmp_path / "coverage.db"
    catalog = ControlCatalog(database)
    initial_report = catalog.get_coverage_report(framework="CWE Top 25")
    initial_history = catalog.list_mapping_history(framework="CWE Top 25")

    assert initial_report["catalog_version"] == "1.0.0"
    assert initial_report["certification_status"] == "NOT_ASSESSED"
    assert initial_report["mappings"]
    assert initial_report["state_counts"]["not_assessed"] == len(
        initial_report["mappings"]
    )
    assert all(
        mapping["mapping_interpretation"] == "RELATED_NOT_EQUIVALENT"
        for mapping in initial_report["mappings"]
    )

    assessment = catalog.create_assessment(
        "APP-VULN-001",
        AssessmentState.VERIFIED,
        "Operator reviewed the scoped vulnerability process.",
        "assessor-1",
        [
            EvidenceInput(
                source="approved-test",
                reference="artifact://coverage/evidence",
                sha256="a" * 64,
            )
        ],
    )
    updated_report = catalog.get_coverage_report(framework="CWE Top 25")
    matching_control = next(
        row
        for row in updated_report["mappings"]
        if row["control_id"] == "APP-VULN-001"
    )
    assert matching_control["assessment_state"] == "verified"
    assert matching_control["assessment_id"] == assessment["assessment_id"]
    assert matching_control["assessment_catalog_version"] == "1.0.0"
    assert updated_report["state_counts"]["verified"] == 1
    assert "not independently" in " ".join(updated_report["limitations"])

    ControlCatalog(database)
    assert catalog.list_mapping_history(framework="CWE Top 25") == initial_history
    assert sqlite3.connect(database).execute(
        "SELECT catalog_version FROM control_assessments WHERE assessment_id = ?",
        (assessment["assessment_id"],),
    ).fetchone() == ("1.0.0",)


def test_existing_assessment_database_migrates_to_catalog_version(tmp_path):
    database = tmp_path / "legacy-controls.db"
    legacy_assessment_id = "legacy-assessment"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE control_assessments (
                assessment_id TEXT PRIMARY KEY,
                control_id TEXT NOT NULL,
                state TEXT NOT NULL,
                summary TEXT NOT NULL,
                assessed_by TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE control_evidence (
                evidence_id TEXT PRIMARY KEY,
                assessment_id TEXT NOT NULL REFERENCES control_assessments(assessment_id)
                    ON DELETE CASCADE,
                source TEXT NOT NULL,
                reference TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO control_assessments VALUES (?, ?, ?, ?, ?, ?)",
            (
                legacy_assessment_id,
                "APP-VULN-001",
                "needs_review",
                "Legacy record",
                "assessor",
                "2026-10-18T10:00:00+00:00",
            ),
        )

    catalog = ControlCatalog(database)
    legacy_assessment = catalog.get_assessment(legacy_assessment_id)
    assert legacy_assessment is not None
    assert legacy_assessment["catalog_version"] == "1.0.0"
    assert catalog.get_coverage_report()["mapping_count"] > 0


def test_control_assessment_api_is_authenticated_and_fail_closed(monkeypatch, tmp_path):
    monkeypatch.setenv("SANCTUM_API_KEY", "test-key-" + "x" * 32)
    monkeypatch.delenv("SANCTUM_AUTHORIZED_TARGETS", raising=False)
    monkeypatch.setattr(server, "control_catalog", ControlCatalog(tmp_path / "api-controls.db"))
    client = TestClient(server.app)
    payload = {
        "state": "verified",
        "summary": "The scoped control was independently retested.",
        "assessed_by": "test-analyst",
        "evidence": [{
            "source": "test",
            "reference": "artifact://test/evidence",
            "sha256": "a" * 64,
        }],
    }

    assert client.get("/api/v1/controls").status_code == 401
    headers = {"X-API-Key": "test-key-" + "x" * 32}
    controls_response = client.get("/api/v1/controls", headers=headers)
    assert controls_response.status_code == 200
    assert controls_response.json()["catalog_version"] == "1.0.0"
    assert client.get("/api/v1/controls/coverage").status_code == 401
    coverage = client.get("/api/v1/controls/coverage", headers=headers)
    assert coverage.status_code == 200
    coverage_report = coverage.json()
    report_digest = coverage_report.pop("report_sha256")
    assert report_digest == hashlib.sha256(
        json.dumps(
            coverage_report,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    assert coverage_report["certification_status"] == "NOT_ASSESSED"
    assert coverage_report["mapping_count"] > 0
    assert client.get(
        "/api/v1/controls/coverage?framework=not-a-framework",
        headers=headers,
    ).status_code == 404
    mapping_history = client.get(
        "/api/v1/controls/mappings/history?framework=NIST%20CSF",
        headers=headers,
    )
    assert mapping_history.status_code == 200
    assert mapping_history.json()["mappings"]
    assert all(
        item["framework"] == "NIST CSF"
        for item in mapping_history.json()["mappings"]
    )
    denied_audit = client.post(
        "/api/v1/audit",
        headers=headers,
        json={
            "target_domain": "example.com",
            "authorization_reference": "approved-ticket-1",
        },
    )
    assert denied_audit.status_code == 403
    frameworks = client.get("/api/v1/frameworks?category=methodology", headers=headers)
    assert frameworks.status_code == 200
    assert {item["reference_id"] for item in frameworks.json()["frameworks"]} == {
        "ptes",
        "osstmm",
        "tiber-eu",
    }
    correlated = client.post(
        "/api/v1/events/correlate",
        headers=headers,
        json={
            "events": [
                {"event_id": "e1", "event_type": "login", "correlation_key": "case-1"},
                {"event_id": "e2", "event_type": "privilege-change", "correlation_key": "case-1"},
            ]
        },
    )
    assert correlated.status_code == 200
    assert correlated.json()["status"] == "LOCAL_CORRELATION_ONLY"
    assert correlated.json()["correlations"][0]["threat_assessment"] == "NOT_ASSESSED"
    response = client.post(
        "/api/v1/controls/APP-VULN-001/assessments",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 200
    assert response.json()["state"] == "verified"
    assessment_coverage = client.get(
        "/api/v1/controls/coverage?framework=CWE%20Top%2025",
        headers=headers,
    ).json()
    vuln_mapping = next(
        item
        for item in assessment_coverage["mappings"]
        if item["control_id"] == "APP-VULN-001"
    )
    assert vuln_mapping["assessment_state"] == "verified"
    assert vuln_mapping["assessment_id"] == response.json()["assessment_id"]
    assert client.post(
        "/api/v1/controls/unknown/assessments",
        headers=headers,
        json=payload,
    ).status_code == 404
