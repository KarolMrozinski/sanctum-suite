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
    assert client.get("/api/v1/controls", headers=headers).status_code == 200
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
    assert client.post(
        "/api/v1/controls/unknown/assessments",
        headers=headers,
        json=payload,
    ).status_code == 404
