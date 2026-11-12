import re
from typing import Dict, Any, Tuple


class LLMGuardrailProxy:
    """Real-time Guardrail Proxy inspecting and filtering LLM prompts against Prompt Injection."""

    SUSPICIOUS_PATTERNS = [
        r"ignore previous instructions",
        r"disregard all prior rules",
        r"system prompt override",
        r"reveal your hidden instructions",
        r"act as jailbroken ai",
    ]

    def inspect_prompt(self, prompt: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Skanuje zapytanie użytkownika pod kątem ataku.
        Zwraca: (is_blocked, prompt_or_reason, details)
        """
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                return True, "[BLOCKED] Prompt Injection detected by SANCTUM Guardrail.", {
                    "matched_pattern": pattern,
                    "action": "DROP_REQUEST",
                }
        
        return False, prompt, {"action": "ALLOW"}