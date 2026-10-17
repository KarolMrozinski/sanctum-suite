import sqlite3
from datetime import datetime
from typing import List, Dict, Any


class AuditStorageEngine:
    """Silnik trwałego zapisu wyników audytu w bazie SQLite."""

    def __init__(self, db_path: str = "sanctum_audit.db") -> None:
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    audit_id TEXT PRIMARY KEY,
                    target TEXT NOT NULL,
                    score REAL NOT NULL,
                    risk_level TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.commit()

    def save_audit(self, audit_id: str, target: str, score: float, risk_level: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO audit_logs VALUES (?, ?, ?, ?, ?)",
                (audit_id, target, score, risk_level, datetime.utcnow().isoformat()),
            )
            conn.commit()