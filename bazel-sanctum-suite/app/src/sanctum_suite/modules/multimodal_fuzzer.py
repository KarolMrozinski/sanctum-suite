from typing import Any


class MultimodalSafetyFuzzer:
    """Reports image and audio prompt testing as unavailable without a test harness."""

    def evaluate_visual_prompts(self, endpoint: str) -> dict[str, Any]:
        return {
            "endpoint": endpoint,
            "status": "NOT_EXECUTED",
            "test_harness_configured": False,
            "images_scanned": 0,
            "vulnerabilities": None,
            "vision_resilience_score": None,
        }
