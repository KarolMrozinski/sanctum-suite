from typing import Any


class CcsdsTelemetryAnalyzer:
    """Placeholder; does not parse or assess CCSDS telemetry frames."""

    def analyze_ccsds_frame(self, frame_hex_header: str) -> dict[str, Any]:
        return {
            "status": "NOT_ANALYZED",
            "frame_parsed": False,
            "cryptographic_authentication_present": None,
            "command_injection_vulnerability": None,
        }
