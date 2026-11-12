import sqlite3

from sanctum_suite.core.database import AuditStorageEngine


def test_existing_audit_log_schema_migrates_and_records_authorization(tmp_path):
    database_path = tmp_path / "audit.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE audit_logs (
                audit_id TEXT PRIMARY KEY,
                target TEXT NOT NULL,
                score REAL NOT NULL,
                risk_level TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO audit_logs VALUES (?, ?, ?, ?, ?)",
            ("old-audit", "old.example", 10.0, "LOW", "2026-01-01T00:00:00+00:00"),
        )

    storage = AuditStorageEngine(str(database_path))
    storage.save_audit(
        "new-audit",
        "approved.example",
        25.0,
        "LOW",
        authorization_reference="change-approval-42",
    )

    with sqlite3.connect(database_path) as connection:
        old_row = connection.execute(
            "SELECT authorization_reference FROM audit_logs WHERE audit_id = ?",
            ("old-audit",),
        ).fetchone()
        new_row = connection.execute(
            "SELECT authorization_reference FROM audit_logs WHERE audit_id = ?",
            ("new-audit",),
        ).fetchone()
    assert old_row == ("",)
    assert new_row == ("change-approval-42",)
