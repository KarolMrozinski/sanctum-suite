import sqlite3
import os
import hashlib


class IsolatedChallengeStateMachine:
    """Bezpieczny menedżer stanu i telemetrii sesji wyzwania (SQLite wewnątrz zakresu DLC)."""

    def __init__(self, db_path: str = "sanctum_cicada_state.db") -> None:
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                operator_callsign TEXT,
                current_stage INTEGER,
                is_solved INTEGER,
                telemetry_log TEXT
            )
        """)
        conn.commit()
        conn.close()

    def create_session(self, session_id: str, operator_callsign: str) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO sessions (session_id, operator_callsign, current_stage, is_solved, telemetry_log) VALUES (?, ?, 1, 0, ?)",
            (session_id, operator_callsign, "Session initialized securely.")
        )
        conn.commit()
        conn.close()

    def update_stage(self, session_id: str, new_stage: int, telemetry_msg: str) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sessions SET current_stage = ?, telemetry_log = telemetry_log || ? WHERE session_id = ?",
            (new_stage, f"\n[LOG] {telemetry_msg}", session_id)
        )
        conn.commit()
        conn.close()

    def get_session_state(self, session_id: str) -> dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT session_id, operator_callsign, current_stage, is_solved, telemetry_log FROM sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return {}
        return {
            "session_id": row[0],
            "operator_callsign": row[1],
            "current_stage": row[2],
            "is_solved": bool(row[3]),
            "telemetry_log": row[4]
        }