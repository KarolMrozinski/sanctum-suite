from sanctum_suite.core.models import RiskLevel
from sanctum_suite.core.database import AuditStorageEngine
from sanctum_suite.core.analytics import AnalyticsStoreEngine
from sanctum_suite.core.reporter import ComplianceReportGenerator
from sanctum_suite.core.pdf_reporter import PDFReportGenerator
from sanctum_suite.core.correlator import ThreatCorrelationEngine
from sanctum_suite.core.scanner import AsyncEndpointScanner
from sanctum_suite.core.port_scanner import AsyncPortScanner
from sanctum_suite.core.signer import SecurityReportSigner
from sanctum_suite.core.mitre import MitreMapperEngine
from sanctum_suite.core.remediation import RemediationPlaybookEngine
from sanctum_suite.core.proxy import LLMGuardrailProxy
from sanctum_suite.core.siem import SIEMIntegrationExporter
from sanctum_suite.core.honeypot import DecoyHoneypotSensor
from sanctum_suite.core.sigma_yara import DetectionRuleGenerator
from sanctum_suite.core.anomaly import MLAnomalyDetector
from sanctum_suite.core.event_bus import DistributedEventBus
from sanctum_suite.core.auto_patcher import AutomatedPatchEngine
from sanctum_suite.modules.osint import SpectreOsintModule
from sanctum_suite.modules.shadow import ShadowAgentModule
from sanctum_suite.modules.ghost import GhostCommModule
from sanctum_suite.modules.multi_turn_fuzzer import MultiTurnJailbreakFuzzer


class SanctumUnifiedOrchestrator:
    """Enterprise Orchestration Engine z Multi-Turn Fuzzerem, Event Busem i Auto-Patcherem."""

    def __init__(self) -> None:
        self.osint = SpectreOsintModule()
        self.shadow = ShadowAgentModule()
        self.ghost = GhostCommModule()
        self.db = AuditStorageEngine()
        self.analytics = AnalyticsStoreEngine()
        self.reporter = ComplianceReportGenerator()
        self.pdf_reporter = PDFReportGenerator()
        self.correlator = ThreatCorrelationEngine()
        self.async_scanner = AsyncEndpointScanner()
        self.port_scanner = AsyncPortScanner()
        self.signer = SecurityReportSigner()
        self.mitre = MitreMapperEngine()
        self.remediation = RemediationPlaybookEngine()
        self.guardrail = LLMGuardrailProxy()
        self.siem = SIEMIntegrationExporter()
        self.honeypot = DecoyHoneypotSensor()
        self.rules_gen = DetectionRuleGenerator()
        self.anomaly_detector = MLAnomalyDetector()
        self.event_bus = DistributedEventBus()
        self.auto_patcher = AutomatedPatchEngine()
        self.multi_turn_fuzzer = MultiTurnJailbreakFuzzer()

    def execute_full_resilience_audit(self, target_domain: str) -> dict:
        audit_id = f"SNC-{hash(target_domain) & 0xFFFF:04X}"

        # Faza 1: OSINT & Network Probing
        osint_res = self.osint.scan_target(target_domain)
        probe_results = self.async_scanner.run_sync_batch_scan(osint_res["subdomains"])
        open_ports = self.port_scanner.run_sync_port_scan("127.0.0.1")

        # Faza 2: AI Safety Red-Teaming & Multi-Turn Fuzzing
        shadow_res = self.shadow.evaluate_llm_endpoints(osint_res["subdomains"])
        multi_turn_res = self.multi_turn_fuzzer.execute_multi_turn_fuzzing(target_domain)
        
        # Faza 3: Threat Correlation, MITRE Mapping & Auto-Patching
        correlation = self.correlator.correlate_findings(open_ports, shadow_res["vulnerabilities"])
        mitre_tactics = self.mitre.map_findings(shadow_res["vulnerabilities"], open_ports)
        playbook = self.remediation.generate_playbook(open_ports, shadow_res["vulnerabilities"])
        auto_patch = self.auto_patcher.generate_remediation_patch(shadow_res["vulnerabilities"])

        # Faza 4: Zero-Trust Alert Packaging & SIEM Format
        envelope_hash = self.ghost.secure_alert_dispatch(shadow_res)

        base_score = min(100.0, len(shadow_res["vulnerabilities"]) * 40.0 + len(open_ports) * 10.0 + 10.0)
        final_score = min(100.0, base_score * correlation["risk_multiplier"])
        risk = RiskLevel.HIGH if final_score > 50 else RiskLevel.LOW

        cef_log = self.siem.format_cef_event(audit_id, target_domain, final_score, risk.value)
        sigma_rule = self.rules_gen.generate_sigma_rule(audit_id, target_domain, shadow_res["vulnerabilities"])
        yara_rule = self.rules_gen.generate_yara_rule(audit_id)

        # Zapis w bazach danych
        self.db.save_audit(audit_id, target_domain, final_score, risk.value)

        audit_summary = {
            "audit_id": audit_id,
            "target": target_domain,
            "overall_score": final_score,
            "risk_level": risk.value,
            "envelope_hash": envelope_hash,
            "osint_summary": osint_res,
            "probed_endpoints": probe_results,
            "open_ports": open_ports,
            "shadow_summary": shadow_res,
            "multi_turn_summary": multi_turn_res,
            "correlation": correlation,
            "mitre_tactics": mitre_tactics,
            "playbook": playbook,
            "auto_patch": auto_patch,
            "cef_log": cef_log,
            "detection_rules": {
                "sigma": sigma_rule,
                "yara": yara_rule,
            },
        }

        # Generowanie raportów
        report_path_html = self.reporter.generate_html_report(audit_summary, f"report_{audit_id}.html")
        report_path_pdf = self.pdf_reporter.generate_pdf_report(audit_summary, f"report_{audit_id}.pdf")

        # Kryptograficzne podpisanie pliku PDF
        pdf_signature = self.signer.sign_file(report_path_pdf)

        audit_summary["report_path_html"] = report_path_html
        audit_summary["report_path_pdf"] = report_path_pdf
        audit_summary["pdf_signature"] = pdf_signature

        return audit_summary