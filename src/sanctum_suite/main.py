import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from sanctum_suite.orchestrator.engine import SanctumUnifiedOrchestrator

app = typer.Typer(help="SANCTUM-SUITE: Enterprise Cyber Resilience Platform")
console = Console()


@app.command(name="run-audit")
def run_full_audit(
    target: str = typer.Option("enterprise-core.com", help="Domena docelowa do przeprowadzenia pełnego audytu"),
) -> None:
    """Uruchamia pełną sekwencję audytową: OSINT ➔ Red-Teaming ➔ Zero-Trust Packaging."""
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
        progress.update(task, advance=30)
        result = orchestrator.execute_full_resilience_audit(target)
        progress.update(task, advance=70)

    table = Table(title="Audit Execution Summary", header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="yellow")

    table.add_row("Audit ID", result["audit_id"])
    table.add_row("Target Domain", result["target"])
    table.add_row("Discovered Subdomains", str(result["osint_summary"]["exposed_assets_count"]))
    table.add_row("Identified Vulnerabilities", str(len(result["shadow_summary"]["vulnerabilities"])))
    table.add_row("Zero-Trust Alert Envelope", result["envelope_hash"])

    console.print("\n")
    console.print(table)

    score_color = "red" if result["overall_score"] > 50 else "green"
    console.print(
        Panel.fit(
            f"[bold]Aggregated Threat Score:[/bold] [{score_color}]{result['overall_score']:.1f} / 100[/{score_color}] | "
            f"[bold]Risk Level:[/bold] [{score_color}]{result['risk_level']}[/{score_color}]",
            border_style=score_color,
        )
    )


if __name__ == "__main__":
    app()