import time
from typing import Dict, Any


class BehavioralBiometricsEngine:
    """Analiza dynamiki klawiatury (Keystroke Dynamics) i wzorców reakcji operatora."""

    def analyze_operator_rhythm(self, typing_latency_ms_list: list) -> Dict[str, Any]:
        if not typing_latency_ms_list:
            return {"stress_detected": True, "confidence": 0.0}
        
        avg_latency = sum(typing_latency_ms_list) / len(typing_latency_ms_list)
        # Symulacja wykrywania anomalii stresowych / przymusu fizycznego
        is_anomalous = avg_latency > 250.0 or avg_latency < 40.0

        return {
            "average_keystroke_latency_ms": round(avg_latency, 2),
            "coercion_stress_detected": is_anomalous,
            "confidence_score": 96.4 if not is_anomalous else 12.1,
            "status": "BIOMETRIC_PROFILE_ANALYZED"
        }