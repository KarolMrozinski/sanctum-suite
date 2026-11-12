"""Normalized SQLite store for explicitly configured telemetry sources."""

from __future__ import annotations

import hashlib
import re
import sqlite3
import uuid
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


_SOURCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_CORRELATION_TOKEN = re.compile(r"^[0-9a-f]{64}$")
_EVENT_LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_timestamp(value: str) -> str:
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("observed_at must be an ISO 8601 timestamp") from error
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("observed_at must include a timezone")
    return (
        timestamp.astimezone(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def validate_source_id(source_id: str) -> str:
    if not isinstance(source_id, str) or not _SOURCE_ID.fullmatch(source_id):
        raise ValueError("source_id must match [A-Za-z0-9][A-Za-z0-9._-]{0,63}")
    return source_id


def validate_event_label(value: str) -> str:
    if not isinstance(value, str) or not _EVENT_LABEL.fullmatch(value):
        raise ValueError(
            "telemetry labels must be structured identifiers without free text"
        )
    return value


class TelemetryEventStore:
    """Stores normalized fields only; raw payloads and external IDs are not retained."""

    def __init__(
        self,
        db_path: str | Path = "sanctum_cases.db",
        *,
        pseudonymize: Callable[[str, str], str] | None = None,
    ) -> None:
        self.db_path = str(Path(db_path).expanduser())
        self._pseudonymize = pseudonymize
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS telemetry_ingestion_batches (
                    batch_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    received_count INTEGER NOT NULL,
                    inserted_count INTEGER NOT NULL,
                    duplicate_count INTEGER NOT NULL,
                    received_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS normalized_telemetry_events (
                    event_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    source_event_id_sha256 TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    reported_severity TEXT,
                    detection_scenario_id TEXT,
                    detection_rule_id TEXT,
                    correlation_token_sha256 TEXT,
                    ingested_at TEXT NOT NULL,
                    batch_id TEXT NOT NULL REFERENCES telemetry_ingestion_batches(batch_id)
                        ON DELETE CASCADE,
                    UNIQUE(source_id, source_event_id_sha256)
                )
                """
            )
            event_columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(normalized_telemetry_events)"
                ).fetchall()
            }
            if "detection_scenario_id" not in event_columns:
                connection.execute(
                    "ALTER TABLE normalized_telemetry_events "
                    "ADD COLUMN detection_scenario_id TEXT"
                )
            if "detection_rule_id" not in event_columns:
                connection.execute(
                    "ALTER TABLE normalized_telemetry_events "
                    "ADD COLUMN detection_rule_id TEXT"
                )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_telemetry_events_time "
                "ON normalized_telemetry_events(ingested_at DESC, event_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_telemetry_events_correlation "
                "ON normalized_telemetry_events(correlation_token_sha256, ingested_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_telemetry_batches_source "
                "ON telemetry_ingestion_batches(source_id, received_at DESC)"
            )

    def _digest_identifier(self, namespace: str, value: str) -> str:
        digest = (
            self._pseudonymize(namespace, value)
            if self._pseudonymize is not None
            else hashlib.sha256(value.encode("utf-8")).hexdigest()
        )
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(
                "pseudonymizer must return a lowercase SHA-256-sized hex value"
            )
        return digest

    def correlation_digest(self, token: str | None) -> str | None:
        if token is None:
            return None
        if not _CORRELATION_TOKEN.fullmatch(token):
            raise ValueError("correlation_token must be a lowercase 64-character hex token")
        return self._digest_identifier("correlation_token", token)

    def ingest(
        self,
        source_id: str,
        events: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        validate_source_id(source_id)
        if not 1 <= len(events) <= 1_000:
            raise ValueError("events must contain between 1 and 1000 entries")
        normalized_events: list[dict[str, Any]] = []
        for event in events:
            source_event_id = event.get("source_event_id")
            event_type = event.get("event_type")
            observed_at = event.get("observed_at")
            severity = event.get("severity")
            detection_scenario_id = event.get("detection_scenario_id")
            detection_rule_id = event.get("detection_rule_id")
            correlation_token = event.get("correlation_token")
            if (
                not isinstance(source_event_id, str)
                or not source_event_id.strip()
                or len(source_event_id) > 256
                or not isinstance(event_type, str)
                or not event_type
                or len(event_type) > 128
                or not isinstance(observed_at, str)
            ):
                raise ValueError("events require source_event_id, event_type, and observed_at")
            validate_event_label(event_type)
            if severity is not None and severity not in {
                "CRITICAL",
                "HIGH",
                "MEDIUM",
                "LOW",
                "INFO",
            }:
                raise ValueError("severity is not supported")
            if (detection_scenario_id is None) != (detection_rule_id is None):
                raise ValueError(
                    "detection_scenario_id and detection_rule_id must be provided together"
                )
            if detection_scenario_id is not None and (
                not isinstance(detection_scenario_id, str)
                or not detection_scenario_id
                or len(detection_scenario_id) > 128
                or not isinstance(detection_rule_id, str)
                or not detection_rule_id
                or len(detection_rule_id) > 128
            ):
                raise ValueError("detection identifiers must contain 1 to 128 characters")
            if detection_scenario_id is not None:
                validate_event_label(detection_scenario_id)
                validate_event_label(detection_rule_id)
            normalized_events.append(
                {
                    "event_id": str(uuid.uuid4()),
                    "source_event_id_sha256": self._digest_identifier(
                        "source_event_id", source_event_id
                    ),
                    "legacy_source_event_id_sha256": (
                        hashlib.sha256(source_event_id.encode("utf-8")).hexdigest()
                        if self._pseudonymize is not None
                        else None
                    ),
                    "event_type": event_type,
                    "observed_at": normalize_timestamp(observed_at),
                    "reported_severity": severity,
                    "detection_scenario_id": (
                        detection_scenario_id
                        if detection_scenario_id is not None
                        else None
                    ),
                    "detection_rule_id": (
                        detection_rule_id if detection_rule_id is not None else None
                    ),
                    "correlation_token_sha256": self.correlation_digest(correlation_token),
                }
            )

        batch_id = str(uuid.uuid4())
        received_at = _utc_now().isoformat()
        inserted = 0
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO telemetry_ingestion_batches (
                    batch_id, source_id, received_count, inserted_count,
                    duplicate_count, received_at
                ) VALUES (?, ?, ?, 0, 0, ?)
                """,
                (batch_id, source_id, len(events), received_at),
            )
            for event in normalized_events:
                legacy_digest = event["legacy_source_event_id_sha256"]
                if legacy_digest is not None:
                    # Raw IDs were discarded, so upgrade legacy hashes only on replay.
                    legacy_row = connection.execute(
                        """
                        SELECT event_id FROM normalized_telemetry_events
                        WHERE source_id = ? AND source_event_id_sha256 = ?
                        """,
                        (source_id, legacy_digest),
                    ).fetchone()
                    if legacy_row is not None:
                        keyed_row = connection.execute(
                            """
                            SELECT event_id FROM normalized_telemetry_events
                            WHERE source_id = ? AND source_event_id_sha256 = ?
                            """,
                            (source_id, event["source_event_id_sha256"]),
                        ).fetchone()
                        if keyed_row is None:
                            connection.execute(
                                """
                                UPDATE normalized_telemetry_events
                                SET source_event_id_sha256 = ?,
                                    correlation_token_sha256 = ?
                                WHERE event_id = ?
                                """,
                                (
                                    event["source_event_id_sha256"],
                                    event["correlation_token_sha256"],
                                    legacy_row["event_id"],
                                ),
                            )
                        continue
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO normalized_telemetry_events (
                        event_id, source_id, source_event_id_sha256, event_type,
                        observed_at, reported_severity, detection_scenario_id,
                        detection_rule_id, correlation_token_sha256, ingested_at, batch_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event["event_id"],
                        source_id,
                        event["source_event_id_sha256"],
                        event["event_type"],
                        event["observed_at"],
                        event["reported_severity"],
                        event["detection_scenario_id"],
                        event["detection_rule_id"],
                        event["correlation_token_sha256"],
                        received_at,
                        batch_id,
                    ),
                )
                inserted += cursor.rowcount
            connection.execute(
                """
                UPDATE telemetry_ingestion_batches
                SET inserted_count = ?, duplicate_count = ?
                WHERE batch_id = ?
                """,
                (inserted, len(events) - inserted, batch_id),
            )
        return {
            "batch_id": batch_id,
            "source_id": source_id,
            "received_count": len(events),
            "inserted_count": inserted,
            "duplicate_count": len(events) - inserted,
            "received_at": received_at,
        }

    def list_events(
        self,
        *,
        source_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        if not 1 <= limit <= 1_000:
            raise ValueError("limit must be between 1 and 1000")
        with self._connect() as connection:
            if source_id is None:
                rows = connection.execute(
                    """
                    SELECT event_id, source_id, event_type, observed_at,
                        reported_severity, detection_scenario_id, detection_rule_id,
                        correlation_token_sha256, ingested_at
                    FROM normalized_telemetry_events
                    ORDER BY observed_at DESC, event_id LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            else:
                validate_source_id(source_id)
                rows = connection.execute(
                    """
                    SELECT event_id, source_id, event_type, observed_at,
                        reported_severity, detection_scenario_id, detection_rule_id,
                        correlation_token_sha256, ingested_at
                    FROM normalized_telemetry_events
                    WHERE source_id = ?
                    ORDER BY observed_at DESC, event_id LIMIT ?
                    """,
                    (source_id, limit),
                ).fetchall()
            return [dict(row) for row in rows]

    def find_correlated_events(
        self,
        *,
        window_hours: int = 24,
        limit: int = 10_000,
    ) -> list[dict[str, Any]]:
        if not 1 <= window_hours <= 720:
            raise ValueError("window_hours must be between 1 and 720")
        if not 2 <= limit <= 10_000:
            raise ValueError("limit must be between 2 and 10000")
        cutoff = (_utc_now() - timedelta(hours=window_hours)).isoformat()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_id, source_id, event_type, observed_at,
                    reported_severity, detection_scenario_id, detection_rule_id,
                    correlation_token_sha256
                FROM normalized_telemetry_events
                WHERE correlation_token_sha256 IS NOT NULL AND ingested_at >= ?
                ORDER BY ingested_at DESC, event_id
                LIMIT ?
                """,
                (cutoff, limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def delete_expired_events(self, *, retention_days: int | None) -> int:
        if retention_days is None:
            return 0
        if not 1 <= retention_days <= 36_500:
            raise ValueError("retention_days must be between 1 and 36500")
        cutoff = (_utc_now() - timedelta(days=retention_days)).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM normalized_telemetry_events WHERE ingested_at < ?",
                (cutoff,),
            )
            connection.execute(
                """
                DELETE FROM telemetry_ingestion_batches
                WHERE received_at < ?
                    AND NOT EXISTS (
                        SELECT 1 FROM normalized_telemetry_events
                        WHERE normalized_telemetry_events.batch_id =
                            telemetry_ingestion_batches.batch_id
                    )
                """,
                (cutoff,),
            )
            return cursor.rowcount
