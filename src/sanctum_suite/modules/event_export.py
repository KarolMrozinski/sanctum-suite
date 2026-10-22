from __future__ import annotations

import hashlib
import json
import os
import socket
import time
from datetime import datetime, timezone
from typing import Any, Mapping


def _cef_escape(value: Any, *, header: bool = False) -> str:
    text = "" if value is None else str(value)
    escaped = text.replace("\\", "\\\\")
    if header:
        return escaped.replace("|", "\\|")
    return escaped.replace("|", "\\|").replace("=", "\\=").replace("\r", "\\r").replace("\n", "\\n")


class CorporateTelemetryExporter:
    """Formats telemetry for SIEM and enterprise logging ingestion."""

    def __init__(
        self,
        *,
        hostname: str | None = None,
        app_name: str = "sanctum-suite",
        procid: str | None = None,
        facility: int = 16,
        default_severity: int = 6,
    ) -> None:
        self.hostname = hostname or socket.gethostname()
        self.app_name = app_name
        self.procid = procid or str(os.getpid())
        self.facility = facility
        self.default_severity = default_severity

    @staticmethod
    def _as_event_dict(event: Mapping[str, Any] | Any) -> dict[str, Any]:
        if isinstance(event, Mapping):
            return dict(event)
        if hasattr(event, "model_dump"):
            return dict(event.model_dump())
        if hasattr(event, "dict"):
            return dict(event.dict())
        return {"message": str(event)}

    def format_rfc5424(
        self,
        event: Mapping[str, Any] | Any,
        *,
        severity: int | None = None,
        facility: int | None = None,
        hostname: str | None = None,
        app_name: str | None = None,
        procid: str | None = None,
        msgid: str | None = None,
    ) -> str:
        payload = self._as_event_dict(event)
        severity = self.default_severity if severity is None else int(severity)
        facility = self.facility if facility is None else int(facility)
        rsyslog_priority = (facility << 3) | severity
        timestamp = payload.get("timestamp") or datetime.now(timezone.utc).isoformat()
        message = payload.get("message") or json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        structured_data = payload.get("structured_data") or "-"
        if isinstance(structured_data, (dict, list, tuple)):
            structured_data = json.dumps(structured_data, separators=(",", ":"), ensure_ascii=False)
        return (
            f"<{rsyslog_priority}>1 {timestamp} {hostname or self.hostname} {app_name or self.app_name} "
            f"{procid or self.procid} {msgid or payload.get('msgid', 'SANCTUM')} {structured_data} - {message}"
        )

    def format_cef(
        self,
        event: Mapping[str, Any] | Any,
        *,
        vendor: str = "SanctumSuite",
        product: str = "SecurityOperations",
        version: str = "1.0",
        event_name: str | None = None,
    ) -> str:
        payload = self._as_event_dict(event)
        event_name = event_name or str(payload.get("event_name") or payload.get("type") or "audit")
        score = payload.get("score")
        risk = payload.get("risk") or payload.get("severity") or "INFO"
        source = payload.get("source") or payload.get("actor") or payload.get("host") or self.hostname
        timestamp = payload.get("timestamp") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        header = [
            vendor,
            product,
            version,
            "0",
            event_name,
            str(score if isinstance(score, (int, float)) else 0),
        ]
        escaped_header = "|".join(_cef_escape(part, header=True) for part in header)
        extension_dict = {
            "rt": timestamp,
            "src": str(source),
            "msg": str(payload.get("message") or json.dumps(payload, separators=(",", ":"), ensure_ascii=False)),
            "sev": str(risk),
            "eventId": str(payload.get("event_id") or hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]),
        }
        extension = " ".join(f"{key}={_cef_escape(value)}" for key, value in extension_dict.items())
        return f"CEF:0|{escaped_header}|{extension}"

    def export_syslog(self, event: Mapping[str, Any] | Any, **kwargs: Any) -> str:
        return self.format_rfc5424(event, **kwargs)

    def export_cef(self, event: Mapping[str, Any] | Any, **kwargs: Any) -> str:
        return self.format_cef(event, **kwargs)


SyslogRFC5424Exporter = CorporateTelemetryExporter
CEFEventExporter = CorporateTelemetryExporter
