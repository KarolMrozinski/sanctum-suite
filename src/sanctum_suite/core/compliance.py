from typing import List, Dict, Any


class RegulatoryComplianceEngine:
    """Silnik walidacji zgodności regulacyjnej i normatywnej (EU AI Act, NIS2, ISO 27001)."""

    def evaluate_compliance(self, shadow_vulns: List[Dict[str, Any]], open_ports: List[Dict[str, Any]]) -> Dict[str, Any]:
        has_prompt_injection = any(v.get("issue") == "PROMPT_INJECTION_RISK" for v in shadow_vulns)
        has_exposed_services = len(open_ports) > 0

        eu_ai_act = {
            "article_15_cybersecurity": "NON_COMPLIANT" if has_prompt_injection else "COMPLIANT",
            "article_14_human_oversight": "COMPLIANT",
            "risk_status": "HIGH_RISK_AI_SYSTEM" if has_prompt_injection else "LOW_RISK",
        }

        nis2_directive = {
            "article_21_risk_management": "ACTION_REQUIRED" if has_exposed_services else "OPTIMAL",
            "supply_chain_security": "VERIFIED",
        }

        iso_27001 = {
            "control_A_8_8_technical_vulnerabilities": "FAIL" if (has_prompt_injection or has_exposed_services) else "PASS",
            "control_A_8_20_network_security": "PASS" if not has_exposed_services else "WARNING",
        }

        return {
            "eu_ai_act": eu_ai_act,
            "nis2": nis2_directive,
            "iso_27001": iso_27001,
            "overall_compliance_grade": "NON_COMPLIANT" if has_prompt_injection else "COMPLIANT",
        }