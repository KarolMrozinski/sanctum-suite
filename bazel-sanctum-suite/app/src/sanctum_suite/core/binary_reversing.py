from typing import Any


class ProjectZeroBinaryReversingEngine:
    """Reports the absence of an integrated binary-analysis engine."""

    def analyze_firmware_binary(self, binary_path: str) -> dict[str, Any]:
        return {
            "binary_path": binary_path,
            "status": "NOT_ANALYZED",
            "analysis_performed": False,
            "architecture": None,
            "entropy_score": None,
            "packed_or_obfuscated": None,
            "heap_overflow_risk": None,
            "backdoors_detected": None,
            "external_analysis_required": True,
        }
