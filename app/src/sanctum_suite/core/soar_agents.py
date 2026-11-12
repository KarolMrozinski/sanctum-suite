from typing import Any


class AutonomousSOARAgent:
    """Produces human-review recommendations; it never performs remediation."""

    def __init__(self, agent_name: str = "SANCTUM-SENTINEL-01") -> None:
        self.agent_name = agent_name

    def evaluate_and_remediate(self, audit_summary: dict[str, Any]) -> dict[str, Any]:
        recommendations: list[dict[str, str]] = []
        exposed_services = [
            item for item in audit_summary.get("open_ports", [])
            if item.get("port") in {11434, 8080}
        ]
        for service in exposed_services:
            recommendations.append({
                "action": "REVIEW_SERVICE_EXPOSURE",
                "target": f"TCP:{service['port']}",
                "details": "Confirm the service is required and restrict access according to policy.",
            })
        if audit_summary.get("overall_score", 0.0) > 50.0:
            recommendations.append({
                "action": "REVIEW_HIGH_RISK_FINDINGS",
                "target": "security-review",
                "details": "Review findings and approve any mitigation through the normal change process.",
            })
        return {
            "agent_id": self.agent_name,
            "status": "RECOMMENDATIONS_READY" if recommendations else "NO_RECOMMENDATIONS",
            "actions_executed": 0,
            "recommendations": recommendations,
        }
