from typing import Any


class MultiTurnJailbreakFuzzer:
    """Reports multi-turn model testing as unavailable without a test harness."""

    def execute_multi_turn_fuzzing(self, endpoint: str) -> dict[str, Any]:
        return {
            "endpoint": endpoint,
            "status": "NOT_EXECUTED",
            "test_harness_configured": False,
            "conversations_tested": 0,
            "vulnerabilities": None,
            "adaptive_score": None,
        }
