from sanctum_suite.core.models import RiskLevel
from sanctum_suite.core.database import AuditStorageEngine
from sanctum_suite.core.analytics import AnalyticsStoreEngine
from sanctum_suite.core.reporter import ComplianceReportGenerator
from sanctum_suite.core.scanner import AsyncEndpointScanner
from sanctum_suite.core.port_scanner import AsyncPortScanner
from sanctum_suite.modules.osint import SpectreOsintModule
from sanctum_suite.modules.shadow import ShadowAgentModule
from sanctum_suite.modules.ghost import GhostCommModule


class SanctumUnifiedOrchestrator:
    """Enterprise Orchestration Engine z asynchronicznym skanerem punktów i portów."""

    def __init__(self) -> None:
        self.osint = SpectreOsintModule()
        self.shadow = ShadowAgentModule()
        self.ghost = GhostCommModule()
        self.db = AuditStorageEngine()
        self.analytics = AnalyticsStoreEngine()
        self.reporter = ComplianceReportGenerator()
        self.async_scanner = AsyncEndpointScanner()
        self.port_scanner = AsyncPortScanner()

    def execute_full_resilience_audit(self, target_domain: str) -> dict:
        audit_id = f"SNC-{hash(target_domain) & 0xFFFF:04X}"

        # Faza 1: OSINT & Network Probing
        osint_res = self.osint.scan_target(target_domain)
        probe_results = self.async_scanner.run_sync_batch_scan(osint_res["subdomains"])
        
        # Skanowanie otwartych portów na domenie głównej
        open_ports = self.port_scanner.run_sync_port_scan("127.0.0.1")  # Skanowanie środowiska lokalnego / mock targetu

        self.analytics.record_event(
            f"EVT-OSINT-{audit_id}",
            audit_id,
            target_domain,
            "SPECTRE-OSINT",
            25.0,
            f"Probed {len(probe_results)} subdomains, found {len(open_ports)} open ports",
        )

        # Faza 2: AI Safety Red-Teaming
        shadow_res = self.shadow.evaluate_llm_endpoints(osint_res["subdomains"])
        vuln_count = len(shadow_res["vulnerabilities"])
        self.analytics.record_event(
            f"EVT-SHADOW-{audit_id}",
            audit_id,
            target_domain,
            "SHADOW-AGENT",
            vuln_count * 40.0,
            f"Found {vuln_count} AI vulnerabilities",
        )

        # Faza 3: Zero-Trust Alert Packaging
        envelope_hash = self.ghost.secure_alert_dispatch(shadow_res)

        score = min(100.0, vuln_count * 40.0 + len(open_ports) * 10.0 + 10.0)
        risk = RiskLevel.HIGH if score > 50 else RiskLevel.LOW

        # Zapis w bazach SQLite i DuckDB
        self.db.save_audit(audit_id, target_domain, score, risk.value)

        audit_summary = {
            "audit_id": audit_id,
            "target": target_domain,
            "overall_score": score,
            "risk_level": risk.value,
            "envelope_hash": envelope_hash,
            "osint_summary": osint_res,
            "probed_endpoints": probe_results,
            "open_ports": open_ports,
            "shadow_summary": shadow_res,
        }

        # Generowanie raportu HTML
        report_path = self.reporter.generate_html_report(audit_summary, f"report_{audit_id}.html")
        audit_summary["report_path"] = report_path

        return audit_summary