import shutil
from pathlib import Path
from typing import Any


class ParrotSecEngine:
    """Reports local Parrot OS/tool availability; never launches target scans."""

    TOOL_CANDIDATES = ("nmap", "yara", "volatility3", "radare2")

    def __init__(self) -> None:
        self.available_tools = [
            tool for tool in self.TOOL_CANDIDATES if shutil.which(tool) is not None
        ]

    @staticmethod
    def _os_release() -> dict[str, str]:
        release_file = Path("/etc/os-release")
        if not release_file.is_file():
            return {}
        values: dict[str, str] = {}
        for line in release_file.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator and key in {"ID", "NAME", "VERSION_ID", "PRETTY_NAME"}:
                values[key] = value.strip().strip('"')
        return values

    def run_recon_audit(self, target_host: str) -> dict[str, Any]:
        """Return a scope plan only; network reconnaissance is deliberately not executed."""
        target = target_host.strip()
        if not target:
            raise ValueError("An authorized target scope is required")
        os_release = self._os_release()
        return {
            "engine": "ParrotSecEngine",
            "environment": {
                "os_id": os_release.get("ID"),
                "os_name": os_release.get("NAME"),
                "os_version": os_release.get("VERSION_ID"),
            },
            "target_scope": target,
            "status": "NOT_EXECUTED",
            "tools_available": self.available_tools,
            "tools_executed": [],
            "network_requests_made": False,
        }
