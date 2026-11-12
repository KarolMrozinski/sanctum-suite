import asyncio
from typing import List, Dict, Any
from sanctum_suite.core.target_authorization import require_authorized_target


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
        if not 0 < timeout <= 30:
            raise ValueError("timeout must be greater than zero and at most 30 seconds")
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
        except (ConnectionRefusedError, asyncio.TimeoutError):
            return {
                "port": port,
                "service": self.COMMON_PORTS.get(port, "UNKNOWN"),
                "is_open": False,
            }

    async def scan_host_ports(
        self,
        host: str,
        authorization_reference: str,
        ports: List[int] | None = None,
    ) -> List[Dict[str, Any]]:
        """Skanuje listę portów na wybranym hoście w sposób asynchroniczny."""
        authorized_host = require_authorized_target(host, authorization_reference)
        target_ports = list(self.COMMON_PORTS.keys()) if ports is None else ports
        if len(target_ports) > 64 or any(
            not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535
            for port in target_ports
        ):
            raise ValueError("ports must contain at most 64 valid TCP port numbers")
        tasks = [self._check_port(authorized_host, port) for port in target_ports]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r["is_open"]]

    def run_sync_port_scan(
        self,
        host: str,
        authorization_reference: str,
        ports: List[int] | None = None,
    ) -> List[Dict[str, Any]]:
        """Wrapper pozwalający na wygodne uruchomienie skanu w kodzie synchronicznym."""
        return asyncio.run(
            self.scan_host_ports(
                host,
                authorization_reference=authorization_reference,
                ports=ports,
            )
        )