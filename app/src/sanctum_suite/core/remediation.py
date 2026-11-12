from typing import List, Dict, Any


class RemediationPlaybookEngine:
    """Silnik generowania scenariuszy naprawczych (Playbooks / Hardening Rules)."""

    def generate_playbook(self, open_ports: List[Dict[str, Any]], shadow_vulns: List[Dict[str, Any]]) -> Dict[str, Any]:
        iptables_rules = []
        recommendations = []

        for p in open_ports:
            port = p.get("port")
            if port in [11434, 6379, 5432]:
                iptables_rules.append(f"iptables -A INPUT -p tcp --dport {port} -s 127.0.0.1 -j ACCEPT")
                iptables_rules.append(f"iptables -A INPUT -p tcp --dport {port} -j DROP")

        if shadow_vulns:
            recommendations.append("Deploy WAF rule / Guardrail Middleware for LLM input sanitization.")
            recommendations.append("Enforce system prompt isolation to mitigate Prompt Injection.")

        return {
            "firewall_hardening_script": "\n".join(iptables_rules),
            "strategic_recommendations": recommendations,
        }