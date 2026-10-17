from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, Query
from pydantic import BaseModel
from typing import List, Dict, Any
import asyncio
import json

from sanctum_suite.orchestrator.engine import SanctumUnifiedOrchestrator
from sanctum_suite.core.analytics import AnalyticsStoreEngine

app = FastAPI(
    title="SANCTUM-SUITE Enterprise API",
    description="REST & WebSocket API for Enterprise Cyber Resilience Platform",
    version="0.1.0",
)

orchestrator = SanctumUnifiedOrchestrator()
analytics = AnalyticsStoreEngine()


class AuditRequest(BaseModel):
    target_domain: str


class AuditResponse(BaseModel):
    status: str
    audit_id: str
    target: str
    overall_score: float
    risk_level: str
    report_html: str
    report_pdf: str


@app.get("/")
async def root() -> Dict[str, str]:
    return {"status": "ONLINE", "system": "SANCTUM-SUITE Enterprise Core"}


@app.post("/api/v1/audit", response_model=AuditResponse)
async def trigger_audit(payload: AuditRequest) -> Dict[str, Any]:
    """Wyzwala pełen audyt odporności cyfrowej dla podanej domeny."""
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


@app.get("/api/v1/analytics")
async def get_analytics(target: str = Query(..., description="Domena docelowa")) -> Dict[str, Any]:
    """Pobiera zbiorcze wskaźniki analityczne z bazy DuckDB."""
    return analytics.get_target_threat_metrics(target)


@app.websocket("/ws/incidents")
async def websocket_incident_stream(websocket: WebSocket) -> None:
    """Strumieniowanie żywych incydentów i alertów w czasie rzeczywistym przez WebSocket."""
    await websocket.accept()
    try:
        while True:
            # Symulowany strumień zdarzeń telemetrycznych dla podłączonych klientów SIEM/SOC
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