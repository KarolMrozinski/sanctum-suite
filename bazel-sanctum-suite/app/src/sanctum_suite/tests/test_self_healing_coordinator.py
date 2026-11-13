import json

import pytest
from typer.testing import CliRunner

from sanctum_suite import main
from sanctum_suite.core.self_healing_coordinator import (
    AutonomousSelfHealingCoordinator,
    SelfHealingApprovalError,
    tee_model_capabilities,
)


def test_self_healing_coordinator_does_not_claim_to_patch():
    coordinator = AutonomousSelfHealingCoordinator()
    res = coordinator.trigger_autonomous_hot_patch("core.quantum_ram_vault")
    
    assert res["status"] == "NOT_IMPLEMENTED"
    assert res["hot_patch_applied"] is False
    assert res["isolation_performed"] is False
    assert res["system_recovery_status"] == "NOT_ASSESSED"


def _propose(coordinator):
    return coordinator.propose_remediation(
        target_module="sanctum.api.authz",
        action="opa_policy_update",
        reason_code="anomaly_detected",
        evidence_sha256="a" * 64,
        current_policy_version="policy-v1",
        proposed_change_sha256="b" * 64,
        created_by="monitor-agent",
    )


def test_self_healing_records_proposals_and_requires_distinct_operator_approval(
    tmp_path,
):
    database = tmp_path / "remediation.sqlite"
    coordinator = AutonomousSelfHealingCoordinator(database)
    proposal = _propose(coordinator)

    assert proposal["status"] == "APPROVAL_REQUIRED"
    assert proposal["change_applied"] is False
    with pytest.raises(SelfHealingApprovalError, match="cannot approve their own"):
        coordinator.decide_proposal(
            proposal_id=proposal["proposal_id"],
            approver_id="monitor-agent",
            approved=True,
        )

    decision = coordinator.decide_proposal(
        proposal_id=proposal["proposal_id"],
        approver_id="security-operator",
        approved=True,
    )
    assert decision["status"] == "APPROVED_PENDING_MANUAL_DEPLOYMENT"
    assert decision["change_applied"] is False
    listed = AutonomousSelfHealingCoordinator(database).list_proposals()
    assert listed[0]["status"] == "APPROVED"
    assert listed[0]["proposed_change_sha256"] == "b" * 64
    with pytest.raises(SelfHealingApprovalError, match="already has a decision"):
        coordinator.decide_proposal(
            proposal_id=proposal["proposal_id"],
            approver_id="second-operator",
            approved=False,
        )


def test_self_healing_rejects_invalid_proposals_and_tampered_journal(tmp_path):
    database = tmp_path / "remediation.sqlite"
    coordinator = AutonomousSelfHealingCoordinator(database)
    with pytest.raises(SelfHealingApprovalError, match="must be SHA-256"):
        coordinator.propose_remediation(
            target_module="sanctum.api.authz",
            action="key_rotation",
            reason_code="rotation_due",
            evidence_sha256="not-a-digest",
            current_policy_version="policy-v1",
            proposed_change_sha256="b" * 64,
            created_by="monitor-agent",
        )
    proposal = _propose(coordinator)
    import sqlite3

    with sqlite3.connect(database) as connection:
        connection.execute("DROP TRIGGER self_healing_events_no_update")
        connection.execute(
            "UPDATE self_healing_events SET event_json = ?",
            ('{"event_type":"proposal","proposal_id":"rewritten"}',),
        )
    with pytest.raises(SelfHealingApprovalError, match="hash chain is invalid"):
        coordinator.list_proposals()


def test_local_tee_model_is_not_claimed_as_configured():
    status = tee_model_capabilities()

    assert status["status"] == "NOT_CONFIGURED"
    assert "not generated" in status["limitations"]


def test_capabilities_and_approval_cli_report_non_autonomous_status(tmp_path):
    capabilities = CliRunner().invoke(main.app, ["security-capabilities"])
    assert capabilities.exit_code == 0, capabilities.output
    capability_report = json.loads(capabilities.stdout)
    assert capability_report["qkd"]["status"] == "NOT_CONFIGURED"
    assert capability_report["tee_local_model"]["status"] == "NOT_CONFIGURED"
    assert capability_report["self_healing"]["automatic_key_rotation"] is False

    database = tmp_path / "remediation.sqlite"
    proposal = CliRunner().invoke(
        main.app,
        [
            "self-healing-propose",
            "--database-file",
            str(database),
            "--target-module",
            "sanctum.api.authz",
            "--action",
            "key_rotation",
            "--reason-code",
            "scheduled_rotation",
            "--evidence-sha256",
            "a" * 64,
            "--current-policy-version",
            "policy-v1",
            "--proposed-change-sha256",
            "b" * 64,
            "--created-by",
            "monitor-agent",
        ],
    )
    assert proposal.exit_code == 0, proposal.output
    proposal_report = json.loads(proposal.stdout)
    decision = CliRunner().invoke(
        main.app,
        [
            "self-healing-decide",
            "--database-file",
            str(database),
            "--proposal-id",
            proposal_report["proposal_id"],
            "--approver-id",
            "security-operator",
            "--approve",
        ],
    )
    assert decision.exit_code == 0, decision.output
    decision_report = json.loads(decision.stdout)
    assert decision_report["status"] == "APPROVED_PENDING_MANUAL_DEPLOYMENT"
    assert decision_report["change_applied"] is False