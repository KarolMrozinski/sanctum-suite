from sanctum_suite.core.models import AuditContext, RiskLevel
from sanctum_suite.core.database import AuditStorageEngine
from sanctum_suite.modules.osint import SpectreOsintModule
from sanctum_suite.modules.shadow import ShadowAgentModule
from sanctum_suite.modules.ghost import GhostCommModule


class SanctumUnifiedOrchestrator:
    """Główny silnik spinający proces skanowania, red-teamingu i szyfrowania."""

    def __init__(self) -> None:
        self.osint = SpectreOsintModule()
        self.shadow = ShadowAgentModule()
        self.ghost = GhostCommModule()
        self.db = AuditStorageEngine()

    def execute_full_resilience_audit(self, target_domain: str) -> dict:
        # Faza 1: OSINT
        osint_res = self.osint.scan_target(target_domain)

        # Faza 2: AI Safety Red-Teaming
        shadow_res = self.shadow.evaluate_llm_endpoints(osint_res["subdomains"])

        # Faza 3: Zero-Trust Alert Packaging
        envelope_hash = self.ghost.secure_alert_dispatch(shadow_res)

        # Kalkulacja zbiorczego ryzyka
        score = min(100.0, len(shadow_res["vulnerabilities"]) * 40.0 + 10.0)
        risk = RiskLevel.HIGH if score > 50 else RiskLevel.LOW

        # Zapis do bazy danych
        audit_id = f"SNC-{hash(target_domain) & 0xFFFF:04X}"
        self.db.save_audit(audit_id, target_domain, score, risk.value)

        return {
            "audit_id": audit_id,
            "target": target_domain,
            "overall_score": score,
            "risk_level": risk.value,
            "envelope_hash": envelope_hash,
            "osint_summary": osint_res,
            "shadow_summary": shadow_res,
        }