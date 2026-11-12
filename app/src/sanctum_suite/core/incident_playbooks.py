"""Simulated, human-reviewed incident response recommendations."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class IncidentPlaybookStore:
    """Persists recommendation snapshots and append-only operator decisions."""

    def __init__(self, db_path: str | Path = "sanctum_cases.db") -> None:
        self.db_path = str(Path(db_path).expanduser())
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        Path(self.db_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS incident_playbooks (
                    plan_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL REFERENCES incident_cases(case_id) ON DELETE CASCADE,
                    status TEXT NOT NULL CHECK (
                        status IN ('simulated', 'approved_for_manual_review', 'rejected')
                    ),
                    simulated_by TEXT NOT NULL,
                    case_snapshot_json TEXT NOT NULL,
                    steps_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_incident_playbooks_case "
                "ON incident_playbooks(case_id, created_at DESC)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS incident_playbook_decisions (
                    decision_id TEXT PRIMARY KEY,
                    plan_id TEXT NOT NULL REFERENCES incident_playbooks(plan_id) ON DELETE CASCADE,
                    decision TEXT NOT NULL CHECK (decision IN ('approve', 'reject')),
                    reviewer TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _validate_text(value: str, name: str, maximum: int) -> None:
        if not value.strip() or len(value) > maximum:
            raise ValueError(f"{name} must contain between 1 and {maximum} characters")

    @staticmethod
    def _recommendations(
        priority: str,
        event_types: list[str],
        has_evidence: bool,
    ) -> list[dict[str, str]]:
        steps = [
            {
                "step_id": "verify-scope",
                "title": "Verify incident scope and response authority",
                "description": (
                    "Manually confirm affected assets, the approved response scope, "
                    "and the responsible decision-maker before taking action."
                ),
                "basis": f"Case priority is source-reported as {priority}; independently validate it.",
            },
            {
                "step_id": "preserve-evidence",
                "title": "Preserve and validate relevant evidence",
                "description": (
                    "Follow the organization's evidence-handling process. Preserve source "
                    "records, timestamps, and chain-of-custody details; do not alter originals."
                ),
                "basis": (
                    "Existing evidence references are available."
                    if has_evidence
                    else "No evidence references are currently attached to the case."
                ),
            },
            {
                "step_id": "assess-impact",
                "title": "Assess impact and uncertainty",
                "description": (
                    "Have an analyst review the case timeline with the relevant system owner "
                    "and record confirmed impact separately from assumptions."
                ),
                "basis": (
                    "Review the caller-supplied event sequence; exact-key grouping alone "
                    "does not establish malicious activity."
                ),
            },
            {
                "step_id": "coordinate-response",
                "title": "Coordinate through the approved response process",
                "description": (
                    "Notify the designated incident lead and asset owner using the "
                    "organization's established escalation and communications process."
                ),
                "basis": "Human coordination is required; this plan sends no notifications.",
            },
            {
                "step_id": "manual-change-review",
                "title": "Require separate change approval for any containment",
                "description": (
                    "If containment is warranted, prepare a separate change request, assess "
                    "operational impact, and obtain the required independent approval."
                ),
                "basis": "This simulated playbook cannot authorize or perform containment.",
            },
        ]
        if any("privilege" in event_type.casefold() for event_type in event_types):
            steps.insert(
                2,
                {
                    "step_id": "review-access-records",
                    "title": "Review relevant access-control records",
                    "description": (
                        "Ask the authorized identity or system owner to validate the reported "
                        "access change against their own audit records and approved request."
                    ),
                    "basis": "The case timeline contains a privilege-related event label.",
                },
            )
        return steps

    def simulate(self, case_id: str, *, simulated_by: str) -> dict[str, Any] | None:
        self._validate_text(simulated_by, "simulated_by", 200)
        plan_id = str(uuid.uuid4())
        created_at = _utc_now()
        with self._connect() as connection:
            case = connection.execute(
                "SELECT * FROM incident_cases WHERE case_id = ?", (case_id,)
            ).fetchone()
            if case is None:
                return None
            events = connection.execute(
                "SELECT event_id, event_type, source, observed_at, reported_severity "
                "FROM incident_case_events WHERE case_id = ? "
                "ORDER BY observed_at IS NULL, observed_at, case_event_id",
                (case_id,),
            ).fetchall()
            evidence_count = connection.execute(
                "SELECT COUNT(*) FROM incident_case_evidence WHERE case_id = ?",
                (case_id,),
            ).fetchone()[0]
            snapshot = {
                "title": case["title"],
                "priority": case["priority"],
                "priority_reasons": json.loads(case["priority_reasons_json"]),
                "status": case["status"],
                "event_count": len(events),
                "evidence_reference_count": evidence_count,
                "event_types": sorted({event["event_type"] for event in events}),
            }
            steps = self._recommendations(
                case["priority"],
                [event["event_type"] for event in events],
                evidence_count > 0,
            )
            connection.execute(
                """
                INSERT INTO incident_playbooks (
                    plan_id, case_id, status, simulated_by, case_snapshot_json,
                    steps_json, created_at, updated_at
                ) VALUES (?, ?, 'simulated', ?, ?, ?, ?, ?)
                """,
                (
                    plan_id,
                    case_id,
                    simulated_by.strip(),
                    json.dumps(snapshot, ensure_ascii=False),
                    json.dumps(steps, ensure_ascii=False),
                    created_at,
                    created_at,
                ),
            )
        result = self.get_plan(plan_id)
        if result is None:
            raise RuntimeError("Playbook simulation was saved but could not be read back")
        return result

    def list_plans(self, case_id: str) -> list[dict[str, Any]] | None:
        with self._connect() as connection:
            if connection.execute(
                "SELECT 1 FROM incident_cases WHERE case_id = ?", (case_id,)
            ).fetchone() is None:
                return None
            plan_ids = connection.execute(
                "SELECT plan_id FROM incident_playbooks WHERE case_id = ? "
                "ORDER BY created_at DESC, plan_id",
                (case_id,),
            ).fetchall()
        plans = [self.get_plan(row["plan_id"]) for row in plan_ids]
        return [plan for plan in plans if plan is not None]

    def get_plan(self, plan_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM incident_playbooks WHERE plan_id = ?", (plan_id,)
            ).fetchone()
            if row is None:
                return None
            return {
                "plan_id": row["plan_id"],
                "case_id": row["case_id"],
                "status": row["status"],
                "simulated_by": row["simulated_by"],
                "case_snapshot": json.loads(row["case_snapshot_json"]),
                "steps": json.loads(row["steps_json"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "decisions": [
                    dict(decision)
                    for decision in connection.execute(
                        "SELECT decision_id, decision, reviewer, rationale, created_at "
                        "FROM incident_playbook_decisions WHERE plan_id = ? "
                        "ORDER BY created_at, decision_id",
                        (plan_id,),
                    ).fetchall()
                ],
                "execution_status": "NOT_EXECUTED",
            }

    def record_decision(
        self,
        plan_id: str,
        *,
        decision: str,
        reviewer: str,
        rationale: str,
    ) -> dict[str, Any] | None:
        if decision not in {"approve", "reject"}:
            raise ValueError("decision must be approve or reject")
        self._validate_text(reviewer, "reviewer", 200)
        self._validate_text(rationale, "rationale", 2_000)
        now = _utc_now()
        with self._connect() as connection:
            plan = connection.execute(
                "SELECT status FROM incident_playbooks WHERE plan_id = ?", (plan_id,)
            ).fetchone()
            if plan is None:
                return None
            connection.execute(
                """
                INSERT INTO incident_playbook_decisions (
                    decision_id, plan_id, decision, reviewer, rationale, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), plan_id, decision, reviewer.strip(), rationale.strip(), now),
            )
            connection.execute(
                "UPDATE incident_playbooks SET status = ?, updated_at = ? WHERE plan_id = ?",
                (
                    "approved_for_manual_review" if decision == "approve" else "rejected",
                    now,
                    plan_id,
                ),
            )
        return self.get_plan(plan_id)
