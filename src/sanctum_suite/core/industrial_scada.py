from typing import Any


class IndustrialScadaTelemetryAuditor:
    """Creates an authorized ICS assessment scope; it does not probe industrial hosts."""

    def audit_industrial_protocols(self, target_host: str) -> dict[str, Any]:
        target = target_host.strip()
        if not target:
            raise ValueError("An authorized ICS assessment scope is required")
        return {
            "target_scope": target,
            "protocols_analyzed": [],
            "status": "NOT_ASSESSED",
            "network_requests_made": False,
            "limitations": (
                "No Modbus, OPC UA, IEC 60870-5-104, PLC, or OT traffic is inspected or generated. "
                "Testing requires a site-approved plan and passive/safe instrumentation."
            ),
        }
