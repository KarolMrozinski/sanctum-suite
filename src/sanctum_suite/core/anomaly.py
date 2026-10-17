import math
from typing import Dict, Any


class MLAnomalyDetector:
    """Lekki silnik analizy anomalii telemetrycznych i tekstowych (Entropy & Heuristics)."""

    def _calculate_entropy(self, text: str) -> float:
        if not text:
            return 0.0
        entropy = 0.0
        for x in set(text):
            p_x = float(text.count(x)) / len(text)
            entropy -= p_x * math.log(p_x, 2)
        return entropy

    def score_prompt_anomaly(self, prompt: str) -> Dict[str, Any]:
        """Oblicza wskaźnik anomalii w prompcie na podstawie entropii i długości."""
        entropy = self._calculate_entropy(prompt)
        length = len(prompt)
        
        # Zapytania o wysokiej entropii lub nienaturalnej długości są flagowane jako anomalie
        is_anomaly = entropy > 4.5 or length > 1000
        score = min(1.0, (entropy / 5.0) * 0.5 + (length / 2000.0) * 0.5)

        return {
            "is_anomaly": is_anomaly,
            "anomaly_score": round(score, 3),
            "entropy": round(entropy, 3),
            "prompt_length": length,
        }