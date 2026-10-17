from typing import Dict, Any, List


class OWASPLLMComplianceEngine:
    """Silnik klasyfikacji i ewaluacji podatności wg standardu OWASP Top 10 for LLM Applications."""

    OWASP_CATEGORIES = {
        "LLM01": "Prompt Injection (Direct & Indirect)",
        "LLM02": "Sensitive Information Disclosure",
        "LLM03": "Supply Chain Vulnerabilities",
        "LLM04": "Data and Model Poisoning / Resource Exhaustion",
        "LLM05": "Improper Output Handling",
        "LLM06": "Excessive Agency",
        "LLM07": "System Prompt Leakage",
        "LLM08": "Vector and Embedding Weaknesses",
        "LLM09": "Misinformation & Hallucination Risk",
        "LLM10": "Unbounded Consumption",
    }

    def evaluate_owasp_top10(self, vulnerabilities: List[Dict[str, str]]) -> Dict[str, Any]:
        """Klonuje i mapuje znaleziska audytowe na oficjalną taksonomię OWASP LLM."""
        mapped_categories: Dict[str, int] = {cat: 0 for cat in self.OWASP_CATEGORIES}

        for vuln in vulnerabilities:
            v_type = vuln.get("vulnerability_type", "").upper()
            if "INJECTION" in v_type or "JAILBREAK" in v_type:
                mapped_categories["LLM01"] += 1
            elif "DISCLOSURE" in v_type or "PII" in v_type:
                mapped_categories["LLM02"] += 1
            elif "EXCESSIVE" in v_type or "TOOL" in v_type:
                mapped_categories["LLM06"] += 1
            elif "LEAK" in v_type or "SYSTEM" in v_type:
                mapped_categories["LLM07"] += 1
            else:
                mapped_categories["LLM05"] += 1

        total_issues = sum(mapped_categories.values())
        compliance_status = "PASSED" if total_issues == 0 else "RISK_DETECTED"

        return {
            "standard": "OWASP Top 10 for LLM Applications",
            "compliance_status": compliance_status,
            "total_mapped_issues": total_issues,
            "category_breakdown": mapped_categories,
        }