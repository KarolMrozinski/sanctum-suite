from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from sanctum_suite.core.audit_chain import canonical_json
from sanctum_suite.core.tee_attestation import TEEAttestation


_ZERO_HASH = "0" * 64
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_MODULE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*){0,15}$")
_ACTIONS = {"opa_policy_update", "key_rotation"}


class SelfHealingApprovalError(RuntimeError):
    """Raised when a remediation proposal cannot safely be recorded or approved."""


class TEEAnomalyAssessmentProvider(Protocol):
    """Integration contract for an independently attested local model runtime."""

    def assess(
        self,
        *,
        evidence_sha256: str,
        attestation: TEEAttestation,
    ) -> dict[str, Any]: ...


def tee_model_capabilities() -> dict[str, str]:
    return {
        "status": "NOT_CONFIGURED",
        "runtime": "none",
        "limitations": (
            "No local model runtime, enclave measurement allowlist, or inference "
            "adapter is configured; anomaly assessments are not generated."
        ),
    }


class AutonomousSelfHealingCoordinator:
    """Stores hash-linked remediation proposals; it never deploys policies or rotates keys."""

    def __init__(self, database_file: Path | None = None) -> None:
        self._database_file = database_file

    def trigger_autonomous_hot_patch(self, compromised_module: str) -> dict[str, Any]:
        return {
            "target_module": compromised_module,
            "status": "NOT_IMPLEMENTED",
            "hot_patch_applied": False,
            "isolation_performed": False,
            "system_recovery_status": "NOT_ASSESSED",
            "total_healed_incidents": None,
        }

    def _connect(self) -> sqlite3.Connection:
        database_file = self._database_file
        if database_file is None:
            raise SelfHealingApprovalError(
                "A persistent proposal database must be configured"
            )
        if not database_file.parent.is_dir():
            raise SelfHealingApprovalError(
                "Proposal database parent directory must exist"
            )
        connection = sqlite3.connect(database_file, timeout=5.0)
        connection.row_factory = sqlite3.Row
        try:
            if database_file.exists():
                database_file.chmod(0o600)
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS self_healing_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_json TEXT NOT NULL,
                    previous_event_sha256 TEXT NOT NULL,
                    event_sha256 TEXT NOT NULL UNIQUE
                )
                """
            )
            connection.executescript(
                """
                CREATE TRIGGER IF NOT EXISTS self_healing_events_no_update
                BEFORE UPDATE ON self_healing_events
                BEGIN
                    SELECT RAISE(ABORT, 'self-healing events are append-only');
                END;
                CREATE TRIGGER IF NOT EXISTS self_healing_events_no_delete
                BEFORE DELETE ON self_healing_events
                BEGIN
                    SELECT RAISE(ABORT, 'self-healing events are append-only');
                END;
                """
            )
        except OSError as error:
            connection.close()
            raise SelfHealingApprovalError(
                "Could not protect remediation proposal database"
            ) from error
        except sqlite3.Error:
            connection.close()
            raise
        return connection

    @staticmethod
    def _event_digest(event: dict[str, Any], previous: str) -> str:
        return hashlib.sha256(
            canonical_json({"event": event, "previous_event_sha256": previous})
        ).hexdigest()

    @staticmethod
    def _validate_event(event: dict[str, Any]) -> bool:
        event_type = event.get("event_type")
        try:
            created_at = datetime.fromisoformat(event["created_at"])
        except (KeyError, TypeError, ValueError):
            return False
        if created_at.tzinfo is None or created_at.utcoffset() is None:
            return False
        if event_type == "proposal":
            return (
                set(event)
                == {
                    "event_type",
                    "proposal_id",
                    "target_module",
                    "action",
                    "reason_code",
                    "evidence_sha256",
                    "current_policy_version",
                    "proposed_change_sha256",
                    "created_by",
                    "created_at",
                }
                and isinstance(event["proposal_id"], str)
                and _IDENTIFIER.fullmatch(event["proposal_id"]) is not None
                and isinstance(event["target_module"], str)
                and _MODULE.fullmatch(event["target_module"]) is not None
                and isinstance(event["action"], str)
                and event["action"] in _ACTIONS
                and isinstance(event["reason_code"], str)
                and _IDENTIFIER.fullmatch(event["reason_code"]) is not None
                and isinstance(event["evidence_sha256"], str)
                and _SHA256.fullmatch(event["evidence_sha256"]) is not None
                and isinstance(event["proposed_change_sha256"], str)
                and _SHA256.fullmatch(event["proposed_change_sha256"]) is not None
                and isinstance(event["current_policy_version"], str)
                and _IDENTIFIER.fullmatch(event["current_policy_version"]) is not None
                and isinstance(event["created_by"], str)
                and _IDENTIFIER.fullmatch(event["created_by"]) is not None
            )
        if event_type == "decision":
            return (
                set(event)
                == {
                    "event_type",
                    "proposal_id",
                    "actor_id",
                    "decision",
                    "created_at",
                }
                and isinstance(event["proposal_id"], str)
                and _IDENTIFIER.fullmatch(event["proposal_id"]) is not None
                and isinstance(event["actor_id"], str)
                and _IDENTIFIER.fullmatch(event["actor_id"]) is not None
                and isinstance(event["decision"], str)
                and event["decision"] in {"approved", "rejected"}
            )
        return False

    def _verify(self, connection: sqlite3.Connection) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        previous = _ZERO_HASH
        rows = connection.execute(
            """
            SELECT sequence, event_json, previous_event_sha256, event_sha256
            FROM self_healing_events
            ORDER BY sequence
            """
        )
        for expected_sequence, row in enumerate(rows, start=1):
            try:
                event = json.loads(row["event_json"])
            except (TypeError, json.JSONDecodeError) as error:
                raise SelfHealingApprovalError(
                    "Remediation proposal event log is invalid"
                ) from error
            if (
                not isinstance(event, dict)
                or not self._validate_event(event)
                or canonical_json(event).decode("utf-8") != row["event_json"]
                or row["sequence"] != expected_sequence
                or row["previous_event_sha256"] != previous
                or row["event_sha256"] != self._event_digest(event, previous)
            ):
                raise SelfHealingApprovalError(
                    "Remediation proposal event log hash chain is invalid"
                )
            events.append(event)
            previous = row["event_sha256"]
        return events

    def _append(self, connection: sqlite3.Connection, event: dict[str, Any]) -> None:
        self._verify(connection)
        latest = connection.execute(
            "SELECT event_sha256 FROM self_healing_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        previous = latest["event_sha256"] if latest is not None else _ZERO_HASH
        serialized = canonical_json(event).decode("utf-8")
        connection.execute(
            """
            INSERT INTO self_healing_events (
                event_json, previous_event_sha256, event_sha256
            ) VALUES (?, ?, ?)
            """,
            (serialized, previous, self._event_digest(event, previous)),
        )

    @staticmethod
    def _proposals(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        proposals: dict[str, dict[str, Any]] = {}
        for event in events:
            if event["event_type"] == "proposal":
                proposals[event["proposal_id"]] = {
                    key: value
                    for key, value in event.items()
                    if key != "event_type"
                }
            else:
                proposal = proposals.get(event["proposal_id"])
                if (
                    proposal is None
                    or proposal.get("decision") is not None
                    or proposal.get("created_by") == event["actor_id"]
                ):
                    raise SelfHealingApprovalError(
                        "Remediation decision references an unknown or decided proposal"
                    )
                proposal["decision"] = event["decision"]
                proposal["decided_by"] = event["actor_id"]
                proposal["decided_at"] = event["created_at"]
        return proposals

    def propose_remediation(
        self,
        *,
        target_module: str,
        action: str,
        reason_code: str,
        evidence_sha256: str,
        current_policy_version: str,
        proposed_change_sha256: str,
        created_by: str,
    ) -> dict[str, Any]:
        if not isinstance(target_module, str) or not _MODULE.fullmatch(target_module):
            raise SelfHealingApprovalError("Remediation target module is invalid")
        if action not in _ACTIONS:
            raise SelfHealingApprovalError(
                "Remediation action must be opa_policy_update or key_rotation"
            )
        if not isinstance(reason_code, str) or not _IDENTIFIER.fullmatch(reason_code):
            raise SelfHealingApprovalError("Remediation reason code is invalid")
        if not isinstance(created_by, str) or not _IDENTIFIER.fullmatch(created_by):
            raise SelfHealingApprovalError("Proposal creator identifier is invalid")
        if (
            not isinstance(evidence_sha256, str)
            or not _SHA256.fullmatch(evidence_sha256)
            or not isinstance(proposed_change_sha256, str)
            or not _SHA256.fullmatch(proposed_change_sha256)
        ):
            raise SelfHealingApprovalError(
                "Evidence and proposed change must be SHA-256 digests"
            )
        if (
            not isinstance(current_policy_version, str)
            or not _IDENTIFIER.fullmatch(current_policy_version)
        ):
            raise SelfHealingApprovalError("Current policy version is invalid")

        proposal_id = str(uuid4())
        event = {
            "event_type": "proposal",
            "proposal_id": proposal_id,
            "target_module": target_module,
            "action": action,
            "reason_code": reason_code,
            "evidence_sha256": evidence_sha256,
            "current_policy_version": current_policy_version,
            "proposed_change_sha256": proposed_change_sha256,
            "created_by": created_by,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._append(connection, event)
        except sqlite3.Error as error:
            raise SelfHealingApprovalError(
                "Could not persist remediation proposal"
            ) from error
        return {
            **{key: value for key, value in event.items() if key != "event_type"},
            "status": "APPROVAL_REQUIRED",
            "change_applied": False,
        }

    def decide_proposal(
        self,
        *,
        proposal_id: str,
        approver_id: str,
        approved: bool,
    ) -> dict[str, Any]:
        if not isinstance(proposal_id, str) or not _IDENTIFIER.fullmatch(proposal_id):
            raise SelfHealingApprovalError("Proposal identifier is invalid")
        if not isinstance(approver_id, str) or not _IDENTIFIER.fullmatch(approver_id):
            raise SelfHealingApprovalError("Approver identifier is invalid")
        if type(approved) is not bool:
            raise SelfHealingApprovalError("Approval decision must be a boolean")
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                proposals = self._proposals(self._verify(connection))
                proposal = proposals.get(proposal_id)
                if proposal is None:
                    raise SelfHealingApprovalError("Remediation proposal was not found")
                if proposal.get("decision") is not None:
                    raise SelfHealingApprovalError(
                        "Remediation proposal already has a decision"
                    )
                if proposal["created_by"] == approver_id:
                    raise SelfHealingApprovalError(
                        "Proposal creator cannot approve their own remediation"
                    )
                event = {
                    "event_type": "decision",
                    "proposal_id": proposal_id,
                    "actor_id": approver_id,
                    "decision": "approved" if approved else "rejected",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                self._append(connection, event)
        except sqlite3.Error as error:
            raise SelfHealingApprovalError(
                "Could not persist remediation decision"
            ) from error
        return {
            "proposal_id": proposal_id,
            "status": (
                "APPROVED_PENDING_MANUAL_DEPLOYMENT"
                if approved
                else "REJECTED"
            ),
            "decided_by": approver_id,
            "change_applied": False,
        }

    def list_proposals(self) -> list[dict[str, Any]]:
        try:
            with self._connect() as connection:
                proposals = self._proposals(self._verify(connection))
        except sqlite3.Error as error:
            raise SelfHealingApprovalError(
                "Could not read remediation proposals"
            ) from error
        results = []
        for proposal in proposals.values():
            decision = proposal.get("decision")
            results.append(
                {
                    **proposal,
                    "status": (
                        "PENDING"
                        if decision is None
                        else decision.upper()
                    ),
                    "change_applied": False,
                }
            )
        return results
