from typing import Any


class SatcomSpoofSimulationEngine:
    """Reports satellite telemetry and uplink testing as unavailable."""

    def audit_ccsds_telemetry_link(self, satellite_id: str) -> dict[str, Any]:
        return {
            "addon": "SANCTUM-DLC-SATCOM-SPOOF",
            "target_satellite": satellite_id,
            "status": "NOT_ASSESSED",
            "assessment_performed": False,
            "orbital_mechanics": None,
            "ccsds_telemetry_inspection": None,
            "uplink_spoofing_assessment": None,
            "reason": "No authorized satellite test environment or CCSDS adapter is configured",
        }
