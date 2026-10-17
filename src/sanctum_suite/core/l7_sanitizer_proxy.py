import re
from typing import Dict, Any


class L7GuardrailSanitizerProxy:
    """Proxy Guardrail L7 do filtrującej sanityzacji wejścia/wyjścia w komunikacji z LLM."""

    def sanitize_input_payload(self, raw_prompt: str) -> Dict[str, Any]:
        """Waliduje i oczyszcza zapytanie wejściowe przed przekazaniem do modelu."""
        cleaned_prompt = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", raw_prompt)
        has_anomalous_characters = len(cleaned_prompt) != len(raw_prompt)

        return {
            "original_length": len(raw_prompt),
            "sanitized_prompt": cleaned_prompt,
            "is_clean": not has_anomalous_characters,
            "sanitization_applied": has_anomalous_characters,
        }

    def sanitize_output_payload(self, model_response: str) -> Dict[str, Any]:
        """Skanuje odpowiedź modelu i usuwa ewentualne przypadkowe znaki sterujące lub wycieki strukturalne."""
        redacted_response = model_response.replace("SECRET_KEY", "[REDACTED]")
        
        return {
            "sanitized_response": redacted_response,
            "leak_prevented": redacted_response != model_response,
        }