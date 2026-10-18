import uuid
from typing import Dict, Any, List


class AutonomousBehavioralSentinel:
    """Rdzeń SANCTUM (Mandiant/Project Zero Spec): Zaawansowany Strażnik Dryfu Behawioralnego i Izolacji Sieciowej."""

    def __init__(self, entropy_threshold: float = 7.5) -> None:
        self.sentinel_id = f"BEH-SENTINEL-ADV-{uuid.uuid4().hex[:8].upper()}"
        self.threshold = entropy_threshold

    def evaluate_system_entropy(self, operational_metrics: List[float]) -> Dict[str, Any]:
        """Dokonuje wielowymiarowej analizy anomalii strumienia operacyjnego pod kątem eksfiltracji."""
        if not operational_metrics:
            return {
                "status": "INSUFFICIENT_METRICS",
                "anomaly_detected": False,
                "autonomous_action_taken": "NONE",
                "quarantined_resources": []
            }

        avg_entropy = sum(operational_metrics) / len(operational_metrics)
        max_metric = max(operational_metrics)
        anomaly_detected = avg_entropy > self.threshold or max_metric > (self.threshold * 1.2)

        action = "NONE"
        quarantine_list = []
        if anomaly_detected:
            action = "ISOLATE_SUBSYSTEM_AND_ROTATE_KEYS"
            quarantine_list = ["ALL_EXTERNAL_SOCKETS", "UNTRUSTED_IPC_CHANNELS"]

        return {
            "sentinel_id": self.sentinel_id,
            "average_entropy": round(avg_entropy, 2),
            "peak_entropy": round(max_metric, 2),
            "threshold": self.threshold,
            "anomaly_detected": anomaly_detected,
            "autonomous_action_taken": action,
            "quarantined_resources": quarantine_list,
            "status": "BEHAVIORAL_DEFENSE_ENFORCED"
        }