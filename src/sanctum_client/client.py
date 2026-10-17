import httpx
from typing import Dict, Any


class SanctumSuiteClient:
    """Natywne SDK Python do łatwej integracji z REST API platformy SANCTUM-SUITE."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000", api_key: str = "sanctum-secret-key-2026") -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        }

    def trigger_audit(self, target_domain: str) -> Dict[str, Any]:
        """Uruchamia pełen audyt dla wskazanej domeny."""
        url = f"{self.base_url}/api/v1/audit"
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json={"target_domain": target_domain}, headers=self.headers)
            response.raise_for_status()
            return response.json()

    def inspect_prompt(self, prompt: str) -> Dict[str, Any]:
        """Skanuje zapytanie prompt przez Guardrail Proxy oraz ML Anomaly Detector."""
        url = f"{self.base_url}/api/v1/inspect-prompt"
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json={"prompt": prompt}, headers=self.headers)
            response.raise_for_status()
            return response.json()