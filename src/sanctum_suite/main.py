import io
import ipaddress
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import typer
import uvicorn
from fastapi import HTTPException
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from sanctum_suite.orchestrator.engine import SanctumUnifiedOrchestrator
from sanctum_suite.core.analytics import AnalyticsStoreEngine
from sanctum_suite.core.tui import SanctumInteractiveDashboard
from sanctum_suite.core.port_scanner import AsyncPortScanner
from sanctum_suite.core.target_authorization import (
    TargetAuthorizationError,
    require_authorized_target,
)
from sanctum_suite.core.billing import CommercialLicenseManager, LicenseTier
from sanctum_suite.core.license_issuer import issue_license_token

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
    target: str = typer.Option(..., help=_safe_text("Dokladny cel dopuszczony przez administratora")),
    authorization_reference: str = typer.Option(..., "--authorization-reference", help=_safe_text("Identyfikator pisemnej zgody")),
) -> None:
    """Runs the explicitly authorized assessment workflow and writes audit reports."""
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
        try:
            result = orchestrator.execute_full_resilience_audit(
                target,
                authorization_reference=authorization_reference,
            )
        except TargetAuthorizationError as error:
            raise typer.BadParameter(str(error)) from error
        except HTTPException as error:
            raise typer.BadParameter(str(error.detail)) from error
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
    authorization_reference: str = typer.Option(..., "--authorization-reference", help=_safe_text("Identyfikator pisemnej zgody")),
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
        try:
            require_authorized_target(host, authorization_reference)
            license_manager = CommercialLicenseManager()
            entitlement = license_manager.validate_license_key(
                os.environ.get("SANCTUM_LICENSE_KEY")
            )
            license_manager.check_and_increment_usage(
                entitlement["tenant_id"],
                entitlement,
                "audits",
            )
            open_ports = scanner.run_sync_port_scan(
                host,
                authorization_reference=authorization_reference,
            )
        except TargetAuthorizationError as error:
            raise typer.BadParameter(str(error)) from error
        except HTTPException as error:
            raise typer.BadParameter(str(error.detail)) from error

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


@app.command(name="issue-license")
def issue_license_cmd(
    private_key_file: Path = typer.Option(..., "--private-key-file", exists=True, file_okay=True, dir_okay=False, readable=True),
    license_id: str = typer.Option(..., "--license-id"),
    tenant_id: str = typer.Option(..., "--tenant-id"),
    tier: str = typer.Option(..., "--tier"),
    expires_in_days: int = typer.Option(..., "--expires-in-days"),
    max_audits_per_month: int = typer.Option(..., "--max-audits-per-month"),
    max_prompts_per_day: int = typer.Option(..., "--max-prompts-per-day"),
    features: str = typer.Option("audit", "--features"),
) -> None:
    """Issues a signed offline entitlement; run only on the isolated licensing workstation."""
    if not 1 <= expires_in_days <= 3650:
        raise typer.BadParameter("expires-in-days must be between 1 and 3650")
    if max_audits_per_month < 0 or max_prompts_per_day < 0:
        raise typer.BadParameter("Usage limits must be non-negative")
    try:
        normalized_tier = LicenseTier(tier.upper())
    except ValueError as error:
        raise typer.BadParameter("tier must be COMMUNITY, PROFESSIONAL, or ENTERPRISE") from error
    feature_list = [feature.strip() for feature in features.split(",") if feature.strip()]
    if not feature_list:
        raise typer.BadParameter("At least one feature is required")
    try:
        private_key_bytes = private_key_file.read_bytes()
    except OSError as error:
        raise typer.BadParameter(f"Cannot read private-key file: {error}") from error
    try:
        private_key = serialization.load_pem_private_key(private_key_bytes, password=None)
    except TypeError:
        password = typer.prompt("Private key password", hide_input=True).encode("utf-8")
        try:
            private_key = serialization.load_pem_private_key(
                private_key_bytes,
                password=password,
            )
        except (TypeError, ValueError) as error:
            raise typer.BadParameter("Private-key file or password is invalid") from error
    except ValueError as error:
        raise typer.BadParameter("Private-key file is invalid") from error
    if not isinstance(private_key, Ed25519PrivateKey):
        raise typer.BadParameter("Private key must use Ed25519")

    expires_at = int((datetime.now(timezone.utc) + timedelta(days=expires_in_days)).timestamp())
    try:
        token = issue_license_token(
            private_key,
            license_id=license_id,
            tenant_id=tenant_id,
            tier=normalized_tier,
            expires_at=expires_at,
            max_audits_per_month=max_audits_per_month,
            max_prompts_per_day=max_prompts_per_day,
            features=feature_list,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    typer.echo(json.dumps({
        "license_token": token,
        "verification_public_key_pem": public_key,
    }, indent=2))


@app.command(name="serve")
def start_api_server(
    host: str = typer.Option("127.0.0.1", help=_safe_text("Adres IP interfejsu serwera API")),
    port: int = typer.Option(8000, help=_safe_text("Port sieciowy serwera HTTP/WebSocket")),
) -> None:
    """Runs the REST API and WebSockets server (FastAPI + Uvicorn)."""
    certificate = os.environ.get("SANCTUM_TLS_CERT_FILE")
    private_key = os.environ.get("SANCTUM_TLS_KEY_FILE")
    tls_proxy_approved = (
        os.environ.get("SANCTUM_TRUST_TLS_TERMINATION_PROXY", "").casefold() == "true"
    )
    if bool(certificate) != bool(private_key):
        raise typer.BadParameter(
            "Configure both SANCTUM_TLS_CERT_FILE and SANCTUM_TLS_KEY_FILE"
        )
    if (
        not certificate
        and not _is_loopback_bind_host(host)
        and not tls_proxy_approved
    ):
        raise typer.BadParameter(
            "Binding the API outside loopback requires TLS files or explicit approval "
            "of a TLS-terminating proxy"
        )
    if certificate and private_key and (
        not Path(certificate).is_file() or not Path(private_key).is_file()
    ):
        raise typer.BadParameter("Configured TLS certificate and key must be existing files")

    scheme = "https" if certificate else "http"
    display_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
    console.print(
        Panel.fit(
            _safe_text(
                f"[bold cyan]SANCTUM-SUITE REST & WEBSOCKET API SERVER[/bold cyan]\n"
                f"Endpoint: [yellow]{scheme}://{display_host}:{port}[/yellow]\n"
                f"Swagger Docs: [green]{scheme}://{display_host}:{port}/docs[/green]"
            ),
            border_style="cyan",
        )
    )
    uvicorn.run(
        "sanctum_suite.api.server:app",
        host=host,
        port=port,
        reload=False,
        ssl_certfile=certificate,
        ssl_keyfile=private_key,
    )


def _is_loopback_bind_host(host: str) -> bool:
    if host.casefold() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False

if __name__ == "__main__":
    app()