import asyncio
from typing import List, Dict, Any


class DecoyHoneypotSensor:
    """Lekki sensor sieciowy rejestrujący podejrzane próby nawiązania połączenia."""

    def __init__(self, port: int = 11435) -> None:
        self.port = port
        self.intercepted_connections: List[Dict[str, Any]] = []

    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        ip = peer[0] if peer else "UNKNOWN"
        
        self.intercepted_connections.append({"ip": ip, "port": self.port, "status": "INTERCEPTED"})
        writer.close()
        await writer.wait_closed()

    async def run_decoy_session(self, duration_seconds: float = 1.0) -> List[Dict[str, Any]]:
        """Uruchamia emulowany port na określony czas i zbiera metryki połączeń."""
        try:
            server = await asyncio.start_server(self._handle_connection, "127.0.0.1", self.port)
            await asyncio.sleep(duration_seconds)
            server.close()
            await server.wait_closed()
        except Exception:
            pass
        return self.intercepted_connections