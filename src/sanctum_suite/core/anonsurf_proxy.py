from typing import Any


class AnonSurfProxyModule:
    """Reports proxy configuration status without changing host networking."""

    def __init__(self) -> None:
        self.is_active = False

    def enable_anonsurf_tunnel(self) -> dict[str, Any]:
        return {
            "status": "NOT_IMPLEMENTED",
            "tunnel_active": False,
            "dns_leak_protection": None,
            "mac_spoofing": None,
            "limitations": "No Tor, AnonSurf, DNS, routing, or MAC configuration is changed.",
        }

    def disable_anonsurf_tunnel(self) -> dict[str, Any]:
        return {
            "status": "NOT_IMPLEMENTED",
            "tunnel_active": False,
            "host_network_modified": False,
        }
