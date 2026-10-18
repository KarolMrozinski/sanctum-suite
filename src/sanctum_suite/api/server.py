from fastapi import FastAPI, WebSocket, Security, HTTPException, status, Query
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from typing import Dict, Any
from fastapi import Response
import hmac
import os
from starlette.concurrency import run_in_threadpool

from sanctum_suite.orchestrator.engine import SanctumUnifiedOrchestrator
from sanctum_suite.core.analytics import AnalyticsStoreEngine
from sanctum_suite.core.sigma_yara import DetectionRuleGenerator
from sanctum_suite.core.anomaly import MLAnomalyDetector

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
audits_total = 0


class AuditRequest(BaseModel):
    target_domain: str = Field(min_length=1, max_length=253)

class PromptInspectRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=32_768)


@app.get("/")
async def root() -> Dict[str, str]:
    return {"status": "ONLINE", "system": "SANCTUM-SUITE Enterprise Core"}


@app.post("/api/v1/audit", dependencies=[Security(verify_api_key)])
async def trigger_audit(payload: AuditRequest) -> Dict[str, Any]:
    """Wyzwala pełen audyt odporności cyfrowej (Wymaga nagłówka X-API-Key)."""
    global audits_total
    result = await run_in_threadpool(
        orchestrator.execute_full_resilience_audit, payload.target_domain
    )
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


@app.websocket("/ws/incidents")
async def websocket_incident_stream(websocket: WebSocket) -> None:
    """Rejects the endpoint until a real, authenticated event source is configured."""
    await websocket.accept()
    await websocket.close(code=1013, reason="Incident telemetry is not configured")

@app.post("/api/v1/inspect-prompt", dependencies=[Security(verify_api_key)])
async def inspect_prompt_endpoint(payload: PromptInspectRequest) -> Dict[str, Any]:
    """Skanuje prompt przez Guardrail Proxy oraz Anomaly Detector."""
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
