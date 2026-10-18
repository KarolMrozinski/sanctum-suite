import re
import uuid
from typing import Any


_AUDIT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class DetectionRuleGenerator:
    """Generates starter detection rules with safely normalized identifiers."""

    @staticmethod
    def _validate_audit_id(audit_id: str) -> str:
        if not _AUDIT_ID_PATTERN.fullmatch(audit_id):
            raise ValueError("audit_id must contain only letters, digits, '.', '_' or '-'")
        return audit_id

    def generate_sigma_rule(
        self,
        audit_id: str,
        target: str,
        shadow_vulns: list[dict[str, Any]],
    ) -> str:
        del target
        audit_id = self._validate_audit_id(audit_id)
        has_prompt_injection = any(
            finding.get("issue") == "PROMPT_INJECTION_RISK"
            for finding in shadow_vulns
        )
        if not has_prompt_injection:
            return "# No prompt-injection finding supplied; no Sigma rule generated."

        rule_id = uuid.uuid5(uuid.NAMESPACE_URL, f"sanctum-audit:{audit_id}")
        return f"""title: SANCTUM AI Prompt Injection Attempt
id: {rule_id}
status: experimental
description: Detects a SANCTUM guardrail event that blocked a prompt-injection attempt.
logsource:
    category: application
    product: sanctum_guardrail
detection:
    selection:
        EventResult: 'BLOCKED'
        Action: 'DROP_REQUEST'
    condition: selection
falsepositives:
    - Authorized security testing
level: high
"""

    def generate_yara_rule(self, audit_id: str) -> str:
        audit_id = self._validate_audit_id(audit_id)
        safe_id = re.sub(r"[^A-Za-z0-9_]", "_", audit_id)
        return f"""rule SANCTUM_Prompt_Injection_Pattern_{safe_id}
{{
    meta:
        author = "SANCTUM-SUITE"
        description = "Heuristic strings for triage; not a complete detector"
    strings:
        $p1 = "ignore previous instructions" nocase
        $p2 = "disregard all prior rules" nocase
        $p3 = "system prompt override" nocase
    condition:
        any of ($p*)
}}"""
