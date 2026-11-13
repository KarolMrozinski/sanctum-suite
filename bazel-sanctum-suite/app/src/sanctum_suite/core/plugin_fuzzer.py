from typing import Any


class AgentToolPluginFuzzer:
    """Reports agent-tool testing as unassessed until a real test harness is configured."""

    def evaluate_agent_tools(self, target_domain: str) -> dict[str, Any]:
        return {
            "target": target_domain,
            "status": "NOT_ASSESSED",
            "test_harness_configured": False,
            "tools_scanned": None,
            "vulnerabilities": None,
            "indirect_injection_susceptible": None,
        }
