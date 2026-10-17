import asyncio
from typing import List, Dict, Any


class AsyncPortScanner:
    """Asynchroniczny skaner portów o wysokiej wydajności do identyfikacji otwartych usług."""

    COMMON_PORTS = {
        22: "SSH",
        80: "HTTP",
        443: "HTTPS",
        5432: "PostgreSQL",
        6379: "Redis",
        11434: "Ollama LLM API",
        8080: "HTTP-ALT / Proxy",
    }

    def __init__(self, timeout: float = 1.0) -> None:
        self.timeout = timeout

    async def _check_port(self, host: str, port: int) -> Dict[str, Any]:
        """Próba nawiązania połączenia TCP na określonym porcie."""
        try:
            conn = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(conn, timeout=self.timeout)
            writer.close()
            await writer.wait_closed()
            return {
                "port": port,
                "service": self.COMMON_PORTS.get(port, "UNKNOWN"),
                "is_open": True,
            }
        except Exception:
            return {
                "port": port,
                "service": self.COMMON_PORTS.get(port, "UNKNOWN"),
                "is_open": False,
            }

    async def scan_host_ports(self, host: str, ports: List[int] = None) -> List[Dict[str, Any]]:
        """Skanuje listę portów na wybranym hoście w sposób asynchroniczny."""
        target_ports = ports or list(self.COMMON_PORTS.keys())
        tasks = [self._check_port(host, port) for port in target_ports]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r["is_open"]]

    def run_sync_port_scan(self, host: str, ports: List[int] = None) -> List[Dict[str, Any]]:
        """Wrapper pozwalający na wygodne uruchomienie skanu w kodzie synchronicznym."""
        return asyncio.run(self.scan_host_ports(host, ports))