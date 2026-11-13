from typing import Any


class NeuralDecoderCore:
    """Placeholder; does not authenticate sessions or evaluate an enclave."""

    def evaluate_session_tensor(self, session_metrics: dict[str, float]) -> dict[str, Any]:
        return {
            "status": "NOT_ASSESSED",
            "evaluation_performed": False,
            "session_authorized": None,
            "neural_confidence": None,
        }
