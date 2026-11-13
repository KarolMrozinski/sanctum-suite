from typing import Any


class NeuralDecoderSimulationEngine:
    """Reports coercion, biometric, and enclave analysis as unavailable."""

    def evaluate_operator_behavior(
        self,
        keystroke_latencies: list[float],
        panic_active: bool = False,
    ) -> dict[str, Any]:
        return {
            "addon": "SANCTUM-DLC-NEURAL-DECODER",
            "status": "NOT_ASSESSED",
            "analysis_performed": False,
            "biometric_analysis": None,
            "threat_assessment": None,
            "neural_core_eval": None,
            "reason": "No validated biometric or hardware-enclave assessment is configured",
        }
