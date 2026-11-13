#!/usr/bin/env python3

import os
import pytest
from pathlib import Path

from sanctum_suite.core.crypto_lifecycle import CryptoLifecycleManager
from sanctum_suite.core.network_policy import NetworkPolicyGuard
from sanctum_suite.core.db_maintenance import DatabaseMaintenanceGuard
from sanctum_suite.core.detection_generator import AutomatedDetectionRuleGenerator
from sanctum_suite.core.purple_team_orchestrator import AdvancedPurpleTeamOrchestrator
from sanctum_suite.core.xdr_correlation_engine import AdvancedXDRCorrelationEngine
from sanctum_suite.core.rbac_policy_auditor import RBACPolicyAuditor
from sanctum_suite.core.audit_chain_auditor import ImmutableAuditChainAuditor
from sanctum_suite.core.artifact_supply_guard import ArtifactSupplyGuard
from sanctum_suite.core.exfiltration_guard import AdvancedExfiltrationGuard
from sanctum_suite.core.hardware_security_validator import HardwareSecurityValidator
from sanctum_suite.core.emergency_sanitization import EmergencySanitizationGuard
from sanctum_suite.core.ipc_bus import SecureIPCBus
from sanctum_suite.core.telemetry_buffer import TelemetryBuffer
from sanctum_suite.core.agent_orchestrator import AutonomousAgentOrchestrator

def test_advanced_ecosystem_and_agents_integration(tmp_path: Path):
    keys_dir = tmp_path / "keys"
    rules_dir = tmp_path / "rules"
    telemetry_dir = tmp_path / "telemetry"
    ipc_dir = tmp_path / "ipc"
    workspace_dir = tmp_path / "workspace"

    # 1. Crypto Lifecycle
    crypto_mgr = CryptoLifecycleManager(keys_dir=keys_dir)
    assert crypto_mgr.keys_dir == keys_dir

    # 2. Network Policy Guard
    net_guard = NetworkPolicyGuard(air_gapped_enforced=True)
    sockets_audit = net_guard.audit_active_sockets()
    assert isinstance(sockets_audit, list)

    # 3. Detection Generator
    det_gen = AutomatedDetectionRuleGenerator(rules_output_dir=rules_dir)
    yara_content = det_gen.generate_yara_rule_content("ADV_TEST_APT", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
    assert "Sanctum_APT_ADV_TEST_APT" in yara_content

    # 4. Telemetry Buffer & Ingestion
    telemetry_buf = TelemetryBuffer(buffer_dir=telemetry_dir, max_buffer_size=2)
    event_rec = telemetry_buf.push_event("ADV_TEST_EVENT", {"status": "ok"})
    assert "record_hash" in event_rec
    assert telemetry_buf.get_buffered_count() == 1

    # 5. Secure IPC Bus
    ipc_bus = SecureIPCBus(ipc_socket_dir=ipc_dir)
    msg_res = ipc_bus.dispatch_encrypted_message("advanced_alerts", "test_sender", {"alert": "critical"})
    assert msg_res["status"] == "delivered"

    # 6. Autonomous Agent Orchestrator
    orchestrator = AutonomousAgentOrchestrator(workspace_dir=workspace_dir)
    cycle_report = orchestrator.run_autonomous_cycle({"high_severity_incidents_found": 0, "flagged_anomalies_count": 0})
    assert cycle_report["system_status"] == "stable"

    # 7. Emergency Sanitization Check
    sanitization = EmergencySanitizationGuard(target_secure_dir=tmp_path / "secure_zone")
    sanit_res = sanitization.execute_total_sanitization_protocol(authorization_valid=True)
    assert sanit_res["sanitization_executed"] is False