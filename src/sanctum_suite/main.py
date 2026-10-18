import io
import sys

import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from sanctum_suite.orchestrator.engine import SanctumUnifiedOrchestrator
from sanctum_suite.core.analytics import AnalyticsStoreEngine
from sanctum_suite.core.tui import SanctumInteractiveDashboard
from sanctum_suite.core.port_scanner import AsyncPortScanner

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
    """Replace non-ASCII characters to keep Rich output working on legacy Windows terminals."""
    if value is None:
        return ""
    text = str(value)
    encoding = (getattr(sys.stdout, "encoding", "") or "").lower()
    if "utf" in encoding:
        return text
    return text.translate(_ASCII_TRANSLATION).encode("ascii", "ignore").decode("ascii")


def _build_console() -> Console:
    stream = sys.stdout
    encoding = (getattr(stream, "encoding", "") or "").lower()
    if "utf" not in encoding:
        try:
            stream = io.TextIOWrapper(stream.buffer, encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            stream = sys.stdout
    return Console(file=stream, emoji=False, legacy_windows=False)


app = typer.Typer(help=_safe_text("SANCTUM-SUITE: Enterprise Cyber Resilience Platform"))
console = _build_console()


@app.command(name="run-audit")
def run_full_audit(
    target: str = typer.Option("enterprise-core.com", help=_safe_text("Domena docelowa do przeprowadzenia pelnego audytu")),
) -> None:
    """Runs the full audit workflow (Async Probe + OSINT + Red-Teaming + DuckDB + PDF/HTML reports)."""
    console.print(
        Panel.fit(
            _safe_text(f"[bold cyan]SANCTUM-SUITE UNIFIED ORCHESTRATOR[/bold cyan]\nExecuting Enterprise Resilience Audit for: [yellow]{target}[/yellow]"),
            border_style="cyan",
        )
    )

    orchestrator = SanctumUnifiedOrchestrator()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[bold cyan]Running Async Probing & Resilience Audit Flow...", total=100)
        progress.update(task, advance=50)
        result = orchestrator.execute_full_resilience_audit(target)
        progress.update(task, advance=50)

    table = Table(title="Audit Execution Summary", header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="yellow")

    table.add_row("Audit ID", result["audit_id"])
    table.add_row("Target Domain", result["target"])
    table.add_row("Probed Endpoints", str(len(result["probed_endpoints"])))
    table.add_row("Identified Vulnerabilities", str(len(result["shadow_summary"]["vulnerabilities"])))
    table.add_row("Attack Chains Found", str(result["correlation"]["chain_count"]))
    table.add_row("Generated HTML Report", result["report_path_html"])
    table.add_row("Generated PDF Report", result["report_path_pdf"])

    console.print("\n")
    console.print(table)


@app.command(name="analytics")
def view_analytics(
    target: str = typer.Option("enterprise-core.com", help=_safe_text("Domena do analityki DuckDB")),
) -> None:
    """Displays aggregated analytics collected in the DuckDB store."""
    analytics = AnalyticsStoreEngine()
    metrics = analytics.get_target_threat_metrics(target)

    console.print(
        Panel.fit(
            _safe_text(
                f"[bold green]DUCKDB ANALYTICS SUMMARY ({target})[/bold green]\n"
                f"Total Recorded Events: [cyan]{metrics['total_events']}[/cyan]\n"
                f"Average Risk Score: [yellow]{metrics['avg_risk_score']}[/yellow]\n"
                f"Max Risk Score: [red]{metrics['max_risk_score']}[/red]"
            ),
            border_style="green",
        )
    )


@app.command(name="dashboard")
def run_tui_dashboard(
    target: str = typer.Option("enterprise-core.com", help=_safe_text("Domena docelowa dla podgladu TUI Live")),
) -> None:
    """Runs the interactive full-screen TUI dashboard in real time."""
    dashboard = SanctumInteractiveDashboard()
    dashboard.render_live_session(target, duration_seconds=5)


@app.command(name="scan-ports")
def scan_ports_cmd(
    host: str = typer.Option("127.0.0.1", help=_safe_text("Adres IP lub domena do przeskanowania portow")),
) -> None:
    """Runs a fast asynchronous TCP port scan and service detection."""
    console.print(
        Panel.fit(
            _safe_text(f"[bold magenta]SANCTUM ASYNC PORT SCANNER[/bold magenta]\nTarget Host: [cyan]{host}[/cyan]"),
            border_style="magenta",
        )
    )

    scanner = AsyncPortScanner()
    with console.status(_safe_text("[bold green]Skanowanie otwartych portow TCP...")):
        open_ports = scanner.run_sync_port_scan(host)

    table = Table(title=f"Open Ports on {host}", header_style="bold cyan")
    table.add_column("Port", style="yellow", justify="right")
    table.add_column("Detected Service", style="green")
    table.add_column("Status", style="bold red")

    for port_info in open_ports:
        table.add_row(str(port_info["port"]), port_info["service"], "OPEN")

    console.print("\n")
    if open_ports:
        console.print(table)
    else:
        console.print(_safe_text("[dim yellow]Nie znaleziono otwartych portow w standardowym zakresie.[/dim yellow]"))


@app.command(name="serve")
def start_api_server(
    host: str = typer.Option("127.0.0.1", help=_safe_text("Adres IP interfejsu serwera API")),
    port: int = typer.Option(8000, help=_safe_text("Port sieciowy serwera HTTP/WebSocket")),
) -> None:
    """Runs the REST API and WebSockets server (FastAPI + Uvicorn)."""
    console.print(
        Panel.fit(
            _safe_text(
                f"[bold cyan]SANCTUM-SUITE REST & WEBSOCKET API SERVER[/bold cyan]\n"
                f"Endpoint: [yellow]http://{host}:{port}[/yellow]\n"
                f"Swagger Docs: [green]http://{host}:{port}/docs[/green]"
            ),
            border_style="cyan",
        )
    )
    uvicorn.run("sanctum_suite.api.server:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    app()