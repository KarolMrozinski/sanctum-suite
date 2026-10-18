"""Persistent incident case records and activity references."""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_CASE_STATUSES = {"open", "in_progress", "resolved", "closed"}
_PRIORITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO", "NOT_ASSESSED"}
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class IncidentCaseStore:
    """SQLite-backed cases; notes and evidence references are append-only."""

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
                CREATE TABLE IF NOT EXISTS incident_cases (
                    case_id TEXT PRIMARY KEY,
                    correlation_id TEXT UNIQUE,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    priority TEXT NOT NULL CHECK (
                        priority IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO', 'NOT_ASSESSED')
                    ),
                    status TEXT NOT NULL CHECK (
                        status IN ('open', 'in_progress', 'resolved', 'closed')
                    ),
                    assigned_to TEXT,
                    created_by TEXT NOT NULL,
                    priority_reasons_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS incident_case_events (
                    case_event_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL REFERENCES incident_cases(case_id) ON DELETE CASCADE,
                    event_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    source TEXT,
                    observed_at TEXT,
                    reported_severity TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(case_id, event_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS incident_case_notes (
                    note_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL REFERENCES incident_cases(case_id) ON DELETE CASCADE,
                    author TEXT NOT NULL,
                    body TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS incident_case_evidence (
                    evidence_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL REFERENCES incident_cases(case_id) ON DELETE CASCADE,
                    source TEXT NOT NULL,
                    reference TEXT NOT NULL,
                    sha256 TEXT,
                    added_by TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_incident_cases_updated "
                "ON incident_cases(updated_at DESC, case_id)"
            )

    @staticmethod
    def _validate_text(value: str, name: str, maximum: int) -> None:
        if not value.strip() or len(value) > maximum:
            raise ValueError(f"{name} must contain between 1 and {maximum} characters")

    def create_case(
        self,
        *,
        title: str,
        summary: str,
        created_by: str,
        priority: str = "NOT_ASSESSED",
        correlation_id: str | None = None,
        priority_reasons: list[str] | None = None,
        timeline: list[dict[str, Any]] | None = None,
        assigned_to: str | None = None,
    ) -> dict[str, Any]:
        self._validate_text(title, "title", 200)
        self._validate_text(summary, "summary", 4_000)
        self._validate_text(created_by, "created_by", 200)
        if priority not in _PRIORITIES:
            raise ValueError("priority is not supported")
        if correlation_id is not None:
            self._validate_text(correlation_id, "correlation_id", 128)
        if assigned_to is not None:
            self._validate_text(assigned_to, "assigned_to", 200)
        reasons = priority_reasons or []
        if len(reasons) > 20 or any(not reason.strip() or len(reason) > 500 for reason in reasons):
            raise ValueError("priority_reasons must contain at most 20 non-empty entries of 500 characters")
        events = timeline or []
        if len(events) > 1_000:
            raise ValueError("timeline cannot contain more than 1000 events")
        event_ids: set[str] = set()
        for event in events:
            if (
                not isinstance(event, dict)
                or not isinstance(event.get("event_id"), str)
                or not event["event_id"]
                or len(event["event_id"]) > 128
                or not isinstance(event.get("event_type"), str)
                or not event["event_type"]
                or len(event["event_type"]) > 128
            ):
                raise ValueError("timeline events require valid event_id and event_type")
            if event["event_id"] in event_ids:
                raise ValueError("timeline event_id values must be unique")
            event_ids.add(event["event_id"])
        case_id = str(uuid.uuid4())
        created_at = _utc_now()
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO incident_cases (
                        case_id, correlation_id, title, summary, priority, status,
                        assigned_to, created_by, priority_reasons_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?)
                    """,
                    (
                        case_id,
                        correlation_id,
                        title.strip(),
                        summary.strip(),
                        priority,
                        assigned_to.strip() if assigned_to else None,
                        created_by.strip(),
                        json.dumps(reasons, ensure_ascii=False),
                        created_at,
                        created_at,
                    ),
                )
                for event in events:
                    connection.execute(
                        """
                        INSERT INTO incident_case_events (
                            case_event_id, case_id, event_id, event_type, source,
                            observed_at, reported_severity, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(uuid.uuid4()),
                            case_id,
                            event["event_id"],
                            event["event_type"],
                            event.get("source"),
                            event.get("observed_at"),
                            event.get("reported_severity"),
                            created_at,
                        ),
                    )
        except sqlite3.IntegrityError as error:
            if "incident_cases.correlation_id" in str(error):
                raise ValueError("A case already exists for this correlation_id") from error
            raise
        result = self.get_case(case_id)
        if result is None:
            raise RuntimeError("Case was saved but could not be read back")
        return result

    def list_cases(self, *, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        if status is not None and status not in _CASE_STATUSES:
            raise ValueError("status is not supported")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        with self._connect() as connection:
            if status is None:
                rows = connection.execute(
                    "SELECT * FROM incident_cases ORDER BY updated_at DESC, case_id LIMIT ?",
                    (limit,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM incident_cases WHERE status = ? "
                    "ORDER BY updated_at DESC, case_id LIMIT ?",
                    (status, limit),
                ).fetchall()
            return [self._case_summary(row, connection) for row in rows]

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM incident_cases WHERE case_id = ?", (case_id,)
            ).fetchone()
            if row is None:
                return None
            result = self._case_summary(row, connection)
            result["timeline"] = [
                dict(event)
                for event in connection.execute(
                    "SELECT event_id, event_type, source, observed_at, reported_severity "
                    "FROM incident_case_events WHERE case_id = ? "
                    "ORDER BY observed_at IS NULL, observed_at, case_event_id",
                    (case_id,),
                ).fetchall()
            ]
            result["notes"] = [
                dict(note)
                for note in connection.execute(
                    "SELECT note_id, author, body, created_at FROM incident_case_notes "
                    "WHERE case_id = ? ORDER BY created_at, note_id",
                    (case_id,),
                ).fetchall()
            ]
            result["evidence"] = [
                dict(item)
                for item in connection.execute(
                    "SELECT evidence_id, source, reference, sha256, added_by, created_at "
                    "FROM incident_case_evidence WHERE case_id = ? "
                    "ORDER BY created_at, evidence_id",
                    (case_id,),
                ).fetchall()
            ]
            return result

    @staticmethod
    def _case_summary(row: sqlite3.Row, connection: sqlite3.Connection) -> dict[str, Any]:
        event_count = connection.execute(
            "SELECT COUNT(*) FROM incident_case_events WHERE case_id = ?",
            (row["case_id"],),
        ).fetchone()[0]
        return {
            "case_id": row["case_id"],
            "correlation_id": row["correlation_id"],
            "title": row["title"],
            "summary": row["summary"],
            "priority": row["priority"],
            "priority_reasons": json.loads(row["priority_reasons_json"]),
            "status": row["status"],
            "assigned_to": row["assigned_to"],
            "created_by": row["created_by"],
            "event_count": event_count,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def update_case(
        self,
        case_id: str,
        *,
        status: str | None = None,
        assigned_to: str | None = None,
        update_assignee: bool | None = None,
    ) -> dict[str, Any] | None:
        if update_assignee is None:
            update_assignee = assigned_to is not None
        if status is None and not update_assignee:
            raise ValueError("At least one case field must be updated")
        if status is not None and status not in _CASE_STATUSES:
            raise ValueError("status is not supported")
        if assigned_to is not None:
            self._validate_text(assigned_to, "assigned_to", 200)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT case_id FROM incident_cases WHERE case_id = ?", (case_id,)
            ).fetchone()
            if row is None:
                return None
            fields = ["updated_at = ?"]
            values: list[Any] = [_utc_now()]
            if status is not None:
                fields.append("status = ?")
                values.append(status)
            if update_assignee:
                fields.append("assigned_to = ?")
                values.append(assigned_to.strip() if assigned_to else None)
            values.append(case_id)
            connection.execute(
                f"UPDATE incident_cases SET {', '.join(fields)} WHERE case_id = ?",
                values,
            )
        return self.get_case(case_id)

    def add_note(self, case_id: str, *, author: str, body: str) -> dict[str, Any] | None:
        self._validate_text(author, "author", 200)
        self._validate_text(body, "body", 4_000)
        with self._connect() as connection:
            if connection.execute(
                "SELECT 1 FROM incident_cases WHERE case_id = ?", (case_id,)
            ).fetchone() is None:
                return None
            connection.execute(
                "INSERT INTO incident_case_notes (note_id, case_id, author, body, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), case_id, author.strip(), body.strip(), _utc_now()),
            )
            connection.execute(
                "UPDATE incident_cases SET updated_at = ? WHERE case_id = ?",
                (_utc_now(), case_id),
            )
        return self.get_case(case_id)

    def add_evidence(
        self,
        case_id: str,
        *,
        source: str,
        reference: str,
        added_by: str,
        sha256: str | None = None,
    ) -> dict[str, Any] | None:
        self._validate_text(source, "source", 100)
        self._validate_text(reference, "reference", 2_048)
        self._validate_text(added_by, "added_by", 200)
        if sha256 is not None and not _SHA256_PATTERN.fullmatch(sha256):
            raise ValueError("sha256 must be a lowercase 64-character hex digest")
        with self._connect() as connection:
            if connection.execute(
                "SELECT 1 FROM incident_cases WHERE case_id = ?", (case_id,)
            ).fetchone() is None:
                return None
            connection.execute(
                """
                INSERT INTO incident_case_evidence (
                    evidence_id, case_id, source, reference, sha256, added_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    case_id,
                    source.strip(),
                    reference.strip(),
                    sha256,
                    added_by.strip(),
                    _utc_now(),
                ),
            )
            connection.execute(
                "UPDATE incident_cases SET updated_at = ? WHERE case_id = ?",
                (_utc_now(), case_id),
            )
        return self.get_case(case_id)
