import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from sanctum_suite.orchestrator.engine import SanctumUnifiedOrchestrator
from sanctum_suite.core.analytics import AnalyticsStoreEngine
from sanctum_suite.core.tui import SanctumInteractiveDashboard

app = typer.Typer(help="SANCTUM-SUITE: Enterprise Cyber Resilience Platform")
console = Console()


@app.command(name="run-audit")
def run_full_audit(
    target: str = typer.Option("enterprise-core.com", help="Domena docelowa do przeprowadzenia pełnego audytu"),
) -> None:
    """Uruchamia pełną sekwencję audytową (Async Probe + OSINT + Red-Teaming + DuckDB)."""
    console.print(
        Panel.fit(
            f"[bold cyan]🏛️ SANCTUM-SUITE UNIFIED ORCHESTRATOR[/bold cyan]\n"
            f"Executing Enterprise Resilience Audit for: [yellow]{target}[/yellow]",
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
    table.add_row("Generated Report", result["report_path"])

    console.print("\n")
    console.print(table)


@app.command(name="analytics")
def view_analytics(
    target: str = typer.Option("enterprise-core.com", help="Domena do analityki DuckDB"),
) -> None:
    """Wyświetla zbiorcze wskaźniki analityczne zebrane w bazie DuckDB."""
    analytics = AnalyticsStoreEngine()
    metrics = analytics.get_target_threat_metrics(target)

    console.print(
        Panel.fit(
            f"[bold green]📊 DUCKDB ANALYTICS SUMMARY ({target})[/bold green]\n"
            f"Total Recorded Events: [cyan]{metrics['total_events']}[/cyan]\n"
            f"Average Risk Score: [yellow]{metrics['avg_risk_score']}[/yellow]\n"
            f"Max Risk Score: [red]{metrics['max_risk_score']}[/red]",
            border_style="green",
        )
    )


@app.command(name="dashboard")
def run_tui_dashboard(
    target: str = typer.Option("enterprise-core.com", help="Domena docelowa dla podglądu TUI Live"),
) -> None:
    """Uruchamia interaktywny, pełnoekranowy pulpit TUI w czasie rzeczywistym."""
    dashboard = SanctumInteractiveDashboard()
    dashboard.render_live_session(target, duration_seconds=5)


if __name__ == "__main__":
    app()