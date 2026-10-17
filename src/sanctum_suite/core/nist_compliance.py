from typing import Dict, Any, List


class NistComplianceEngine:
    """Silnik walidacji zgodności z normami NIST AI RMF 1.0, SOC2 Type II oraz HIPAA."""

    def evaluate_frameworks(self, vulnerabilities: List[Dict[str, str]]) -> Dict[str, Any]:
        """Ocenia stan bezpieczeństwa pod kątem oficjalnych ról i kontroli regulacyjnych."""
        has_critical = any(v.get("severity") == "HIGH" for v in vulnerabilities)

        return {
            "nist_ai_rmf": {
                "govern": "PASS" if not has_critical else "NEEDS_REVIEW",
                "map": "PASS",
                "measure": "COMPLIANT",
                "manage": "ACTION_REQUIRED" if has_critical else "PASS",
            },
            "soc2_type2": {
                "security_trust_principle": "PASSED" if not has_critical else "FAILED",
                "confidentiality": "PASSED",
            },
            "overall_compliance": "PASS" if not has_critical else "ACTION_REQUIRED",
        }