import uuid
from typing import Dict, Any, List


class DLPShieldEngine:
    """Silnik ochrony przed eksfiltracją danych (DLP) oraz zarządzania syntetycznymi honeytokenami."""

    def __init__(self) -> None:
        self.active_honeytokens: List[str] = []

    def inject_synthetic_honeytoken(self, secret_type: str = "AWS_KEY") -> Dict[str, str]:
        """Generuje i rejestruje syntetyczny honeytoken dla monitorowania wycieków z RAG."""
        token_id = f"HT-{uuid.uuid4().hex[:8].upper()}"
        fake_secret = f"AKIA{uuid.uuid4().hex[:16].upper()}HONEY"

        self.active_honeytokens.append(fake_secret)
        return {
            "token_id": token_id,
            "secret_type": secret_type,
            "honeytoken": fake_secret,
        }

    def inspect_output_for_exfiltration(self, llm_output: str) -> Dict[str, Any]:
        """Wykrywa obecność zarejestrowanych honeytokenów lub wzorców PII w odpowiedzi modelu."""
        leaked_tokens = [ht for ht in self.active_honeytokens if ht in llm_output]
        
        return {
            "exfiltration_detected": len(leaked_tokens) > 0,
            "leaked_honeytokens_count": len(leaked_tokens),
            "leaked_tokens": leaked_tokens,
        }