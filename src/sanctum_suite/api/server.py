from fastapi import FastAPI, WebSocket, Security, HTTPException, status, Query
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from typing import Dict, Any, List
from fastapi import Response
import hmac
import os
from pathlib import Path
from pydantic import ConfigDict
from starlette.concurrency import run_in_threadpool

from sanctum_suite.orchestrator.engine import SanctumUnifiedOrchestrator
from sanctum_suite.core.analytics import AnalyticsStoreEngine
from sanctum_suite.core.sigma_yara import DetectionRuleGenerator
from sanctum_suite.core.anomaly import MLAnomalyDetector
from sanctum_suite.core.control_catalog import (
    AssessmentState,
    ControlCatalog,
    EvidenceInput,
)
from sanctum_suite.core.xdr_correlator import RealtimeXdrMeshCorrelator
from sanctum_suite.core.methodology_catalog import list_methodology_references
from sanctum_suite.core.target_authorization import TargetAuthorizationError, require_authorized_target
from sanctum_suite.core.billing import CommercialLicenseManager

app = FastAPI(
    title="SANCTUM-SUITE API",
    description="API for audit workflows, analytics, prompt inspection, and detection rules.",
    version="6.0.0",
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    expected_key = os.environ.get("SANCTUM_API_KEY", "")
    if len(expected_key.encode("utf-8")) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is not configured",
        )
    if not api_key or not hmac.compare_digest(
        api_key.encode("utf-8"), expected_key.encode("utf-8")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header",
        )
    return api_key


orchestrator = SanctumUnifiedOrchestrator()
analytics = AnalyticsStoreEngine()
rules_gen = DetectionRuleGenerator()
anomaly_detector = MLAnomalyDetector()
control_catalog: ControlCatalog | None = None
xdr_correlator = RealtimeXdrMeshCorrelator()
license_manager = CommercialLicenseManager()
audits_total = 0


def get_control_catalog() -> ControlCatalog:
    global control_catalog
    if control_catalog is None:
        default_controls_db = Path.home() / ".sanctum-suite" / "controls.sqlite3"
        control_catalog = ControlCatalog(
            os.environ.get("SANCTUM_CONTROLS_DB", str(default_controls_db))
        )
    return control_catalog


def consume_entitlement_usage(metric: str) -> None:
    entitlement = license_manager.validate_license_key(
        os.environ.get("SANCTUM_LICENSE_KEY")
    )
    license_manager.check_and_increment_usage(
        entitlement["tenant_id"],
        entitlement,
        metric,
    )


class AuditRequest(BaseModel):
    target_domain: str = Field(min_length=1, max_length=253)
    authorization_reference: str = Field(min_length=1, max_length=500)

class PromptInspectRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=32_768)

class EvidenceRequest(BaseModel):
    source: str = Field(min_length=1, max_length=100)
    reference: str = Field(min_length=1, max_length=2_048)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

class ControlAssessmentRequest(BaseModel):
    state: AssessmentState
    summary: str = Field(min_length=1, max_length=4_000)
    assessed_by: str = Field(min_length=1, max_length=200)
    evidence: List[EvidenceRequest] = Field(default_factory=list, max_length=20)

class SecurityEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1, max_length=128)
    event_type: str = Field(min_length=1, max_length=128)
    correlation_key: str = Field(min_length=1, max_length=256)

class EventCorrelationRequest(BaseModel):
    events: List[SecurityEvent] = Field(min_length=1, max_length=1_000)


@app.get("/")
async def root() -> Dict[str, str]:
    return {"status": "ONLINE", "system": "SANCTUM-SUITE Enterprise Core"}


@app.post("/api/v1/audit", dependencies=[Security(verify_api_key)])
async def trigger_audit(payload: AuditRequest) -> Dict[str, Any]:
    """Wyzwala pełen audyt odporności cyfrowej (Wymaga nagłówka X-API-Key)."""
    global audits_total
    try:
        target = require_authorized_target(
            payload.target_domain,
            payload.authorization_reference,
        )
    except (TargetAuthorizationError, ValueError) as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    try:
        result = await run_in_threadpool(
            orchestrator.execute_full_resilience_audit,
            target,
            authorization_reference=payload.authorization_reference,
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    audits_total += 1
    return {
        "status": "COMPLETED",
        "audit_id": result["audit_id"],
        "target": result["target"],
        "overall_score": result["overall_score"],
        "risk_level": result["risk_level"],
        "report_html": result["report_path_html"],
        "report_pdf": result["report_path_pdf"],
    }


@app.get("/api/v1/analytics", dependencies=[Security(verify_api_key)])
async def get_analytics(target: str = Query(..., description="Domena docelowa")) -> Dict[str, Any]:
    """Pobiera zbiorcze wskaźniki analityczne z bazy DuckDB (Wymaga nagłówka X-API-Key)."""
    return analytics.get_target_threat_metrics(target)


@app.get("/api/v1/controls", dependencies=[Security(verify_api_key)])
async def list_controls(framework: str | None = Query(default=None, max_length=100)) -> Dict[str, Any]:
    """Lists versioned control definitions without claiming compliance."""
    return {"controls": get_control_catalog().list_controls(framework)}


@app.get("/api/v1/frameworks", dependencies=[Security(verify_api_key)])
async def list_framework_references(
    category: str | None = Query(default=None, max_length=100),
) -> Dict[str, Any]:
    """Lists version-labeled references and their implementation boundaries."""
    return {"frameworks": list_methodology_references(category)}


@app.post("/api/v1/controls/{control_id}/assessments", dependencies=[Security(verify_api_key)])
async def create_control_assessment(
    control_id: str,
    payload: ControlAssessmentRequest,
) -> Dict[str, Any]:
    """Stores an assessment and integrity references, never raw evidence."""
    try:
        return get_control_catalog().create_assessment(
            control_id=control_id,
            state=payload.state,
            summary=payload.summary,
            assessed_by=payload.assessed_by,
            evidence=[
                EvidenceInput(source=item.source, reference=item.reference, sha256=item.sha256)
                for item in payload.evidence
            ],
        )
    except ValueError as error:
        if str(error).startswith("Unknown control:"):
            raise HTTPException(status_code=404, detail=str(error)) from error
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/api/v1/controls/{control_id}/assessments", dependencies=[Security(verify_api_key)])
async def list_control_assessments(
    control_id: str,
    limit: int = Query(default=50, ge=1, le=100),
) -> Dict[str, Any]:
    """Returns the latest evidence-backed assessment records for a control."""
    try:
        return {"assessments": get_control_catalog().list_assessments(control_id, limit)}
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/api/v1/events/correlate", dependencies=[Security(verify_api_key)])
async def correlate_security_events(payload: EventCorrelationRequest) -> Dict[str, Any]:
    """Locally groups normalized events by exact caller-supplied correlation key."""
    return xdr_correlator.ingest_telemetry_stream(
        [event.model_dump() for event in payload.events]
    )


@app.websocket("/ws/incidents")
async def websocket_incident_stream(websocket: WebSocket) -> None:
    """Rejects the endpoint until a real, authenticated event source is configured."""
    await websocket.accept()
    await websocket.close(code=1013, reason="Incident telemetry is not configured")

@app.post("/api/v1/inspect-prompt", dependencies=[Security(verify_api_key)])
async def inspect_prompt_endpoint(payload: PromptInspectRequest) -> Dict[str, Any]:
    """Skanuje prompt przez Guardrail Proxy oraz Anomaly Detector."""
    await run_in_threadpool(consume_entitlement_usage, "prompts")
    is_blocked, msg, details = orchestrator.guardrail.inspect_prompt(payload.prompt)
    anomaly_res = anomaly_detector.score_prompt_anomaly(payload.prompt)
    
    return {
        "is_blocked": is_blocked,
        "status_message": msg,
        "guardrail_details": details,
        "ml_anomaly_analysis": anomaly_res,
    }


@app.get("/api/v1/detection-rules", dependencies=[Security(verify_api_key)])
async def get_detection_rules(audit_id: str = Query("SNC-0001", description="ID Audytu")) -> Dict[str, str]:
    """Generuje natywne reguły Sigma i YARA dla wskazanego audytu."""
    yara_rule = rules_gen.generate_yara_rule(audit_id)
    sigma_rule = rules_gen.generate_sigma_rule(audit_id, "enterprise-core.com", [{"issue": "PROMPT_INJECTION_RISK"}])
    
    return {
        "audit_id": audit_id,
        "sigma_rule": sigma_rule,
        "yara_rule": yara_rule,
    }

@app.get("/healthz", status_code=200)
async def healthz():
    """Liveness probe dla Kubernetes / Docker Healthcheck."""
    return {"status": "HEALTHY", "service": "sanctum-suite-core"}

@app.get("/readyz", status_code=200)
async def readyz():
    """Readiness probe checks that API authentication is configured."""
    if len(os.environ.get("SANCTUM_API_KEY", "").encode("utf-8")) < 32:
        return Response(
            content='{"status":"NOT_READY","reason":"API authentication is not configured"}',
            status_code=503,
            media_type="application/json",
        )
    return {"status": "READY", "api_auth_configured": True}

@app.get("/metrics")
async def metrics():
    """Endpoint eksportu metryk w formacie Prometheus."""
    metrics_data = (
        "# HELP sanctum_audits_total Audits completed by this API process.\n"
        "# TYPE sanctum_audits_total counter\n"
        f"sanctum_audits_total {audits_total}\n"
    )
    return Response(content=metrics_data, media_type="text/plain")
