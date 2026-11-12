from typing import Any


class RegulatoryComplianceEngine:
    """Maps observed technical signals to areas needing evidence-based review."""

    def evaluate_compliance(
        self,
        shadow_vulns: list[dict[str, Any]],
        open_ports: list[dict[str, Any]],
    ) -> dict[str, Any]:
        signals: list[str] = []
        if any(vulnerability.get("issue") == "PROMPT_INJECTION_RISK" for vulnerability in shadow_vulns):
            signals.append("PROMPT_INJECTION_RISK_OBSERVED")
        if open_ports:
            signals.append("OPEN_SERVICES_OBSERVED")

        return {
            "eu_ai_act": {
                "status": "NOT_ASSESSED",
                "review_signals": signals,
            },
            "nis2": {
                "status": "NOT_ASSESSED",
                "review_signals": signals,
            },
            "iso_27001": {
                "status": "NOT_ASSESSED",
                "review_signals": signals,
            },
            "overall_compliance_grade": "NOT_ASSESSED",
            "limitations": (
                "Technical findings alone cannot establish legal applicability, "
                "management-system effectiveness, or compliance."
            ),
        }
