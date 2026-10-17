from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Security, HTTPException, status, Query
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import Dict, Any
import asyncio
import json

from sanctum_suite.orchestrator.engine import SanctumUnifiedOrchestrator
from sanctum_suite.core.analytics import AnalyticsStoreEngine
from sanctum_suite.core.sigma_yara import DetectionRuleGenerator
from sanctum_suite.core.anomaly import MLAnomalyDetector

app = FastAPI(
    title="SANCTUM-SUITE Enterprise API",
    description="Secured REST & WebSocket API for Enterprise Cyber Resilience Platform",
    version="0.1.0",
)

API_KEY = "sanctum-secret-key-2026"
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header",
        )
    return api_key


orchestrator = SanctumUnifiedOrchestrator()
analytics = AnalyticsStoreEngine()
rules_gen = DetectionRuleGenerator()
anomaly_detector = MLAnomalyDetector()


class AuditRequest(BaseModel):
    target_domain: str

class PromptInspectRequest(BaseModel):
    prompt: str


@app.get("/")
async def root() -> Dict[str, str]:
    return {"status": "ONLINE", "system": "SANCTUM-SUITE Enterprise Core"}


@app.post("/api/v1/audit", dependencies=[Security(verify_api_key)])
async def trigger_audit(payload: AuditRequest) -> Dict[str, Any]:
    """Wyzwala pełen audyt odporności cyfrowej (Wymaga nagłówka X-API-Key)."""
    result = orchestrator.execute_full_resilience_audit(payload.target_domain)
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
    """Strumieniowanie żywych incydentów i alertów przez WebSocket."""
    await websocket.accept()
    try:
        while True:
            sample_event = {
                "event": "INCIDENT_DETECTED",
                "source": "SHADOW-AGENT",
                "severity": "HIGH",
                "details": "Validated Prompt Injection vulnerability detected",
            }
            await websocket.send_text(json.dumps(sample_event))
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        pass

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

