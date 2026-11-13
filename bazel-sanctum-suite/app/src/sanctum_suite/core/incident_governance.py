"""Privacy-conscious access auditing and configurable incident retention."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class IncidentGovernanceStore:
    """Stores access metadata without request bodies, IP addresses, or API keys."""

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
                CREATE TABLE IF NOT EXISTS incident_access_audit (
                    audit_id TEXT PRIMARY KEY,
                    occurred_at TEXT NOT NULL,
                    credential_fingerprint TEXT,
                    subject_id TEXT,
                    tenant_id TEXT,
                    authentication_method TEXT,
                    authorization_engine TEXT,
                    authorization_decision TEXT,
                    authorization_policy_version TEXT,
                    action TEXT NOT NULL,
                    outcome_code INTEGER NOT NULL,
                    record_type TEXT NOT NULL
                )
                """
            )
            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(incident_access_audit)"
                ).fetchall()
            }
            for column in (
                "subject_id",
                "tenant_id",
                "authentication_method",
                "authorization_engine",
                "authorization_decision",
                "authorization_policy_version",
            ):
                if column not in columns:
                    connection.execute(
                        f"ALTER TABLE incident_access_audit ADD COLUMN {column} TEXT"
                    )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_incident_access_audit_time "
                "ON incident_access_audit(occurred_at DESC, audit_id)"
            )

    def record_access(
        self,
        *,
        credential_fingerprint: str | None,
        subject_id: str | None = None,
        tenant_id: str | None = None,
        authentication_method: str | None = None,
        authorization_engine: str | None = None,
        authorization_decision: str | None = None,
        authorization_policy_version: str | None = None,
        action: str,
        outcome_code: int,
    ) -> None:
        if credential_fingerprint is not None and len(credential_fingerprint) != 16:
            raise ValueError("credential_fingerprint must be a 16-character digest prefix")
        if not action or len(action) > 256:
            raise ValueError("action must contain between 1 and 256 characters")
        if not 100 <= outcome_code <= 599:
            raise ValueError("outcome_code must be a valid HTTP status code")
        if subject_id is not None and (not subject_id or len(subject_id) > 255):
            raise ValueError("subject_id must contain between 1 and 255 characters")
        if tenant_id is not None and (not tenant_id or len(tenant_id) > 128):
            raise ValueError("tenant_id must contain between 1 and 128 characters")
        if authentication_method not in {None, "api_key", "oidc", "event_source"}:
            raise ValueError("authentication_method is not supported")
        if authorization_engine not in {
            None,
            "local_rbac",
            "opa",
            "opa+rbac",
            "keylime",
            "trustee",
            "keylime+local_rbac",
            "keylime+opa+rbac",
            "trustee+local_rbac",
            "trustee+opa+rbac",
            "keylime+trustee+local_rbac",
            "keylime+trustee+opa+rbac",
            "tee_verifier",
            "tee_verifier+local_rbac",
            "tee_verifier+opa+rbac",
            "keylime+tee_verifier+local_rbac",
            "keylime+tee_verifier+opa+rbac",
        }:
            raise ValueError("authorization_engine is not supported")
        if authorization_decision not in {None, "allow", "deny", "error"}:
            raise ValueError("authorization_decision is not supported")
        if authorization_policy_version is not None and (
            not isinstance(authorization_policy_version, str)
            or not authorization_policy_version
            or len(authorization_policy_version) > 128
        ):
            raise ValueError(
                "authorization_policy_version must contain between 1 and 128 characters"
            )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO incident_access_audit (
                    audit_id, occurred_at, credential_fingerprint, subject_id,
                    tenant_id, authentication_method, authorization_engine,
                    authorization_decision, authorization_policy_version,
                    action, outcome_code, record_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'api_access')
                """,
                (
                    str(uuid.uuid4()),
                    _utc_now().isoformat(),
                    credential_fingerprint,
                    subject_id,
                    tenant_id,
                    authentication_method,
                    authorization_engine,
                    authorization_decision,
                    authorization_policy_version,
                    action,
                    outcome_code,
                ),
            )

    def list_access(self, *, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        with self._connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                "SELECT audit_id, occurred_at, credential_fingerprint, subject_id, "
                "tenant_id, authentication_method, authorization_engine, "
                "authorization_decision, authorization_policy_version, action, "
                    "outcome_code, record_type FROM incident_access_audit "
                    "ORDER BY occurred_at DESC, audit_id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            ]

    def apply_retention(
        self,
        *,
        case_retention_days: int | None = None,
        audit_retention_days: int | None = None,
    ) -> dict[str, int]:
        self._validate_retention(case_retention_days, "case_retention_days")
        self._validate_retention(audit_retention_days, "audit_retention_days")
        result = {"cases_deleted": 0, "audit_records_deleted": 0}
        with self._connect() as connection:
            if case_retention_days is not None:
                cutoff = (_utc_now() - timedelta(days=case_retention_days)).isoformat()
                expired_ids = [
                    row["case_id"]
                    for row in connection.execute(
                        "SELECT case_id FROM incident_cases "
                        "WHERE status IN ('resolved', 'closed') AND updated_at < ?",
                        (cutoff,),
                    ).fetchall()
                ]
                if expired_ids:
                    connection.executemany(
                        "DELETE FROM incident_cases WHERE case_id = ?",
                        [(case_id,) for case_id in expired_ids],
                    )
                    result["cases_deleted"] = len(expired_ids)
                if expired_ids:
                    connection.execute(
                        """
                        INSERT INTO incident_access_audit (
                            audit_id, occurred_at, credential_fingerprint, action,
                            outcome_code, record_type
                        ) VALUES (?, ?, NULL, ?, 200, 'retention')
                        """,
                        (
                            str(uuid.uuid4()),
                            _utc_now().isoformat(),
                            f"retention.deleted_resolved_cases:{len(expired_ids)}",
                        ),
                    )
            if audit_retention_days is not None:
                cutoff = (_utc_now() - timedelta(days=audit_retention_days)).isoformat()
                cursor = connection.execute(
                    "DELETE FROM incident_access_audit WHERE occurred_at < ?",
                    (cutoff,),
                )
                result["audit_records_deleted"] = cursor.rowcount
        return result

    @staticmethod
    def _validate_retention(days: int | None, name: str) -> None:
        if days is not None and not 1 <= days <= 36_500:
            raise ValueError(f"{name} must be between 1 and 36500 days")
