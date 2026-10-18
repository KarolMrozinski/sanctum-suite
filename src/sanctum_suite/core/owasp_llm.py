from typing import Any


class OWASPLLMComplianceEngine:
    """Maps supplied findings to OWASP LLM categories; it does not assess compliance."""

    OWASP_CATEGORIES = {
        "LLM01": "Prompt Injection",
        "LLM02": "Sensitive Information Disclosure",
        "LLM03": "Supply Chain Vulnerabilities",
        "LLM04": "Data and Model Poisoning",
        "LLM05": "Improper Output Handling",
        "LLM06": "Excessive Agency",
        "LLM07": "System Prompt Leakage",
        "LLM08": "Vector and Embedding Weaknesses",
        "LLM09": "Misinformation",
        "LLM10": "Unbounded Consumption",
    }

    _CATEGORY_MARKERS = {
        "LLM01": ("INJECTION", "JAILBREAK"),
        "LLM02": ("DISCLOSURE", "PII", "SENSITIVE_INFORMATION"),
        "LLM03": ("SUPPLY_CHAIN", "DEPENDENCY"),
        "LLM04": ("POISONING", "TRAINING_DATA"),
        "LLM05": ("OUTPUT_HANDLING", "UNSAFE_OUTPUT"),
        "LLM06": ("EXCESSIVE_AGENCY", "TOOL_ABUSE", "TOOL_MISUSE"),
        "LLM07": ("SYSTEM_PROMPT", "PROMPT_LEAK"),
        "LLM08": ("VECTOR", "EMBEDDING"),
        "LLM09": ("MISINFORMATION", "HALLUCINATION"),
        "LLM10": ("RESOURCE_EXHAUSTION", "UNBOUNDED_CONSUMPTION"),
    }

    def evaluate_owasp_top10(
        self,
        vulnerabilities: list[dict[str, Any]],
    ) -> dict[str, Any]:
        mapped_categories = {category: 0 for category in self.OWASP_CATEGORIES}
        unmapped_findings = 0
        for finding in vulnerabilities:
            description = " ".join(
                str(finding.get(field, ""))
                for field in ("vulnerability_type", "issue", "category")
            ).upper()
            matched_category = next(
                (
                    category
                    for category, markers in self._CATEGORY_MARKERS.items()
                    if any(marker in description for marker in markers)
                ),
                None,
            )
            if matched_category is None:
                unmapped_findings += 1
            else:
                mapped_categories[matched_category] += 1

        total_mapped_issues = sum(mapped_categories.values())
        return {
            "standard": "OWASP Top 10 for LLM Applications",
            "status": "FINDINGS_MAPPED_NOT_COMPLIANCE" if vulnerabilities else "NOT_ASSESSED",
            "assessment_status": "NOT_ASSESSED",
            "compliance_status": "NOT_ASSESSED",
            "total_findings_received": len(vulnerabilities),
            "total_mapped_issues": total_mapped_issues,
            "unmapped_findings": unmapped_findings,
            "category_breakdown": mapped_categories,
        }
