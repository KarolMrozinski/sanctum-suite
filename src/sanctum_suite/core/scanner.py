import asyncio
import httpx
from typing import List, Dict, Any


class AsyncEndpointScanner:
    """Asynchroniczny silnik o wysokiej wydajności do audytu punktów końcowych i nagłówków bezpieczeństwa."""

    def __init__(self, timeout: float = 3.0) -> None:
        self.timeout = timeout

    async def _probe_single_target(self, client: httpx.AsyncClient, target_url: str) -> Dict[str, Any]:
        """Sondowanie pojedynczego celu pod kątem obecności interfejsu API, certyfikatów i nagłówków security."""
        try:
            # Pasywne zapytanie HEAD/GET dla zweryfikowania dostępności
            response = await client.get(f"https://{target_url}", timeout=self.timeout)
            headers = response.headers
            
            missing_headers = []
            for h in ["Strict-Transport-Security", "Content-Security-Policy", "X-Frame-Options"]:
                if h not in headers:
                    missing_headers.append(h)

            return {
                "url": target_url,
                "status_code": response.status_code,
                "is_alive": True,
                "missing_security_headers": missing_headers,
                "server": headers.get("Server", "UNKNOWN"),
            }
        except Exception:
            # Fallback dla niedostępnego lub zablokowanego punktu
            return {
                "url": target_url,
                "status_code": 0,
                "is_alive": False,
                "missing_security_headers": ["ALL"],
                "server": "UNREACHABLE",
            }

    async def scan_endpoints_batch(self, targets: List[str]) -> List[Dict[str, Any]]:
        """Asynchroniczne skanowanie równoległe całej paczki domen/endpointów."""
        async with httpx.AsyncClient(verify=False) as client:
            tasks = [self._probe_single_target(client, target) for target in targets]
            results = await asyncio.gather(*tasks)
            return list(results)

    def run_sync_batch_scan(self, targets: List[str]) -> List[Dict[str, Any]]:
        """Współbieżne wywołanie synchroniczne dla łatwego użycia w orkiestratorze."""
        return asyncio.run(self.scan_endpoints_batch(targets))