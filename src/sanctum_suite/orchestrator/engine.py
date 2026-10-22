import os
import asyncio
import uuid

import httpx

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
from sanctum_suite.core.github_integration import GitHubAutomatedPRPublisher
from sanctum_suite.core.rbac import RBACPermissionManager, UserRole
from sanctum_suite.core.compliance import RegulatoryComplianceEngine
from sanctum_suite.core.attack_graph import AttackGraphEngine
from sanctum_suite.core.task_queue import AsyncTaskQueueManager
from sanctum_suite.core.container_scanner import DockerContainerCVEAnalyzer
from sanctum_suite.core.billing import CommercialLicenseManager
from sanctum_suite.core.target_authorization import require_authorized_target
from sanctum_suite.core.tenant_manager import TenantProvisioningManager
from sanctum_suite.core.soar_agents import AutonomousSOARAgent
from sanctum_suite.core.kms_vault import ZeroTrustKMSVault
from sanctum_suite.core.deobfuscator import PayloadDeobfuscatorEngine
from sanctum_suite.core.plugin_fuzzer import AgentToolPluginFuzzer
from sanctum_suite.core.xdr_sync import EDRTelemetrySyncEngine
from sanctum_suite.core.gan_mutator import GANMutatorEngine
from sanctum_suite.core.k8s_operator import K8sCiliumOperator
from sanctum_suite.core.dlp_shield import DLPShieldEngine
from sanctum_suite.core.parrot_engine import ParrotSecEngine
from sanctum_suite.core.anonsurf_proxy import AnonSurfProxyModule
from sanctum_suite.core.parrot_forensics import ParrotForensicsEngine
from sanctum_suite.core.parrot_containers import ParrotContainerOrchestrator
from sanctum_suite.core.nist_compliance import NistComplianceEngine
from sanctum_suite.core.gpu_probe import GPUMemorySecurityProbe
from sanctum_suite.core.owasp_llm import OWASPLLMComplianceEngine
from sanctum_suite.core.llm04_resource_probe import LLMResourceExhaustionProbe
from sanctum_suite.core.parrot_owasp_reporter import ParrotOwaspReporter
from sanctum_suite.core.threat_actors import SovereignThreatActorEngine
from sanctum_suite.core.global_regulatory import GlobalRegulatoryEngine
from sanctum_suite.core.lowlevel_resilience import LowLevelResilienceEngine
from sanctum_suite.core.exploit_lab import ExploitLabEngine
from sanctum_suite.core.cyber_plumber import CyberPlumberNetworkEngine
from sanctum_suite.core.spider_graph import SpiderGraphOsintEngine
from sanctum_suite.core.cilium_profiler import CiliumSecurityProfileEngine
from sanctum_suite.core.dora_iso_reporter import DoraIsoComplianceReporter
from sanctum_suite.core.l7_sanitizer_proxy import L7GuardrailSanitizerProxy
from sanctum_suite.core.polymorphic_fuzzer import PolymorphicFuzzingEngine
from sanctum_suite.core.deception_mesh import DeceptionMeshOrchestrator
from sanctum_suite.core.supply_chain_sbom import SupplyChainSbomAuditEngine
from sanctum_suite.core.xdr_correlator import RealtimeXdrMeshCorrelator
from sanctum_suite.core.trust_chain import SovereignTrustChainVerifier
from sanctum_suite.core.bas_simulator import ContinuousBasSimulator
from sanctum_suite.core.industrial_scada import IndustrialScadaTelemetryAuditor
from sanctum_suite.core.binary_reversing import ProjectZeroBinaryReversingEngine
from sanctum_suite.core.opsec_auditor import OpSecFootprintAuditor
from sanctum_suite.core.ebpf_enforcement import EbpfInKernelEnforcementEngine
from sanctum_suite.core.autonomous_red_team import AutonomousAgentRedTeamEngine
from sanctum_suite.core.post_quantum_pqc import PostQuantumCryptographicAssuranceEngine
from sanctum_suite.modules.osint import SpectreOsintModule
from sanctum_suite.modules.shadow import ShadowAgentModule
from sanctum_suite.modules.ghost import GhostCommModule
from sanctum_suite.modules.multi_turn_fuzzer import MultiTurnJailbreakFuzzer
from sanctum_suite.modules.multimodal_fuzzer import MultimodalSafetyFuzzer
from sanctum_suite.core.airgap_diode import AirGapDataDiodeBroker
from sanctum_suite.core.diamond_model import DiamondModelThreatTracker
from sanctum_suite.core.nist_sp800_53 import NistSp80053ControlAssurance
from sanctum_suite.core.purple_team import PurpleTeamEmulationCoordinator
from sanctum_suite.core.tempest_auditor import TempestSdip27EmissionsAuditor
from sanctum_suite.core.threat_intel import SovereignThreatIntelAggregator
from sanctum_suite.core.zero_trust_mesh import ZeroTrustMeshProtocolEngine
from sanctum_suite.core.self_healing import SelfHealingBinaryEngine
from sanctum_suite.core.vram_guard import VramEnclaveGuardEngine
from sanctum_suite.core.darknet_apt_shield import DarknetAptShieldEngine
from sanctum_suite.core.cloud_infrastructure import CloudInfrastructureManager
from sanctum_suite.core.was_security import WASModule

class SanctumUnifiedOrchestrator:
    """Sovereign Enterprise Orchestration Engine z eBPF In-Kernel Enforcement, Autonomous Red-Team i PQC Assurance."""

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
        self.github_pr = GitHubAutomatedPRPublisher()
        self.rbac = RBACPermissionManager()
        self.multi_turn_fuzzer = MultiTurnJailbreakFuzzer()
        self.multimodal_fuzzer = MultimodalSafetyFuzzer()
        self.compliance_engine = RegulatoryComplianceEngine()
        self.attack_graph_engine = AttackGraphEngine()
        self.task_queue = AsyncTaskQueueManager()
        self.container_scanner = DockerContainerCVEAnalyzer()
        self.license_manager = CommercialLicenseManager()
        self.tenant_manager = TenantProvisioningManager()
        self.soar_agent = AutonomousSOARAgent()
        self.kms_vault = ZeroTrustKMSVault()
        self.deobfuscator = PayloadDeobfuscatorEngine()
        self.plugin_fuzzer = AgentToolPluginFuzzer()
        self.xdr_sync = EDRTelemetrySyncEngine()
        self.gan_mutator = GANMutatorEngine()
        self.k8s_operator = K8sCiliumOperator()
        self.dlp_shield = DLPShieldEngine()
        self.parrot_engine = ParrotSecEngine()
        self.anonsurf = AnonSurfProxyModule()
        self.forensics = ParrotForensicsEngine()
        self.parrot_containers = ParrotContainerOrchestrator()
        self.nist_engine = NistComplianceEngine()
        self.gpu_probe = GPUMemorySecurityProbe()
        self.owasp_engine = OWASPLLMComplianceEngine()
        self.resource_probe = LLMResourceExhaustionProbe()
        self.parrot_owasp_reporter = ParrotOwaspReporter()
        self.threat_actors = SovereignThreatActorEngine()
        self.global_regulatory = GlobalRegulatoryEngine()
        self.lowlevel_resilience = LowLevelResilienceEngine()
        self.exploit_lab = ExploitLabEngine()
        self.cyber_plumber = CyberPlumberNetworkEngine()
        self.spider_graph = SpiderGraphOsintEngine()
        self.cilium_profiler = CiliumSecurityProfileEngine()
        self.dora_iso_reporter = DoraIsoComplianceReporter()
        self.l7_sanitizer = L7GuardrailSanitizerProxy()
        self.polymorphic_fuzzer = PolymorphicFuzzingEngine()
        self.deception_mesh = DeceptionMeshOrchestrator()
        self.supply_chain_sbom = SupplyChainSbomAuditEngine()
        self.xdr_correlator = RealtimeXdrMeshCorrelator()
        self.trust_chain = SovereignTrustChainVerifier()
        self.bas_simulator = ContinuousBasSimulator()
        self.scada_auditor = IndustrialScadaTelemetryAuditor()
        self.binary_reversing = ProjectZeroBinaryReversingEngine()
        self.opsec_auditor = OpSecFootprintAuditor()
        self.ebpf_kernel_shield = EbpfInKernelEnforcementEngine()
        self.autonomous_red_team = AutonomousAgentRedTeamEngine()
        self.pqc_assurance = PostQuantumCryptographicAssuranceEngine()
        self.airgap_diode = AirGapDataDiodeBroker()
        self.diamond_tracker = DiamondModelThreatTracker()
        self.nist_800_53 = NistSp80053ControlAssurance()
        self.purple_team = PurpleTeamEmulationCoordinator()
        self.tempest_auditor = TempestSdip27EmissionsAuditor()
        self.threat_intel = SovereignThreatIntelAggregator()
        self.zt_mesh = ZeroTrustMeshProtocolEngine()
        self.self_healing = SelfHealingBinaryEngine()
        self.vram_guard = VramEnclaveGuardEngine()
        self.darknet_shield = DarknetAptShieldEngine()
        self.cloud_infrastructure = CloudInfrastructureManager()
        self.was_security = WASModule()

    def execute_full_resilience_audit(
        self,
        target_domain: str,
        role: UserRole = UserRole.ADMIN,
        license_key: str | None = None,
        tenant_id: str | None = None,
        authorization_reference: str | None = None,
    ) -> dict:
        self.rbac.verify_permission(role, "RUN_AUDIT")

        target_domain = require_authorized_target(target_domain, authorization_reference)
        verified_authorization_reference = (authorization_reference or "").strip()
        lic_info = self.license_manager.validate_license_key(
            license_key or os.environ.get("SANCTUM_LICENSE_KEY")
        )
        if tenant_id is not None and tenant_id != lic_info["tenant_id"]:
            raise PermissionError("Requested tenant does not match the signed license")
        tenant_id = lic_info["tenant_id"]
        self.license_manager.check_and_increment_usage(tenant_id, lic_info, "audits")

        audit_id = f"SNC-{uuid.uuid4().hex[:12].upper()}"

        # Wykonanie silników w kernelu eBPF, Autonomous Red-Team oraz PQC
        kernel_shield = self.ebpf_kernel_shield.enforce_kernel_shield("strict_syscall_lsm")
        autonomous_rt = self.autonomous_red_team.execute_autonomous_campaign(target_domain)
        pqc_audit = self.pqc_assurance.audit_cryptographic_primitives()

        # Wykonanie audytów SCADA, Binary Reversing oraz OpSec
        scada_audit = self.scada_auditor.audit_industrial_protocols(target_domain)
        binary_audit = self.binary_reversing.analyze_firmware_binary("firmware_sample.bin")
        opsec_audit = self.opsec_auditor.evaluate_operational_footprint(target_domain)

        # Weryfikacja łańcucha zaufania i inicjalizacja XDR/BAS
        trust_check = self.trust_chain.verify_module_integrity("SanctumOrchestratorCore", b"sanctum_core_binary_v1")
        xdr_stream = self.xdr_correlator.ingest_telemetry_stream([{"source": "eBPF", "event": "syscall_audit"}])
        bas_sim = self.bas_simulator.execute_lateral_movement_simulation("inference-cluster")

        # Inicjalizacja komponentów ochronnych i sieci pułapek
        sanitized_input = self.l7_sanitizer.sanitize_input_payload(target_domain)
        canary_mesh = self.deception_mesh.deploy_canary_mesh("cluster-edge")
        poly_payload = self.polymorphic_fuzzer.generate_polymorphic_payload("ignore previous instructions")
        sbom_audit = self.supply_chain_sbom.audit_software_bill_of_materials("sbom.json")

        # Placeholder integrations: the Parrot container adapter only returns a non-executing plan.
        plumber_tunnel = self.cyber_plumber.establish_multihop_tunnel("entry-node.proxy", "exit-node.proxy")
        parrot_container = self.parrot_containers.spawn_parrot_microcontainer("DEEP_SCAN")
        anonsurf_status = self.anonsurf.enable_anonsurf_tunnel()

        # Faza 1: OSINT, Port, Container, GPU, Kernel Exploit Lab & Cilium eBPF Profiling
        osint_res = self.osint.scan_target(target_domain)
        probe_results = self.async_scanner.run_sync_batch_scan(
            [target_domain],
            authorization_reference=verified_authorization_reference,
        )
        open_ports = self.port_scanner.run_sync_port_scan(
            target_domain,
            authorization_reference=verified_authorization_reference,
        )
        container_scan = self.container_scanner.inspect_container_image()
        gpu_scan = self.gpu_probe.inspect_gpu_runtime()
        llm04_probe = self.resource_probe.test_context_exhaustion(target_domain)
        parrot_scan = self.parrot_engine.run_recon_audit(target_domain)
        lowlevel_res = self.lowlevel_resilience.execute_low_level_audit(target_domain)
        kernel_exploit_audit = self.exploit_lab.inspect_kernel_mitigations()
        spider_graph_res = self.spider_graph.build_infrastructure_graph(target_domain)
        cilium_profile = self.cilium_profiler.generate_least_privilege_policy("llm-service")

        # Faza 2: AI Safety, Mutator, Agent Tool Fuzzing & Sovereign Threat Actor Emulation
        shadow_res = self.shadow.evaluate_llm_endpoints(osint_res["subdomains"])
        multi_turn_res = self.multi_turn_fuzzer.execute_multi_turn_fuzzing(target_domain)
        multimodal_res = self.multimodal_fuzzer.evaluate_visual_prompts(target_domain)
        plugin_fuzz_res = self.plugin_fuzzer.evaluate_agent_tools(target_domain)
        deobfuscation_res = self.deobfuscator.analyze_payload("aWdub3JlIHByZXZpb3Vz insRydWN0aW9ucw==")
        gan_mutations = self.gan_mutator.generate_mutations("ignore previous instructions")
        apt_simulation = self.threat_actors.simulate_threat_actor_ttps(target_domain, "EQUATION_GROUP")

        # Faza 3: DLP, Forensics, DORA/ISO 42001 Certification & OWASP LLM
        honeytoken_info = self.dlp_shield.inject_synthetic_honeytoken("AWS_KEY")
        dlp_inspection = self.dlp_shield.inspect_output_for_exfiltration("Safe output without leak.")
        forensics_analysis = self.forensics.analyze_memory_dump("mem_sample.raw")
        nist_evaluation = self.nist_engine.evaluate_frameworks(shadow_res["vulnerabilities"])
        owasp_evaluation = self.owasp_engine.evaluate_owasp_top10(shadow_res["vulnerabilities"])
        global_compliance = self.global_regulatory.evaluate_global_compliance(shadow_res["vulnerabilities"])
        dora_iso_scorecard = self.dora_iso_reporter.generate_audit_scorecard(shadow_res["vulnerabilities"])
        scorecard = self.parrot_owasp_reporter.generate_compliance_scorecard(owasp_evaluation, nist_evaluation)

        # Faza 4: Threat Correlation, Attack Graph & EDR Sync
        correlation = self.correlator.correlate_findings(open_ports, shadow_res["vulnerabilities"])
        mitre_tactics = self.mitre.map_findings(shadow_res["vulnerabilities"], open_ports)
        playbook = self.remediation.generate_playbook(open_ports, shadow_res["vulnerabilities"])
        auto_patch = self.auto_patcher.generate_remediation_patch(shadow_res["vulnerabilities"])
        compliance_eval = self.compliance_engine.evaluate_compliance(shadow_res["vulnerabilities"], open_ports)
        attack_graph = self.attack_graph_engine.build_attack_graph(target_domain, open_ports, shadow_res["vulnerabilities"])
        edr_telemetry = self.xdr_sync.sync_endpoint_telemetry(audit_id)
        k8s_isolation = self.k8s_operator.enforce_pod_quarantine("llm-inference-pod")

        # Faza 5: Zero-Trust Alert Packaging & Envelope Encryption
        envelope_hash = self.ghost.secure_alert_dispatch(shadow_res)
        encrypted_kms_payload = self.kms_vault.encrypt_payload(str(shadow_res))

        base_score = min(100.0, len(shadow_res["vulnerabilities"]) * 40.0 + len(open_ports) * 10.0 + 10.0)
        final_score = min(100.0, base_score * correlation["risk_multiplier"])
        risk = RiskLevel.HIGH if final_score > 50 else RiskLevel.LOW

        cef_log = self.siem.format_cef_event(audit_id, target_domain, final_score, risk.value)
        sigma_rule = self.rules_gen.generate_sigma_rule(audit_id, target_domain, shadow_res["vulnerabilities"])
        yara_rule = self.rules_gen.generate_yara_rule(audit_id)

        airgap_transfer = self.airgap_diode.enforce_unidirectional_transfer("telemetry_payload", "secure_enclave_alpha")
        diamond_event = self.diamond_tracker.build_diamond_event("APT29_COZY_BEAR", "Custom eBPF Injection", "inference-cluster")
        nist_controls = self.nist_800_53.audit_security_controls()
        aws_baseline = self.cloud_infrastructure.assess_cloud_infrastructure("aws", region="eu-central-1", workload="sanctum-suite")
        azure_baseline = self.cloud_infrastructure.assess_cloud_infrastructure("azure", region="westeurope", workload="sanctum-suite")
        was_assessment = self.was_security.assess_web_application("api.sanctum-suite.local", "sanctum-api")
        defense_in_depth = self.was_security.assess_web_application("portal.sanctum-suite.local", "sanctum-portal")

        purple_sync = self.purple_team.coordinate_emulation_cycle("APT29 Credential Access", "Sigma-Rule-9941")
        tempest_audit = self.tempest_auditor.audit_enclave_emissions("Enclave-Alpha-Room")
        threat_intel_sync = self.threat_intel.aggregate_threat_feeds()

        zt_mesh_link = self.zt_mesh.establish_secure_mesh_link("enclave-alpha", "enclave-beta")
        self_healing_res = self.self_healing.evaluate_and_patch_memory_anomaly("inference-cluster-pid")
        vram_guard_res = self.vram_guard.secure_gpu_memory_space("NVIDIA_RTX_4070_TI")

        darknet_audit_res = self.darknet_shield.scan_for_apt_anomalies("MEM-HASH-SECURE-99X")

        audit_summary = {
            "audit_id": audit_id,
            "target": target_domain,
            "authorization_reference": verified_authorization_reference,
            "tenant_id": tenant_id,
            "license_tier": lic_info["tier"].value,
            "overall_score": final_score,
            "risk_level": risk.value,
            "kernel_shield": kernel_shield,
            "autonomous_red_team": autonomous_rt,
            "pqc_audit": pqc_audit,
            "scada_audit": scada_audit,
            "binary_audit": binary_audit,
            "opsec_audit": opsec_audit,
            "trust_check": trust_check,
            "xdr_stream": xdr_stream,
            "bas_simulation": bas_sim,
            "sanitized_input": sanitized_input,
            "canary_mesh": canary_mesh,
            "polymorphic_payload": poly_payload,
            "sbom_audit": sbom_audit,
            "plumber_tunnel": plumber_tunnel,
            "anonsurf_tunnel": anonsurf_status,
            "parrot_container": parrot_container,
            "envelope_hash": envelope_hash,
            "kms_envelope": encrypted_kms_payload,
            "osint_summary": osint_res,
            "spider_graph": spider_graph_res,
            "probed_endpoints": probe_results,
            "open_ports": open_ports,
            "container_scan": container_scan,
            "gpu_scan": gpu_scan,
            "llm04_probe": llm04_probe,
            "parrot_scan": parrot_scan,
            "lowlevel_resilience": lowlevel_res,
            "kernel_exploit_audit": kernel_exploit_audit,
            "cilium_profile": cilium_profile,
            "shadow_summary": shadow_res,
            "multi_turn_summary": multi_turn_res,
            "multimodal_summary": multimodal_res,
            "agent_plugin_summary": plugin_fuzz_res,
            "deobfuscation_analysis": deobfuscation_res,
            "gan_mutations": gan_mutations,
            "apt_simulation": apt_simulation,
            "honeytoken_injected": honeytoken_info,
            "dlp_inspection": dlp_inspection,
            "forensics_analysis": forensics_analysis,
            "nist_evaluation": nist_evaluation,
            "owasp_evaluation": owasp_evaluation,
            "global_compliance": global_compliance,
            "dora_iso_scorecard": dora_iso_scorecard,
            "compliance_scorecard": scorecard,
            "edr_telemetry": edr_telemetry,
            "k8s_isolation": k8s_isolation,
            "correlation": correlation,
            "mitre_tactics": mitre_tactics,
            "compliance_evaluation": compliance_eval,
            "attack_graph": attack_graph,
            "playbook": playbook,
            "auto_patch": auto_patch,
            "cef_log": cef_log,
            "detection_rules": {"sigma": sigma_rule, "yara": yara_rule},
            "airgap_transfer": airgap_transfer,
            "diamond_event": diamond_event,
            "nist_controls": nist_controls,
            "cloud_infrastructure": {
                "aws": aws_baseline,
                "azure": azure_baseline,
            },
            "web_application_security": {
                "was": was_assessment,
                "defense_in_depth": defense_in_depth,
            },
            "purple_sync": purple_sync,
            "tempest_audit": tempest_audit,
            "threat_intel_sync": threat_intel_sync,
            "zt_mesh_link": zt_mesh_link,
            "self_healing_res": self_healing_res,
            "vram_guard_res": vram_guard_res,
            "darknet_apt_shield": darknet_audit_res,
        }

        # Faza 6: SOAR Agent & Cleanup
        soar_actions = self.soar_agent.evaluate_and_remediate(audit_summary)
        audit_summary["soar_actions"] = soar_actions

        self.cyber_plumber.teardown_tunnel(plumber_tunnel["tunnel_id"])
        self.parrot_containers.terminate_container(parrot_container["container_id"])
        self.anonsurf.disable_anonsurf_tunnel()

        # Zapis w bazie i raporty
        self.db.save_audit(
            audit_id,
            target_domain,
            final_score,
            risk.value,
            authorization_reference=verified_authorization_reference,
        )

        webhook_delivery = {"status": "NOT_CONFIGURED", "dispatched": False}
        if self.siem.webhook_url:
            try:
                asyncio.run(
                    self.siem.dispatch_webhook_alert(
                        {"audit_id": audit_id, "cef": cef_log}
                    )
                )
            except httpx.HTTPError as error:
                webhook_delivery = {
                    "status": "DELIVERY_FAILED",
                    "dispatched": False,
                    "error_type": type(error).__name__,
                }
            else:
                webhook_delivery = {"status": "DELIVERED", "dispatched": True}
        audit_summary["siem_webhook_delivery"] = webhook_delivery

        report_path_html = self.reporter.generate_html_report(audit_summary, f"report_{audit_id}.html")
        report_path_pdf = self.pdf_reporter.generate_pdf_report(audit_summary, f"report_{audit_id}.pdf")
        pdf_signature = self.signer.sign_file(report_path_pdf)

        audit_summary["report_path_html"] = report_path_html
        audit_summary["report_path_pdf"] = report_path_pdf
        audit_summary["pdf_signature"] = pdf_signature

        return audit_summary