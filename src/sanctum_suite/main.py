import asyncio
import io
import hashlib
import hmac
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
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from sanctum_suite.core.secure_asset_loader import SecureAssetLoader, SECURE_STORAGE_DIR
from sanctum_suite.core.ai_model_loader import SecureAIModelManager, AI_MODELS_DIR
from sanctum_suite.core.offline_release_bundler import OfflineReleaseBundler, RELEASE_BUNDLE_DIR
from sanctum_suite.core.system_orchestrator import SystemOrchestrator
from sanctum_suite.core.offline_release_bundler import OfflineReleaseBundler

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
from sanctum_suite.core.parrot_lab import ParrotLabPreflight
from sanctum_suite.core.offline_release import (
    create_release_manifest,
    public_key_fingerprint,
    verify_release_manifest,
)
from sanctum_suite.core.signer import SecurityReportSigner
from sanctum_suite.core.audit_chain import (
    canonical_json,
    create_audit_checkpoint,
    verify_audit_checkpoint,
)
from sanctum_suite.core.zk_audit import (
    create_zk_audit_proof,
    verify_zk_audit_proof,
)
from sanctum_suite.core.immutable_audit import MinioImmutableAuditStore

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


def _print_json_report(report: dict[str, object]) -> None:
    print(json.dumps(report, indent=2))


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


@app.command(name="parrot-lab-preflight")
def parrot_lab_preflight_cmd(
    iso: Path = typer.Option(..., "--iso", help="Local Parrot ISO downloaded from the official source"),
    sha256: str = typer.Option(..., "--sha256", help="Expected SHA-256 from an independently verified official manifest"),
    edition: str = typer.Option(..., "--edition", help="Parrot edition, for example Security"),
    version: str = typer.Option(..., "--version", help="Exact version shown by the official download source"),
    architecture: str = typer.Option(..., "--architecture", help="Image architecture, for example amd64"),
) -> None:
    """Verify a local Parrot ISO digest and report a non-executing lab preflight."""
    try:
        result = ParrotLabPreflight().inspect(
            iso_path=iso,
            expected_sha256=sha256,
            edition=edition,
            version=version,
            architecture=architecture,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    _print_json_report(result)


@app.command(name="pqc-inventory")
def pqc_inventory_cmd(
    inventory_file: Path = typer.Option(
        ...,
        "--inventory",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="UTF-8 JSON array of operator-supplied cryptographic inventory entries",
    ),
) -> None:
    """Review a declared cryptographic inventory for PQC migration planning."""
    from sanctum_suite.core.post_quantum_pqc import (
        PostQuantumCryptographicAssuranceEngine,
    )

    try:
        if inventory_file.stat().st_size > 1_048_576:
            raise ValueError("Inventory file must not exceed 1 MiB")
        inventory = json.loads(inventory_file.read_text(encoding="utf-8"))
        if not isinstance(inventory, list) or len(inventory) > 1_000:
            raise ValueError("Inventory must be a JSON array with at most 1000 entries")
        result = PostQuantumCryptographicAssuranceEngine().audit_cryptographic_primitives(
            inventory
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    _print_json_report(result)


@app.command(name="pqc-kem-keygen")
def pqc_kem_keygen_cmd(
    key_directory: Path = typer.Option(
        ...,
        "--key-directory",
        file_okay=False,
        help="New directory for ML-KEM-768 and X25519 recipient keys",
    ),
) -> None:
    """Generate recipient keys for hybrid ML-KEM-768 and X25519 encryption."""
    from sanctum_suite.core.post_quantum_pqc import (
        generate_hybrid_encryption_key_pair,
    )

    if key_directory.exists():
        raise typer.BadParameter("Recipient key directory must not already exist")
    try:
        keys = generate_hybrid_encryption_key_pair()
        key_directory.mkdir(parents=True, exist_ok=False)
        if os.name != "nt":
            key_directory.chmod(0o700)
        for key_name, filename in (
            ("mlkem_private_key", "mlkem768-private.bin"),
            ("mlkem_public_key", "mlkem768-public.bin"),
            ("x25519_private_key", "x25519-private.bin"),
            ("x25519_public_key", "x25519-public.bin"),
        ):
            path = key_directory / filename
            if "private" in key_name:
                _write_private_audit_file(path, keys[key_name])
            else:
                with path.open("xb") as output:
                    output.write(keys[key_name])
    except OSError as error:
        raise typer.BadParameter(f"Hybrid KEM key generation failed: {error}") from error
    _print_json_report(
        {
            "status": "HYBRID_KEM_KEY_PAIR_CREATED",
            "algorithms": ["ML-KEM-768", "X25519"],
            "key_directory": str(key_directory),
            "private_keys_must_remain_confidential": True,
        }
    )


@app.command(name="pqc-encrypt")
def pqc_encrypt_cmd(
    input_file: Path = typer.Option(
        ...,
        "--input-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    mlkem_public_key_file: Path = typer.Option(
        ...,
        "--mlkem-public-key-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    x25519_public_key_file: Path = typer.Option(
        ...,
        "--x25519-public-key-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    output_file: Path = typer.Option(
        ...,
        "--output-file",
        file_okay=True,
        dir_okay=False,
    ),
) -> None:
    """Encrypt a file using hybrid ML-KEM-768 and X25519 key establishment."""
    from sanctum_suite.core.post_quantum_pqc import encrypt_hybrid

    if output_file.exists():
        raise typer.BadParameter("Encrypted output file must not already exist")
    try:
        if input_file.stat().st_size > 256_000_000:
            raise ValueError("Checkpoint plaintext exceeds the 256-megabyte size limit")
        envelope = encrypt_hybrid(
            input_file.read_bytes(),
            mlkem_public_key=mlkem_public_key_file.read_bytes(),
            x25519_public_key=x25519_public_key_file.read_bytes(),
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)
        _write_private_audit_file(output_file, envelope)
    except (OSError, TypeError, ValueError) as error:
        raise typer.BadParameter(f"Hybrid encryption failed: {error}") from error
    typer.echo(f"Created authenticated hybrid-encryption envelope: {output_file}")


@app.command(name="pqc-decrypt")
def pqc_decrypt_cmd(
    input_file: Path = typer.Option(
        ...,
        "--input-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    mlkem_private_key_file: Path = typer.Option(
        ...,
        "--mlkem-private-key-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    x25519_private_key_file: Path = typer.Option(
        ...,
        "--x25519-private-key-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    output_file: Path = typer.Option(
        ...,
        "--output-file",
        file_okay=True,
        dir_okay=False,
    ),
) -> None:
    """Authenticate and decrypt a hybrid ML-KEM-768 and X25519 envelope."""
    from sanctum_suite.core.post_quantum_pqc import decrypt_hybrid

    if output_file.exists():
        raise typer.BadParameter("Decrypted output file must not already exist")
    try:
        if input_file.stat().st_size > 260_000_000:
            raise ValueError("Encrypted checkpoint exceeds the 260-megabyte size limit")
        plaintext = decrypt_hybrid(
            input_file.read_bytes(),
            mlkem_private_key=mlkem_private_key_file.read_bytes(),
            x25519_private_key=x25519_private_key_file.read_bytes(),
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)
        _write_private_audit_file(output_file, plaintext)
    except (OSError, TypeError, ValueError) as error:
        raise typer.BadParameter(f"Hybrid decryption failed: {error}") from error
    typer.echo(f"Decrypted and authenticated file: {output_file}")


@app.command(name="security-readiness")
def security_readiness_cmd(
    input_file: Path = typer.Option(
        ...,
        "--input",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="UTF-8 JSON declarations for eBPF, Rust, SPIFFE/SPIRE, and cryptography",
    ),
) -> None:
    """Summarize operator-reported readiness for selected security technologies."""
    from sanctum_suite.core.security_readiness import SecurityReadinessAudit

    try:
        if input_file.stat().st_size > 1_048_576:
            raise ValueError("Input file must not exceed 1 MiB")
        declaration = json.loads(input_file.read_text(encoding="utf-8"))
        if not isinstance(declaration, dict):
            raise ValueError("Input must be a JSON object")
        result = SecurityReadinessAudit().audit(declaration)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    _print_json_report(result)


@app.command(name="supply-chain-verify")
def supply_chain_verify_cmd(
    artifact: Path = typer.Option(
        ...,
        "--artifact",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Local artifact whose SHA-256 is bound by the in-toto statement",
    ),
    attestation_bundle: Path = typer.Option(
        ...,
        "--attestation-bundle",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Sigstore JSON bundle containing the DSSE in-toto statement",
    ),
    certificate_identity: str = typer.Option(
        ...,
        "--certificate-identity",
        help="Exact expected signer certificate identity",
    ),
    certificate_oidc_issuer: str = typer.Option(
        ...,
        "--certificate-oidc-issuer",
        help="Exact expected OIDC issuer",
    ),
    predicate_type: str = typer.Option(
        ...,
        "--predicate-type",
        help="Exact expected in-toto predicate type URI",
    ),
    trivy_report: Path | None = typer.Option(
        None,
        "--trivy-report",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Optional Trivy JSON report to summarize",
    ),
    grype_report: Path | None = typer.Option(
        None,
        "--grype-report",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Optional Grype JSON report to summarize",
    ),
    cosign_command: str = typer.Option(
        "cosign",
        "--cosign-command",
        help="Cosign executable name or path",
    ),
) -> None:
    """Verify a local artifact's Sigstore in-toto attestation and summarize scans."""
    from sanctum_suite.core.supply_chain_verify import (
        SupplyChainArtifactVerifier,
        SupplyChainVerificationError,
    )

    try:
        report = SupplyChainArtifactVerifier().verify(
            artifact=artifact,
            attestation_bundle=attestation_bundle,
            certificate_identity=certificate_identity,
            certificate_oidc_issuer=certificate_oidc_issuer,
            predicate_type=predicate_type,
            trivy_report=trivy_report,
            grype_report=grype_report,
            cosign_command=cosign_command,
        )
    except SupplyChainVerificationError as error:
        raise typer.BadParameter(str(error)) from error
    _print_json_report(report)


@app.command(name="telemetry-archive")
def telemetry_archive_cmd(
    database: Path = typer.Option(
        ...,
        "--database",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Local SQLite database containing normalized telemetry events",
    ),
    output: Path = typer.Option(
        ...,
        "--output",
        help="Output Apache Parquet file",
    ),
    source_id: str | None = typer.Option(
        None,
        "--source-id",
        help="Optional configured telemetry source identifier",
    ),
    limit: int = typer.Option(
        100_000,
        "--limit",
        min=1,
        max=1_000_000,
        help="Maximum number of events to archive",
    ),
    wasm_module: Path | None = typer.Option(
        None,
        "--wasm-module",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Optional untrusted Wasm transform module",
    ),
    otlp_endpoint: str | None = typer.Option(
        None,
        "--otlp-endpoint",
        help="Explicit OTLP/HTTP trace Collector URL; no export by default",
    ),
) -> None:
    """Archive normalized telemetry to Parquet with optional Wasm and OTel."""
    from sanctum_suite.core.telemetry_pipeline import (
        TelemetryPipelineError,
        archive_telemetry,
    )

    try:
        report = archive_telemetry(
            database=database,
            output=output,
            source_id=source_id,
            limit=limit,
            wasm_module=wasm_module,
            otlp_endpoint=otlp_endpoint,
        )
    except TelemetryPipelineError as error:
        raise typer.BadParameter(str(error)) from error
    _print_json_report(report)


@app.command(name="fhe-keygen")
def fhe_keygen_cmd(
    public_key_file: Path = typer.Option(
        ..., "--public-key-file", help="Output public Microsoft SEAL key"
    ),
    private_key_file: Path = typer.Option(
        ..., "--private-key-file", help="Client-held private FHE key; protect this file"
    ),
    parameters_file: Path = typer.Option(
        ..., "--parameters-file", help="Output BFV parameter metadata JSON"
    ),
) -> None:
    """Create client-held BFV keys for encrypted integer aggregation."""
    from sanctum_suite.core.privacy_graph import (
        PrivacyGraphError,
        create_fhe_keypair,
    )

    try:
        report = create_fhe_keypair(
            public_key_path=public_key_file,
            private_key_path=private_key_file,
            parameters_path=parameters_file,
        )
    except PrivacyGraphError as error:
        raise typer.BadParameter(str(error)) from error
    _print_json_report(report)


@app.command(name="fhe-accelerator-status")
def fhe_accelerator_status_cmd() -> None:
    """Report CPU FHE and accelerator tooling without claiming hardware offload."""
    from sanctum_suite.core.privacy_graph import fhe_accelerator_capabilities

    _print_json_report(fhe_accelerator_capabilities())


@app.command(name="security-capabilities")
def security_capabilities_cmd() -> None:
    """Report explicit configuration status for FHE, QKD, local TEE inference, and platform technology stacks."""
    from sanctum_suite.core.privacy_graph import fhe_accelerator_capabilities
    from sanctum_suite.core.qkd import qkd_capabilities
    from sanctum_suite.core.self_healing_coordinator import tee_model_capabilities
    from sanctum_suite.core.technology_stack_catalog import platform_technology_capabilities

    _print_json_report(
        {
            "fhe": fhe_accelerator_capabilities(),
            "qkd": qkd_capabilities(),
            "tee_local_model": tee_model_capabilities(),
            "technology_stack": platform_technology_capabilities(),
            "self_healing": {
                "mode": "OPERATOR_APPROVAL_REQUIRED",
                "automatic_policy_deployment": False,
                "automatic_key_rotation": False,
            },
        }
    )


@app.command(name="self-healing-propose")
def self_healing_propose_cmd(
    database_file: Path = typer.Option(
        ...,
        "--database-file",
        help="Append-only SQLite approval journal",
    ),
    target_module: str = typer.Option(..., "--target-module"),
    action: str = typer.Option(
        ...,
        "--action",
        help="Proposed action: opa_policy_update or key_rotation",
    ),
    reason_code: str = typer.Option(..., "--reason-code"),
    evidence_sha256: str = typer.Option(..., "--evidence-sha256"),
    current_policy_version: str = typer.Option(..., "--current-policy-version"),
    proposed_change_sha256: str = typer.Option(..., "--proposed-change-sha256"),
    created_by: str = typer.Option(..., "--created-by"),
) -> None:
    """Record a remediation proposal for independent human review; never applies it."""
    from sanctum_suite.core.self_healing_coordinator import (
        AutonomousSelfHealingCoordinator,
    )

    try:
        report = AutonomousSelfHealingCoordinator(database_file).propose_remediation(
            target_module=target_module,
            action=action,
            reason_code=reason_code,
            evidence_sha256=evidence_sha256,
            current_policy_version=current_policy_version,
            proposed_change_sha256=proposed_change_sha256,
            created_by=created_by,
        )
    except (OSError, RuntimeError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    _print_json_report(report)


@app.command(name="self-healing-decide")
def self_healing_decide_cmd(
    database_file: Path = typer.Option(
        ...,
        "--database-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Append-only SQLite approval journal",
    ),
    proposal_id: str = typer.Option(..., "--proposal-id"),
    approver_id: str = typer.Option(..., "--approver-id"),
    approve: bool = typer.Option(
        ...,
        "--approve/--reject",
        help="Approve for subsequent manual deployment or reject the proposal",
    ),
) -> None:
    """Record an independent approval decision without applying the proposed change."""
    from sanctum_suite.core.self_healing_coordinator import (
        AutonomousSelfHealingCoordinator,
    )

    try:
        report = AutonomousSelfHealingCoordinator(database_file).decide_proposal(
            proposal_id=proposal_id,
            approver_id=approver_id,
            approved=approve,
        )
    except (OSError, RuntimeError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    _print_json_report(report)


@app.command(name="self-healing-list")
def self_healing_list_cmd(
    database_file: Path = typer.Option(
        ...,
        "--database-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Append-only SQLite approval journal",
    ),
) -> None:
    """Verify and list self-healing proposals and their operator decisions."""
    from sanctum_suite.core.self_healing_coordinator import (
        AutonomousSelfHealingCoordinator,
    )

    try:
        proposals = AutonomousSelfHealingCoordinator(database_file).list_proposals()
    except (OSError, RuntimeError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    _print_json_report(
        {
            "status": "PROPOSAL_JOURNAL_VERIFIED",
            "automatic_changes_applied": False,
            "proposals": proposals,
        }
    )


@app.command(name="fhe-decrypt-sum")
def fhe_decrypt_sum_cmd(
    parameters_file: Path = typer.Option(
        ...,
        "--parameters-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="BFV parameters JSON from sanctum fhe-keygen",
    ),
    private_key_file: Path = typer.Option(
        ...,
        "--private-key-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Client-held Microsoft SEAL private key",
    ),
    ciphertext_file: Path = typer.Option(
        ...,
        "--ciphertext-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Encrypted aggregate.seal from privacy-graph-import",
    ),
) -> None:
    """Decrypt the FHE integer sum on the client holding the private key."""
    from sanctum_suite.core.privacy_graph import (
        PrivacyGraphError,
        decrypt_fhe_sum,
    )

    try:
        report = decrypt_fhe_sum(
            parameters_path=parameters_file,
            private_key_path=private_key_file,
            ciphertext_path=ciphertext_file,
        )
    except PrivacyGraphError as error:
        raise typer.BadParameter(str(error)) from error
    _print_json_report(report)


@app.command(name="privacy-graph-import")
def privacy_graph_import_cmd(
    graph_file: Path = typer.Option(
        ...,
        "--graph-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Case-scoped normalized graph JSON with nodes and edges arrays",
    ),
    scores_file: Path = typer.Option(
        ...,
        "--scores-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Client-side JSON array of node_id and integer score entries",
    ),
    case_id: str = typer.Option(..., "--case-id", help="Case identifier in graph JSON"),
    public_key_file: Path = typer.Option(
        ...,
        "--public-key-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Public Microsoft SEAL key",
    ),
    parameters_file: Path = typer.Option(
        ...,
        "--parameters-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="BFV parameters JSON from sanctum fhe-keygen",
    ),
    dsn_file: Path = typer.Option(
        ...,
        "--dsn-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Protected PostgreSQL connection string file for Apache AGE",
    ),
    graph_name: str = typer.Option("sanctum", "--graph-name"),
    pkcs11_module: str = typer.Option(
        ..., "--pkcs11-module", help="Path to the vendor PKCS#11 library"
    ),
    token_label: str = typer.Option(..., "--token-label"),
    signing_key_label: str = typer.Option(..., "--signing-key-label"),
    pin_file: Path = typer.Option(
        ...,
        "--pin-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Protected PKCS#11 PIN secret file; never pass a PIN directly",
    ),
    certificate_file: Path = typer.Option(
        ...,
        "--certificate-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="PEM or DER RSA certificate corresponding to the HSM signing key",
    ),
    output_directory: Path = typer.Option(
        ...,
        "--output-directory",
        help="New directory for signed manifest and encrypted aggregate",
    ),
) -> None:
    """Import a case graph into Apache AGE with FHE score aggregation and HSM signing."""
    from sanctum_suite.core.privacy_graph import (
        ApacheAGEGraphStore,
        PKCS11ManifestSigner,
        PrivacyGraphError,
        create_private_graph_bundle,
    )

    try:
        graph_store = ApacheAGEGraphStore(
            dsn_file=dsn_file,
            graph_name=graph_name,
        )
        signer = PKCS11ManifestSigner(
            module_path=pkcs11_module,
            token_label=token_label,
            key_label=signing_key_label,
            pin_file=pin_file,
            certificate_file=certificate_file,
        )
        report = create_private_graph_bundle(
            graph_path=graph_file,
            scores_path=scores_file,
            case_id=case_id,
            public_key_path=public_key_file,
            parameters_path=parameters_file,
            output_directory=output_directory,
            graph_store=graph_store,
            signer=signer,
        )
    except PrivacyGraphError as error:
        raise typer.BadParameter(str(error)) from error
    _print_json_report(report)


@app.command(name="privacy-graph-verify")
def privacy_graph_verify_cmd(
    manifest_file: Path = typer.Option(
        ...,
        "--manifest-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    signature_file: Path = typer.Option(
        ...,
        "--signature-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    ciphertext_file: Path = typer.Option(
        ...,
        "--ciphertext-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="FHE aggregate ciphertext to verify against the signed digest",
    ),
    certificate_file: Path = typer.Option(
        ...,
        "--certificate-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Trusted PEM or DER RSA signer certificate",
    ),
) -> None:
    """Verify a private graph manifest signature and its HSM certificate fingerprint."""
    from sanctum_suite.core.privacy_graph import (
        PrivacyGraphError,
        verify_signed_manifest,
    )

    try:
        report = verify_signed_manifest(
            manifest_path=manifest_file,
            signature_path=signature_file,
            ciphertext_path=ciphertext_file,
            certificate_path=certificate_file,
        )
    except PrivacyGraphError as error:
        raise typer.BadParameter(str(error)) from error
    _print_json_report(report)


@app.command(name="generate-executive-report")
def generate_executive_report_cmd(
    readiness_report: Path = typer.Option(
        ...,
        "--readiness-report",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="JSON output from sanctum security-readiness",
    ),
    supply_chain_report: Path = typer.Option(
        ...,
        "--supply-chain-report",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="JSON output from sanctum supply-chain-verify",
    ),
    opa_test_report: Path = typer.Option(
        ...,
        "--opa-test-report",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="JSON array output from opa test --format=json --fail-on-empty",
    ),
    output_json: Path = typer.Option(..., "--output-json", help="JSON report path"),
    output_markdown: Path = typer.Option(
        ..., "--output-markdown", help="Markdown report path"
    ),
) -> None:
    """Combine readiness, supply-chain, and OPA test reports for audit review."""
    from sanctum_suite.core.executive_report import (
        ExecutiveReportError,
        build_executive_report,
        load_executive_report_inputs,
        render_executive_report_markdown,
    )

    try:
        input_paths = {
            path.resolve()
            for path in (readiness_report, supply_chain_report, opa_test_report)
        }
        output_paths = {output_json.resolve(), output_markdown.resolve()}
        if len(output_paths) != 2:
            raise ExecutiveReportError("JSON and Markdown outputs must be different files")
        if input_paths & output_paths:
            raise ExecutiveReportError("Output files must not overwrite input reports")
        if any(not path.parent.is_dir() for path in output_paths):
            raise ExecutiveReportError("Output parent directories must already exist")

        inputs = load_executive_report_inputs(
            readiness_report, supply_chain_report, opa_test_report
        )
        report = build_executive_report(inputs)
        output_json.write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        output_markdown.write_text(
            render_executive_report_markdown(report), encoding="utf-8"
        )
    except (ExecutiveReportError, OSError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(
        f"Executive report status: {report['status']}; "
        f"JSON: {output_json}; Markdown: {output_markdown}"
    )


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


@app.command(name="offline-release-create")
def offline_release_create_cmd(
    artifact_directory: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        writable=True,
    ),
    source_revision: str = typer.Option(
        ...,
        "--source-revision",
        help="Full 40-64 character Git revision represented by this bundle",
    ),
    private_key_file: Path = typer.Option(
        ...,
        "--private-key-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
) -> None:
    """Sign the exact file inventory of a release bundle on an authorized signing station."""
    bundle_root = artifact_directory.resolve()
    if private_key_file.resolve().is_relative_to(bundle_root):
        raise typer.BadParameter("Release signing key must be stored outside the bundle")
    try:
        private_key_bytes = private_key_file.read_bytes()
    except OSError as error:
        raise typer.BadParameter("Cannot read private-key file") from error
    password = None
    if b"ENCRYPTED PRIVATE KEY" in private_key_bytes:
        password = typer.prompt("Private key password", hide_input=True).encode("utf-8")
    try:
        private_key = serialization.load_pem_private_key(
            private_key_bytes,
            password=password,
        )
    except (TypeError, ValueError) as error:
        raise typer.BadParameter("Private-key file or password is invalid") from error
    if not isinstance(private_key, Ed25519PrivateKey):
        raise typer.BadParameter("Release signing key must use Ed25519")
    try:
        manifest = create_release_manifest(
            artifact_directory,
            source_revision=source_revision,
            private_key=private_key,
        )
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(
        f"Signed {len(manifest['artifacts'])} artifact(s); signer SHA-256: "
        f"{manifest['signer_sha256']}"
    )


@app.command(name="offline-release-verify")
def offline_release_verify_cmd(
    artifact_directory: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    public_key_file: Path = typer.Option(
        ...,
        "--public-key-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    expected_signer_fingerprint: str = typer.Option(
        ...,
        "--expected-signer-fingerprint",
        help="SHA-256 fingerprint obtained independently through a trusted channel",
    ),
) -> None:
    """Verify a signed offline release using an independently trusted public key."""
    if public_key_file.resolve().is_relative_to(artifact_directory.resolve()):
        raise typer.BadParameter("Trusted public key must be stored outside the bundle")
    try:
        public_key = serialization.load_pem_public_key(public_key_file.read_bytes())
    except (OSError, ValueError) as error:
        raise typer.BadParameter("Public-key file is invalid or unreadable") from error
    if not isinstance(public_key, Ed25519PublicKey):
        raise typer.BadParameter("Release verification key must use Ed25519")
    try:
        manifest = verify_release_manifest(
            artifact_directory,
            public_key=public_key,
            expected_signer_fingerprint=expected_signer_fingerprint.lower(),
        )
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(
        f"Verified {len(manifest['artifacts'])} artifact(s) for revision "
        f"{manifest['source_revision']}; signer SHA-256: {manifest['signer_sha256']}"
    )


@app.command(name="report-verify")
def report_verify_cmd(
    report_file: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    public_key_file: Path = typer.Option(
        ...,
        "--public-key-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
) -> None:
    """Verify a signed API report with an independently trusted RSA public key."""
    try:
        document = json.loads(report_file.read_bytes())
        public_key_pem = public_key_file.read_bytes()
    except (OSError, json.JSONDecodeError) as error:
        raise typer.BadParameter("Report or public-key file is invalid or unreadable") from error
    if not isinstance(document, dict):
        raise typer.BadParameter("Signed report must be a JSON object")
    signature_record = document.pop("report_signature", None)
    if not isinstance(signature_record, dict) or set(signature_record) != {
        "algorithm",
        "signer_sha256",
        "signature_base64",
    }:
        raise typer.BadParameter("Report signature metadata is missing or invalid")
    if signature_record["algorithm"] != "RSA-PSS-SHA256":
        raise typer.BadParameter("Unsupported report signature algorithm")
    if not all(
        isinstance(signature_record[field], str)
        for field in ("signer_sha256", "signature_base64")
    ):
        raise typer.BadParameter("Report signature metadata has invalid field types")
    report_digest = document.get("report_sha256")
    digest_payload = {
        key: value for key, value in document.items() if key != "report_sha256"
    }
    canonical_digest_payload = json.dumps(
        digest_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    if not isinstance(report_digest, str) or not hmac.compare_digest(
        report_digest, hashlib.sha256(canonical_digest_payload).hexdigest()
    ):
        raise typer.BadParameter("Report SHA-256 digest does not match its content")
    try:
        public_key = serialization.load_pem_public_key(public_key_pem)
        public_key_der = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        signer_fingerprint = hashlib.sha256(public_key_der).hexdigest()
        if not hmac.compare_digest(signature_record["signer_sha256"], signer_fingerprint):
            raise ValueError("Report signer fingerprint does not match trusted public key")
        signed_payload = json.dumps(
            document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        SecurityReportSigner.verify_bytes(
            signed_payload,
            signature_record["signature_base64"],
            public_key_pem,
        )
    except (TypeError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(
        f"Verified report; signer SHA-256: {signer_fingerprint}; "
        f"report SHA-256: {report_digest}"
    )


def _write_private_audit_file(path: Path, content: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        output.write(content)
    if os.name != "nt":
        path.chmod(0o600)


@app.command(name="audit-checkpoint")
def audit_checkpoint_cmd(
    archive_directory: Path = typer.Option(
        ...,
        "--archive-directory",
        file_okay=False,
        help="New directory for the version-pinned audit record export",
    ),
    checkpoint_file: Path = typer.Option(
        ...,
        "--checkpoint-file",
        file_okay=True,
        dir_okay=False,
        help="New output file for the RSA-signed hash-chain checkpoint",
    ),
) -> None:
    """Export locked audit versions and create a signed chain checkpoint."""
    if archive_directory.exists():
        raise typer.BadParameter("Audit archive directory must not already exist")
    if checkpoint_file.exists():
        raise typer.BadParameter("Audit checkpoint file must not already exist")
    try:
        store = MinioImmutableAuditStore()
        stored_records = store.read_audit_records()
        signer = SecurityReportSigner()
        records = [
            {
                "key": str(record["key"]),
                "version_id": str(record["version_id"]),
                "record_sha256": str(record["record_sha256"]),
            }
            for record in stored_records
        ]
        checkpoint = create_audit_checkpoint(
            bucket=store.bucket,
            records=records,
            signer=signer,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        archive_directory.mkdir(parents=True, exist_ok=False)
        if os.name != "nt":
            archive_directory.chmod(0o700)
        for record in stored_records:
            object_path = archive_directory / Path(str(record["key"]))
            object_path.parent.mkdir(parents=True, exist_ok=True)
            if os.name != "nt":
                object_path.parent.chmod(0o700)
            body = record["body"]
            if not isinstance(body, bytes):
                raise ValueError("MinIO returned an invalid audit record body")
            _write_private_audit_file(object_path, body)
        checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        _write_private_audit_file(
            checkpoint_file,
            canonical_json(checkpoint) + b"\n",
        )
    except (OSError, ValueError, RuntimeError) as error:
        raise typer.BadParameter(
            "Audit checkpoint creation failed; any partial export is not verifiable "
            "and must not be used"
        ) from error
    typer.echo(
        f"Created signed checkpoint for {len(records)} immutable audit object version(s); "
        f"chain head: {checkpoint['chain_head_sha256']}"
    )


@app.command(name="audit-verify")
def audit_verify_cmd(
    checkpoint_file: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    archive_directory: Path = typer.Option(
        ...,
        "--archive-directory",
        exists=True,
        file_okay=False,
        readable=True,
    ),
    public_key_file: Path = typer.Option(
        ...,
        "--public-key-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    pqc_public_key_file: Path | None = typer.Option(
        None,
        "--pqc-public-key-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Independently trusted raw ML-DSA-65 public key for hybrid checkpoints",
    ),
) -> None:
    """Verify an exported WORM audit chain using an independently trusted key."""
    try:
        if checkpoint_file.stat().st_size > 256_000_000:
            raise ValueError("Audit checkpoint exceeds the 256-megabyte size limit")
        checkpoint = json.loads(checkpoint_file.read_bytes())
        public_key_pem = public_key_file.read_bytes()
        if not isinstance(checkpoint, dict):
            raise ValueError("Audit checkpoint must be a JSON object")
        result = verify_audit_checkpoint(
            checkpoint=checkpoint,
            archive_directory=archive_directory,
            public_key_pem=public_key_pem,
            pqc_public_key=(
                pqc_public_key_file.read_bytes()
                if pqc_public_key_file is not None
                else None
            ),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(
        f"Verified {result['record_count']} audit object version(s); "
        f"chain head: {result['chain_head_sha256']}; "
        f"signer SHA-256: {result['signer_sha256']}"
    )


@app.command(name="ledger-anchor")
def ledger_anchor_cmd(
    checkpoint_file: Path = typer.Option(
        ...,
        "--checkpoint-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Signed audit checkpoint to verify and anchor by SHA-256",
    ),
    archive_directory: Path = typer.Option(
        ...,
        "--archive-directory",
        exists=True,
        file_okay=False,
        readable=True,
        help="Version-pinned archive used to verify the checkpoint",
    ),
    checkpoint_public_key_file: Path = typer.Option(
        ...,
        "--checkpoint-public-key-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    checkpoint_pqc_public_key_file: Path | None = typer.Option(
        None,
        "--checkpoint-pqc-public-key-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Independently trusted ML-DSA-65 key for hybrid checkpoints",
    ),
    backend: str = typer.Option(..., "--backend", help="Ledger backend: local or fabric"),
    database_file: Path | None = typer.Option(
        None,
        "--database-file",
        help="SQLite path for the local demonstration ledger",
    ),
    fabric_gateway_url: str | None = typer.Option(
        None,
        "--fabric-gateway-url",
        envvar="SANCTUM_LEDGER_FABRIC_GATEWAY_URL",
    ),
    fabric_channel: str | None = typer.Option(
        None,
        "--fabric-channel",
        envvar="SANCTUM_LEDGER_FABRIC_CHANNEL",
    ),
    fabric_chaincode: str | None = typer.Option(
        None,
        "--fabric-chaincode",
        envvar="SANCTUM_LEDGER_FABRIC_CHAINCODE",
    ),
    fabric_ca_file: Path | None = typer.Option(
        None,
        "--fabric-ca-file",
        envvar="SANCTUM_LEDGER_FABRIC_CA_FILE",
    ),
    fabric_client_certificate_file: Path | None = typer.Option(
        None,
        "--fabric-client-certificate-file",
        envvar="SANCTUM_LEDGER_FABRIC_CLIENT_CERT_FILE",
    ),
    fabric_client_key_file: Path | None = typer.Option(
        None,
        "--fabric-client-key-file",
        envvar="SANCTUM_LEDGER_FABRIC_CLIENT_KEY_FILE",
    ),
) -> None:
    """Verify an audit checkpoint, require fresh TEE attestation, and anchor its digest."""
    from sanctum_suite.core.private_ledger import (
        FabricGatewayLedger,
        LocalPrivateLedger,
        PrivateLedgerError,
        anchor_verified_checkpoint,
    )
    from sanctum_suite.core.tee_attestation import (
        TEEAttestationConfigurationError,
        TEEAttestationUnavailable,
        TEEClaimsClient,
    )

    try:
        if checkpoint_file.stat().st_size > 256_000_000:
            raise ValueError("Audit checkpoint exceeds the 256-megabyte size limit")
        checkpoint_bytes = checkpoint_file.read_bytes()
        checkpoint = json.loads(checkpoint_bytes)
        if not isinstance(checkpoint, dict):
            raise ValueError("Audit checkpoint must be a JSON object")
        verify_audit_checkpoint(
            checkpoint=checkpoint,
            archive_directory=archive_directory,
            public_key_pem=checkpoint_public_key_file.read_bytes(),
            pqc_public_key=(
                checkpoint_pqc_public_key_file.read_bytes()
                if checkpoint_pqc_public_key_file is not None
                else None
            ),
        )
        if backend == "local":
            if database_file is None:
                raise ValueError("--database-file is required for the local backend")
            ledger = LocalPrivateLedger(database_file)
        elif backend == "fabric":
            if not all(
                (
                    fabric_gateway_url,
                    fabric_channel,
                    fabric_chaincode,
                    fabric_ca_file,
                    fabric_client_certificate_file,
                    fabric_client_key_file,
                )
            ):
                raise ValueError(
                    "Fabric backend requires gateway URL, channel, chaincode, "
                    "CA, client certificate, and client key configuration"
                )
            ledger = FabricGatewayLedger(
                gateway_url=fabric_gateway_url,
                channel=fabric_channel,
                chaincode=fabric_chaincode,
                ca_certificate_file=fabric_ca_file,
                client_certificate_file=fabric_client_certificate_file,
                client_key_file=fabric_client_key_file,
            )
        else:
            raise ValueError("--backend must be either local or fabric")

        attestation_client = TEEClaimsClient.from_environment(required=True)
        if attestation_client is None:
            raise TEEAttestationConfigurationError(
                "A configured SGX/SNP claims verifier is required"
            )
        checkpoint_sha256 = hashlib.sha256(checkpoint_bytes).hexdigest()
        attestation = asyncio.run(
            attestation_client.verify_readiness(
                operation_digest=checkpoint_sha256
            )
        )
        report = anchor_verified_checkpoint(
            checkpoint_bytes=checkpoint_bytes,
            attestation=attestation,
            ledger=ledger,
        )
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        TypeError,
        ValueError,
        RuntimeError,
        TEEAttestationConfigurationError,
        TEEAttestationUnavailable,
        PrivateLedgerError,
    ) as error:
        raise typer.BadParameter(
            f"Ledger anchoring failed; no audit payload was submitted: {error}"
        ) from error
    _print_json_report(report)


@app.command(name="ledger-verify")
def ledger_verify_cmd(
    database_file: Path = typer.Option(
        ...,
        "--database-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="SQLite database used by the local demonstration ledger",
    ),
) -> None:
    """Verify the local demonstration ledger hash chain."""
    from sanctum_suite.core.private_ledger import (
        LocalPrivateLedger,
        PrivateLedgerError,
    )

    try:
        result = LocalPrivateLedger(database_file).verify()
    except (OSError, RuntimeError, PrivateLedgerError) as error:
        raise typer.BadParameter(str(error)) from error
    _print_json_report(result)


@app.command(name="ledger-consistency")
def ledger_consistency_cmd(
    database_file: Path = typer.Option(
        ...,
        "--database-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    old_tree_size: int = typer.Option(
        ...,
        "--old-tree-size",
        min=0,
        help="Previously retained Merkle tree size",
    ),
    old_tree_root_sha256: str = typer.Option(
        ...,
        "--old-tree-root-sha256",
        help="Previously retained Merkle root in lowercase SHA-256 hex",
    ),
) -> None:
    """Produce a consistency proof from a previously retained local-ledger tree head."""
    from sanctum_suite.core.private_ledger import (
        LocalPrivateLedger,
        PrivateLedgerError,
    )

    try:
        result = LocalPrivateLedger(database_file).consistency_proof(
            old_tree_size=old_tree_size,
            old_tree_root_sha256=old_tree_root_sha256,
        )
    except (OSError, RuntimeError, PrivateLedgerError) as error:
        raise typer.BadParameter(str(error)) from error
    _print_json_report(result)


@app.command(name="smpc-aggregate-demo")
def smpc_aggregate_demo_cmd(
    party_0_input_file: Path = typer.Option(
        ...,
        "--party-0-input-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="JSON input file containing only this party's bounded integer value",
    ),
    party_1_input_file: Path = typer.Option(
        ...,
        "--party-1-input-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="JSON input file containing only this party's bounded integer value",
    ),
    party_2_input_file: Path = typer.Option(
        ...,
        "--party-2-input-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="JSON input file containing only this party's bounded integer value",
    ),
    decision_threshold: int = typer.Option(
        ...,
        "--decision-threshold",
        min=0,
        max=3_000_000,
        help="Public aggregate threshold; only the aggregate and threshold bit are revealed",
    ),
) -> None:
    """Run a three-party local MPyC sum and reveal only aggregate outputs."""
    from sanctum_suite.core.smpc import SMPCError, run_local_smpc_demo

    try:
        report = run_local_smpc_demo(
            participant_input_files=[
                party_0_input_file,
                party_1_input_file,
                party_2_input_file,
            ],
            decision_threshold=decision_threshold,
        )
    except SMPCError as error:
        raise typer.BadParameter(str(error)) from error
    _print_json_report(report)


@app.command(name="audit-zk-prove")
def audit_zk_prove_cmd(
    checkpoint_file: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    archive_directory: Path = typer.Option(
        ...,
        "--archive-directory",
        exists=True,
        file_okay=False,
        readable=True,
    ),
    checkpoint_public_key_file: Path = typer.Option(
        ...,
        "--checkpoint-public-key-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    checkpoint_pqc_public_key_file: Path | None = typer.Option(
        None,
        "--checkpoint-pqc-public-key-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Independently trusted ML-DSA-65 key for hybrid checkpoints",
    ),
    wasm_file: Path = typer.Option(
        ...,
        "--wasm-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    proving_key_file: Path = typer.Option(
        ...,
        "--proving-key-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    verification_key_file: Path = typer.Option(
        ...,
        "--verification-key-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    output_file: Path = typer.Option(
        ...,
        "--output-file",
        file_okay=True,
        dir_okay=False,
        help="New output path for the signed Groth16 proof bundle",
    ),
) -> None:
    """Prove the v1.0 access-control rule over a verified complete WORM snapshot."""
    try:
        binding = create_zk_audit_proof(
            checkpoint_file=checkpoint_file,
            archive_directory=archive_directory,
            checkpoint_public_key_file=checkpoint_public_key_file,
            checkpoint_pqc_public_key_file=checkpoint_pqc_public_key_file,
            wasm_file=wasm_file,
            proving_key_file=proving_key_file,
            verification_key_file=verification_key_file,
            output_file=output_file,
            signer=SecurityReportSigner(),
        )
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        raise typer.BadParameter(f"ZK audit proof creation failed: {error}") from error
    typer.echo(
        f"Created signed Groth16 proof for {binding['record_count']} audit version(s); "
        f"Poseidon root: {binding['poseidon_root']}"
    )


@app.command(name="audit-zk-verify")
def audit_zk_verify_cmd(
    proof_file: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    checkpoint_file: Path = typer.Option(
        ...,
        "--checkpoint-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    archive_directory: Path = typer.Option(
        ...,
        "--archive-directory",
        exists=True,
        file_okay=False,
        readable=True,
    ),
    checkpoint_public_key_file: Path = typer.Option(
        ...,
        "--checkpoint-public-key-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    checkpoint_pqc_public_key_file: Path | None = typer.Option(
        None,
        "--checkpoint-pqc-public-key-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Independently trusted ML-DSA-65 key for hybrid checkpoints",
    ),
    verification_key_file: Path = typer.Option(
        ...,
        "--verification-key-file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
) -> None:
    """Verify a Groth16 proof, its signature, and its complete WORM snapshot binding."""
    try:
        binding = verify_zk_audit_proof(
            proof_file=proof_file,
            checkpoint_file=checkpoint_file,
            archive_directory=archive_directory,
            checkpoint_public_key_file=checkpoint_public_key_file,
            checkpoint_pqc_public_key_file=checkpoint_pqc_public_key_file,
            verification_key_file=verification_key_file,
        )
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        raise typer.BadParameter(f"ZK audit proof verification failed: {error}") from error
    typer.echo(
        f"Verified Groth16 proof for {binding['record_count']} audit version(s); "
        f"policy: {binding['policy_id']}; chain head: {binding['chain_head_sha256']}"
    )


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
        access_log=False,
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

@app.command(name="provision-threat-intel")
def provision_threat_intel_cmd(
    filename: str = typer.Option("threat_intel_feed.db", help="Nazwa pliku bazy Threat Intel"),
    expected_sha256: str = typer.Option(..., "--sha256", help="Oczekiwana suma kontrolna SHA-256"),
) -> None:
    """Weryfikuje i montuje ciężką bazę Threat Intelligence (~1.8 GB)."""
    try:
        loader = SecureAssetLoader(SECURE_STORAGE_DIR)
        loader.provision_asset(filename, expected_sha256)
        typer.echo(f"Pomyślnie zweryfikowano i zamontowano zasób: {filename}")
    except Exception as error:
        raise typer.BadParameter(str(error)) from error


@app.command(name="verify-ai-model")
def verify_ai_model_cmd(
    model_filename: str = typer.Option("local_anomaly_detector.onnx", help="Nazwa pliku modelu ONNX/PyTorch"),
    expected_sha256: str = typer.Option(..., "--sha256", help="Oczekiwana suma kontrolna SHA-256 wag"),
) -> None:
    """Weryfikuje nienaruszalność lokalnego modelu AI (~2.2 GB) przed inferencją."""
    try:
        manager = SecureAIModelManager(AI_MODELS_DIR)
        path = manager.load_heavy_model(model_filename, expected_sha256)
        typer.echo(f"Model AI zweryfikowany i gotowy w ścieżce: {path}")
    except Exception as error:
        raise typer.BadParameter(str(error)) from error


@app.command(name="unpack-offline-bundle")
def unpack_offline_bundle_cmd(
    bundle_filename: str = typer.Option("sanctum_offline_bundle_v6.tar.gz", help="Paczka wdrożeniowa OCI/Helm"),
    expected_sha256: str = typer.Option(..., "--sha256", help="Suma kontrolna paczki Air-Gapped"),
    target_path: Path = typer.Option(Path("/opt/sanctum/runtime"), "--target", help="Katalog docelowy wdrożenia"),
) -> None:
    """Weryfikuje i rozpakowuje archiwum wdrożeniowe w trybie offline (~1.5 GB)."""
    try:
        bundler = OfflineReleaseBundler(RELEASE_BUNDLE_DIR)
        bundler.unpack_airgap_payload(bundle_filename, expected_sha256, target_path)
        typer.echo(f"Wdrożono paczkę offline do: {target_path}")
    except Exception as error:
        raise typer.BadParameter(str(error)) from error

@app.command("preflight")
def cmd_preflight():
    """Uruchamia pełny audyt wstępny i weryfikację środowiska systemowego."""
    console.print("[bold cyan][*] Uruchamianie procedury pre-flight Sanctum Suite...[/bold cyan]")
    try:
        orchestrator = SystemOrchestrator()
        report = orchestrator.run_system_preflight()
        
        table = Table(title="Raport pre-flight systemu")
        table.add_column("Komponent / Sprawdzenie", style="cyan")
        table.add_column("Status", style="green")
        
        for k, v in report.get("checks", {}).items():
            status_str = "[green]OK (Znaleziono)[/green]" if v else "[red]BŁĄD (Brak zasobu)[/red]"
            table.add_row(k, status_str)
            
        console.print(table)
        console.print(f"[bold green][+] Ogólny status systemu: {report.get('overall_status').upper()}[/bold green]")
    except Exception as e:
        console.print(f"[bold red][!] Błąd krytyczny pre-flight: {e}[/bold red]")
        raise typer.Exit(code=1)

@app.command("analyze-ioc")
def cmd_analyze_ioc(hash_value: str = typer.Argument(..., help="Suma kontrolna / IOC do przeanalizowania")):
    """Analizuje pojedynczy wskaźnik zagrożenia (IOC) w lokalnej bazie APT."""
    console.print(f"[bold cyan][*] Analiza wskaźnika IOC: {hash_value}[/bold cyan]")
    try:
        orchestrator = SystemOrchestrator()
        result = orchestrator.execute_threat_analysis_pipeline([hash_value])
        
        results_list = result.get("results", [])
        if results_list:
            res = results_list[0]
            if res.get("matched"):
                console.print(f"[bold red][!] WYKRYTO ZAGROŻENIE![/bold red]")
                console.print(f"    Kampania: [yellow]{res.get('campaign')}[/yellow]")
                console.print(f"    Aktor APT: [yellow]{res.get('threat_actor')}[/yellow]")
                console.print(f"    Poziom pewności: [yellow]{res.get('confidence')}%[/yellow]")
            else:
                console.print("[green][+] Wskaźnik czysty. Brak dopasowań w bazie Threat Intel.[/green]")
    except Exception as e:
        console.print(f"[bold red][!] Błąd analizy IOC: {e}[/bold red]")
        raise typer.Exit(code=1)

@app.command("pack")
def cmd_pack(source_dir: Path = typer.Argument(..., help="Katalog źródłowy do spakowania"), name: str = typer.Option("sanctum_release", help="Nazwa paczki")):
    """Tworzy szyfrowaną paczkę dystrybucyjną offline z manifestem SHA-256."""
    console.print(f"[bold cyan][*] Pakowanie zasobów z {source_dir}...[/bold cyan]")
    try:
        bundler = OfflineReleaseBundler()
        manifest = bundler.create_release_bundle(source_dir, name)
        console.print(f"[bold green][+] Utworzono paczkę:[/bold green] {manifest.get('filename')}")
        console.print(f"    SHA-256: [cyan]{manifest.get('sha256')}[/cyan]")
    except Exception as e:
        console.print(f"[bold red][!] Błąd pakowania: {e}[/bold red]")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()