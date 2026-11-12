import duckdb
from datetime import datetime
from typing import Dict, Any, List


class AnalyticsStoreEngine:
    """Silnik analityczny OLAP w DuckDB do ultraszybkiego zapytaniowania i agregacji logów audytowych."""

    def __init__(self, db_path: str = "sanctum_analytics.duckdb") -> None:
        self.db_path = db_path
        self._init_analytics_db()

    def _init_analytics_db(self) -> None:
        with duckdb.connect(self.db_path) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS security_events (
                    event_id VARCHAR PRIMARY KEY,
                    audit_id VARCHAR,
                    target VARCHAR,
                    module_source VARCHAR,
                    risk_score DOUBLE,
                    details VARCHAR,
                    created_at TIMESTAMP
                )
            """)

    def record_event(self, event_id: str, audit_id: str, target: str, source: str, score: float, details: str) -> None:
        with duckdb.connect(self.db_path) as con:
            con.execute(
                "INSERT INTO security_events VALUES (?, ?, ?, ?, ?, ?, ?)",
                (event_id, audit_id, target, source, score, details, datetime.utcnow()),
            )

    def get_target_threat_metrics(self, target: str) -> Dict[str, Any]:
        with duckdb.connect(self.db_path) as con:
            res = con.execute("""
                SELECT 
                    COUNT(*) as total_events,
                    AVG(risk_score) as avg_risk_score,
                    MAX(risk_score) as max_risk_score
                FROM security_events
                WHERE target = ?
            """, [target]).fetchone()

            if not res or res[0] == 0:
                return {"total_events": 0, "avg_risk_score": 0.0, "max_risk_score": 0.0}

            return {
                "total_events": res[0],
                "avg_risk_score": round(res[1], 2),
                "max_risk_score": round(res[2], 2),
            }