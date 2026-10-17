import json
import httpx
from typing import Dict, Any


class SIEMIntegrationExporter:
    """SIEM & SOAR Telemetry Exporter supporting CEF and HTTP Webhooks."""

    def __init__(self, webhook_url: str = None) -> None:
        self.webhook_url = webhook_url

    def format_cef_event(self, audit_id: str, target: str, score: float, risk: str) -> str:
        """Formatuje zdarzenie w standardzie Common Event Format (CEF)."""
        return (
            f"CEF:0|SANCTUM-SUITE|CyberResilience|0.1.0|AUDIT_EXEC|Audit Completed|{int(score)}|"
            f"suser={target} act={risk} externalId={audit_id}"
        )

    async def dispatch_webhook_alert(self, payload: Dict[str, Any]) -> bool:
        """Wysyła asynchroniczny alert HTTP Webhook do zewnętrznego systemu SOAR."""
        if not self.webhook_url:
            return False
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.post(self.webhook_url, json=payload)
                return response.status_code < 400
            except Exception:
                return False