import time
import sys

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text

_ASCII_TRANSLATION = {
    ord("ą"): "a",
    ord("Ą"): "A",
    ord("ć"): "c",
    ord("Ć"): "C",
    ord("ę"): "e",
    ord("Ę"): "E",
    ord("ł"): "l",
    ord("Ł"): "L",
    ord("ń"): "n",
    ord("Ń"): "N",
    ord("ó"): "o",
    ord("Ó"): "O",
    ord("ś"): "s",
    ord("Ś"): "S",
    ord("ż"): "z",
    ord("Ż"): "Z",
    ord("ź"): "z",
    ord("Ź"): "Z",
}


def _safe_text(value: str) -> str:
    if value is None:
        return ""
    text = str(value)
    encoding = (getattr(sys.stdout, "encoding", "") or "").lower()
    if "utf" in encoding:
        return text
    return text.translate(_ASCII_TRANSLATION).encode("ascii", "ignore").decode("ascii")


class SanctumInteractiveDashboard:
    """Interaktywny, pelnoekranowy TUI Dashboard reprezentujacy zywy strumien zdarzen i status SOC."""

    def __init__(self) -> None:
        self.console = Console(emoji=False, legacy_windows=False)

    def _make_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=3),
        )
        layout["body"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1),
        )
        return layout

    def render_live_session(self, target: str, duration_seconds: int = 5) -> None:
        layout = self._make_layout()

        layout["header"].update(
            Panel(
                Text(_safe_text(f"SANCTUM-SUITE LIVE SOC DASHBOARD | TARGET: {target.upper()}"), style="bold cyan"),
                border_style="cyan",
            )
        )
        layout["footer"].update(
            Panel(
                Text(_safe_text("Press Ctrl+C to terminate live feed | Status: ALL AGENTS OPERATIONAL"), style="dim green"),
                border_style="green",
            )
        )

        table_threats = Table(title=_safe_text("Real-Time Incident Stream"), expand=True)
        table_threats.add_column("Time", style="dim")
        table_threats.add_column("Source", style="cyan")
        table_threats.add_column("Event", style="yellow")
        table_threats.add_column("Risk", justify="right", style="bold red")

        table_threats.add_row("18:14:02", "SPECTRE-OSINT", "Exposed Subdomain Discovered", "MEDIUM")
        table_threats.add_row("18:14:04", "SHADOW-AGENT", "Prompt Injection Bypass Vulnerability", "CRITICAL")
        table_threats.add_row("18:14:05", "GHOST-COMM", "P2P Zero-Trust Route Rerouted", "LOW")

        layout["left"].update(Panel(table_threats, border_style="blue"))

        status_panel = Panel(
            _safe_text(
                "[bold white]Active Modules Status:[/bold white]\n\n"
                "• [green]SPECTRE-OSINT:[/green] Active Scan (3 Targets)\n"
                "• [green]SHADOW-AGENT:[/green] Fuzzing Engine Active\n"
                "• [green]GHOST-COMM:[/green] Mesh Active (4 Nodes)\n"
                "• [green]DUCKDB STORE:[/green] Logging Stream Active\n"
            ),
            title=_safe_text("System Health & Agents"),
            border_style="magenta",
        )
        layout["right"].update(status_panel)

        with Live(layout, console=self.console, refresh_per_second=4, screen=False):
            time.sleep(duration_seconds)