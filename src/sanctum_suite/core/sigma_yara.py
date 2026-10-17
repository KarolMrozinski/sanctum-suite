from typing import List, Dict, Any


class DetectionRuleGenerator:
    """Generator reguł detekcyjnych Sigma i YARA na podstawie wykrytych podatności."""

    def generate_sigma_rule(self, audit_id: str, target: str, shadow_vulns: List[Dict[str, Any]]) -> str:
        """Tworzy regułę Sigma gotową do zaimportowania do Splunk / Elastic / Sentinel."""
        has_prompt_inj = any(v.get("issue") == "PROMPT_INJECTION_RISK" for v in shadow_vulns)
        
        rule_body = f"""title: SANCTUM AI Prompt Injection Attempt ({target})
id: {audit_id}
status: experimental
description: Detects prompt injection patterns targeted at enterprise LLM endpoints.
logsource:
    category: application
    product: sanctum_guardrail
detection:
    selection:
        EventResult: 'BLOCKED'
        Action: 'DROP_REQUEST'
    condition: selection
falsepositives:
    - Penetration testing activities
level: high
""" if has_prompt_inj else "# No critical Prompt Injection pattern detected for Sigma rule generation."

        return rule_body

    def generate_yara_rule(self, audit_id: str) -> str:
        """Tworzy regułę YARA do skanowania artefaktów i logów."""
        return f"""rule SANCTUM_Prompt_Injection_Pattern_{audit_id.replace('-', '_')}
{{
    meta:
        author = "SANCTUM-SUITE Engine"
        description = "Detects known jailbreak and prompt injection payloads"
        date = "2026-10-17"
    strings:
        $p1 = "ignore previous instructions" nocase
        $p2 = "disregard all prior rules" nocase
        $p3 = "system prompt override" nocase
    condition:
        any of ($p*)
}}"""