from typing import Any


class AutonomousBehavioralSentinel:
    """Compares supplied metrics to a threshold without claiming detection or isolation."""

    def __init__(self, entropy_threshold: float = 7.5) -> None:
        self.threshold = entropy_threshold

    def evaluate_system_entropy(self, operational_metrics: list[float]) -> dict[str, Any]:
        if not operational_metrics:
            return {
                "status": "NOT_ASSESSED",
                "metric_threshold_exceeded": None,
                "autonomous_action_taken": "NONE",
                "quarantined_resources": None,
            }

        avg_entropy = sum(operational_metrics) / len(operational_metrics)
        max_metric = max(operational_metrics)
        threshold_exceeded = avg_entropy > self.threshold or max_metric > (self.threshold * 1.2)

        return {
            "average_entropy": round(avg_entropy, 2),
            "peak_entropy": round(max_metric, 2),
            "threshold": self.threshold,
            "status": "METRIC_THRESHOLD_EXCEEDED" if threshold_exceeded else "METRICS_WITHIN_THRESHOLD",
            "metric_threshold_exceeded": threshold_exceeded,
            "anomaly_detected": None,
            "autonomous_action_taken": "NONE",
            "quarantined_resources": None,
        }