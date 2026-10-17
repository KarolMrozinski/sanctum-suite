import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from sanctum_suite.orchestrator.engine import SanctumUnifiedOrchestrator
from sanctum_suite.core.analytics import AnalyticsStoreEngine

app = typer.Typer(help="SANCTUM-SUITE: Enterprise Cyber Resilience Platform")
console = Console()


@app.command(name="run-audit")
def run_full_audit(
    target: str = typer.Option("enterprise-core.com", help="Domena docelowa do przeprowadzenia pełnego audytu"),
) -> None:
    """Uruchamia pełną sekwencję audytową, generuje raport HTML i zapisuje zdarzenia w DuckDB."""
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
        task = progress.add_task("[bold cyan]Running Unified Resilience Audit Flow...", total=100)
        progress.update(task, advance=50)
        result = orchestrator.execute_full_resilience_audit(target)
        progress.update(task, advance=50)

    table = Table(title="Audit Execution Summary", header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="yellow")

    table.add_row("Audit ID", result["audit_id"])
    table.add_row("Target Domain", result["target"])
    table.add_row("Discovered Subdomains", str(result["osint_summary"]["exposed_assets_count"]))
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


if __name__ == "__main__":
    app()