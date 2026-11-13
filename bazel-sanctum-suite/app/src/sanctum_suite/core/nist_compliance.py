from typing import Any


class NistComplianceEngine:
    """Reports review signals without inferring framework compliance from findings."""

    def evaluate_frameworks(self, vulnerabilities: list[dict[str, Any]]) -> dict[str, Any]:
        review_required = bool(vulnerabilities)
        return {
            "nist_ai_rmf": {
                "status": "NEEDS_REVIEW" if review_required else "NOT_ASSESSED",
            },
            "soc2_type2": {
                "status": "NOT_ASSESSED",
            },
            "overall_compliance": "NEEDS_REVIEW" if review_required else "NOT_ASSESSED",
            "limitations": (
                "A vulnerability list is not sufficient evidence to assess an AI risk "
                "management system or an independent SOC 2 examination."
            ),
        }
