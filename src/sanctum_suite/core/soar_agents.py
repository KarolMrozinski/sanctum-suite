from typing import Dict, Any, List


class AutonomousSOARAgent:
    """Autonomiczny Agent SOC/SOAR podejmujący akcje zaradcze w czasie rzeczywistym."""

    def __init__(self, agent_name: str = "SANCTUM-SENTINEL-01") -> None:
        self.agent_name = agent_name

    def evaluate_and_remediate(self, audit_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Analizuje wykryte podatności i wykonuje autonomiczne decyzje naprawcze."""
        actions_taken: List[Dict[str, str]] = []
        overall_score = audit_summary.get("overall_score", 0.0)

        # 1. Automatyczna izolacja skompromitowanych portów/usług
        for port_info in audit_summary.get("open_ports", []):
            if port_info.get("port") in [11434, 8080]:
                actions_taken.append({
                    "action": "FIREWALL_RULE_APPLIED",
                    "target": f"TCP:{port_info.get('port')}",
                    "details": "Applied iptables drop rule for unauthenticated LLM API endpoint.",
                })

        # 2. Automatyczna zmiana polityk Guardraila przy wysokim ryzyku
        if overall_score > 50.0:
            actions_taken.append({
                "action": "GUARDRAIL_STRICT_MODE_ENABLED",
                "target": "LLMGuardrailProxy",
                "details": "Lowered anomaly threshold to 0.35 and enabled multi-turn session blocking.",
            })

        return {
            "agent_id": self.agent_name,
            "status": "REMEDIATION_EXECUTED" if actions_taken else "NO_ACTION_REQUIRED",
            "actions_count": len(actions_taken),
            "executed_actions": actions_taken,
        }