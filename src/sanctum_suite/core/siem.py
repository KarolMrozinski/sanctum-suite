import json
import math
import os
from typing import Any
from urllib.parse import urlsplit

import httpx


def _cef_escape(value: str, header: bool = False) -> str:
    escaped = value.replace("\\", "\\\\")
    if header:
        return escaped.replace("|", "\\|")
    return (
        escaped.replace("|", "\\|")
        .replace("=", "\\=")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
    )


class SIEMIntegrationExporter:
    """Formats CEF and sends payloads only to explicitly configured HTTPS webhooks."""

    def __init__(self, webhook_url: str | None = None, webhook_token: str | None = None) -> None:
        self.webhook_url = webhook_url or os.environ.get("SANCTUM_SIEM_WEBHOOK_URL")
        self.webhook_token = webhook_token or os.environ.get("SANCTUM_SIEM_WEBHOOK_TOKEN")
        if self.webhook_url:
            self._validate_webhook_url(self.webhook_url)

    def format_cef_event(self, audit_id: str, target: str, score: float, risk: str) -> str:
        if not math.isfinite(score) or not 0 <= score <= 100:
            raise ValueError("score must be a finite value between 0 and 100")
        header = [
            "SANCTUM-SUITE",
            "CyberResilience",
            "0.1.0",
            "AUDIT_EXEC",
            "Audit Completed",
            str(int(score)),
        ]
        escaped_header = "|".join(_cef_escape(field, header=True) for field in header)
        extension = " ".join(
            (
                f"suser={_cef_escape(target)}",
                f"act={_cef_escape(risk)}",
                f"externalId={_cef_escape(audit_id)}",
            )
        )
        return f"CEF:0|{escaped_header}|{extension}"

    @staticmethod
    def _validate_webhook_url(webhook_url: str) -> None:
        parsed = urlsplit(webhook_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("Webhook URL must use HTTPS")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Webhook URL cannot include credentials, a query, or a fragment")

    async def dispatch_webhook_alert(self, payload: dict[str, Any]) -> bool:
        if not self.webhook_url:
            raise RuntimeError("No SIEM webhook is configured")
        self._validate_webhook_url(self.webhook_url)
        headers = {"Authorization": f"Bearer {self.webhook_token}"} if self.webhook_token else {}
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
            response = await client.post(self.webhook_url, json=payload, headers=headers)
            response.raise_for_status()
            return response.is_success

    @staticmethod
    def serialize_event(payload: dict[str, Any]) -> str:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
