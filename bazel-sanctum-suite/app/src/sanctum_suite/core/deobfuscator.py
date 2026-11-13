import re
import base64
from typing import Dict, Any, List


class PayloadDeobfuscatorEngine:
    """Silnik deobfuskacji i wielowarstwowej analizy ukrytych ładunków ataku."""

    def __init__(self) -> None:
        self.suspicious_keywords = ["ignore previous instructions", "system prompt", "admin", "override", "drop table"]

    def analyze_payload(self, raw_input: str) -> Dict[str, Any]:
        """Wyrywa i deobfuskuje ukryte wzorce w zapytaniu."""
        normalized = raw_input.lower()
        layers_uncovered: List[str] = []

        # 1. Wykrywanie Base64
        b64_matches = re.findall(r"[A-Za-z0-9+/]{16,}={0,2}", raw_input)
        for match in b64_matches:
            try:
                decoded = base64.b64decode(match).decode("utf-8", errors="ignore")
                if any(kw in decoded.lower() for kw in self.suspicious_keywords):
                    layers_uncovered.append(f"BASE64_OBFUSCATED: '{decoded}'")
            except Exception:
                pass

        # 2. Normalizacja homoglifów Unicode
        normalized_unicode = re.sub(r"[\u200B-\u200D\uFEFF]", "", raw_input)
        if len(normalized_unicode) != len(raw_input):
            layers_uncovered.append("ZERO_WIDTH_UNICODE_INJECTION")

        is_obfuscated = len(layers_uncovered) > 0
        return {
            "is_obfuscated": is_obfuscated,
            "detected_layers": layers_uncovered,
            "risk_score": 0.85 if is_obfuscated else 0.0,
        }