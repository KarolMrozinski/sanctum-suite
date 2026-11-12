from typing import Any


class RubberHoseDetectorEngine:
    """Placeholder; does not detect coercion or delete keys."""

    def evaluate_threat_vector(self, panic_gesture_triggered: bool) -> dict[str, Any]:
        return {
            "status": "NOT_ASSESSED",
            "threat_type": None,
            "action_taken": "NONE",
            "zeroization_performed": False,
        }
