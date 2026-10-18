import uuid
import math
from typing import Dict, Any, List


class AutonomousBehavioralSentinel:
    """Rdzeń SANCTUM: Autonomiczny Strażnik Dryfu Behawioralnego i Entropii (Behavioral Sentinel)."""

    def __init__(self, entropy_threshold: float = 7.5) -> None:
        self.sentinel_id = f"BEH-SENTINEL-{uuid.uuid4().hex[:8].upper()}"
        self.threshold = entropy_threshold

    def evaluate_system_entropy(self, operational_metrics: List[float]) -> Dict[str, Any]:
        """Analizuje entropię oraz wskaźniki behawioralne systemu w czasie rzeczywistym."""
        if not operational_metrics:
            return {"status": "INSUFFICIENT_METRICS", "autonomous_action_taken": False}

        # Obliczenie średniej entropii strumienia danych/operacji
        avg_entropy = sum(operational_metrics) / len(operational_metrics)
        anomaly_detected = avg_entropy > self.threshold

        action = "NONE"
        if anomaly_detected:
            action = "ISOLATE_SUBSYSTEM_AND_ROTATE_KEYS"

        return {
            "sentinel_id": self.sentinel_id,
            "average_entropy": round(avg_entropy, 2),
            "threshold": self.threshold,
            "anomaly_detected": anomaly_detected,
            "autonomous_action_taken": action,
            "status": "BEHAVIORAL_DEFENSE_ACTIVE"
        }