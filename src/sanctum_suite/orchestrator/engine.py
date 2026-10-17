from sanctum_suite.core.models import RiskLevel
from sanctum_suite.core.database import AuditStorageEngine
from sanctum_suite.core.analytics import AnalyticsStoreEngine
from sanctum_suite.core.reporter import ComplianceReportGenerator
from sanctum_suite.modules.osint import SpectreOsintModule
from sanctum_suite.modules.shadow import ShadowAgentModule
from sanctum_suite.modules.ghost import GhostCommModule


class SanctumUnifiedOrchestrator:
    """Enterprise Orchestration Engine z rozbudowaną persystencją analityczną."""

    def __init__(self) -> None:
        self.osint = SpectreOsintModule()
        self.shadow = ShadowAgentModule()
        self.ghost = GhostCommModule()
        self.db = AuditStorageEngine()
        self.analytics = AnalyticsStoreEngine()
        self.reporter = ComplianceReportGenerator()

    def execute_full_resilience_audit(self, target_domain: str) -> dict:
        audit_id = f"SNC-{hash(target_domain) & 0xFFFF:04X}"

        # Faza 1: OSINT
        osint_res = self.osint.scan_target(target_domain)
        self.analytics.record_event(
            f"EVT-OSINT-{audit_id}", audit_id, target_domain, "SPECTRE-OSINT", 25.0, f"Discovered {osint_res['exposed_assets_count']} subdomains"
        )

        # Faza 2: AI Safety Red-Teaming
        shadow_res = self.shadow.evaluate_llm_endpoints(osint_res["subdomains"])
        vuln_count = len(shadow_res["vulnerabilities"])
        self.analytics.record_event(
            f"EVT-SHADOW-{audit_id}", audit_id, target_domain, "SHADOW-AGENT", vuln_count * 40.0, f"Found {vuln_count} AI vulnerabilities"
        )

        # Faza 3: Zero-Trust Alert Packaging
        envelope_hash = self.ghost.secure_alert_dispatch(shadow_res)

        score = min(100.0, vuln_count * 40.0 + 10.0)
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
            "shadow_summary": shadow_res,
        }

        # Generowanie raportu HTML
        report_path = self.reporter.generate_html_report(audit_summary, f"report_{audit_id}.html")
        audit_summary["report_path"] = report_path

        return audit_summary