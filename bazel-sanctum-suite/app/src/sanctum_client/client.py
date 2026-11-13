import httpx
import os
from typing import Any, Dict
from urllib.parse import urlsplit


class SanctumSuiteClient:
    """Natywne SDK Python do łatwej integracji z REST API platformy SANCTUM-SUITE."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        api_key: str | None = None,
    ) -> None:
        api_key = api_key or os.environ.get("SANCTUM_API_KEY")
        if not api_key or len(api_key.encode("utf-8")) < 32:
            raise ValueError(
                "Provide a SANCTUM_API_KEY of at least 32 bytes, either explicitly or through the environment."
            )
        parsed_url = urlsplit(base_url)
        is_local_http = (
            parsed_url.scheme == "http"
            and parsed_url.hostname in {"localhost", "127.0.0.1", "::1"}
        )
        if parsed_url.scheme != "https" and not is_local_http:
            raise ValueError("API connections must use HTTPS except for loopback development.")
        if not parsed_url.hostname or parsed_url.username or parsed_url.password:
            raise ValueError("Provide a valid API URL without embedded credentials.")
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