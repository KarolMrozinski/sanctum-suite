from typing import Any


class EDRTelemetrySyncEngine:
    """Reports endpoint telemetry as unavailable until a vendor adapter is configured."""

    def sync_endpoint_telemetry(self, audit_id: str) -> dict[str, Any]:
        return {
            "audit_id": audit_id,
            "edr_status": "NOT_CONFIGURED",
            "provider_connected": False,
            "correlated_events_count": None,
            "events": None,
        }