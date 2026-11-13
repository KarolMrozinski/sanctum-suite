#!/usr/bin/env python3

import os
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (DBMaintenance): %(message)s"
)
logger = logging.getLogger("DBMaintenance")

class DatabaseMaintenanceError(Exception):
    pass

class DatabaseMaintenanceGuard:

    def __init__(self, db_paths: List[Path] = None):
        self.db_paths = db_paths or [
            Path("/var/lib/sanctum/threat_intel/threat_intel_feed.db"),
            Path("/var/lib/sanctum/cases/cases.sqlite3")
        ]
        logger.info(f"Inicjalizacja DatabaseMaintenanceGuard dla {len(self.db_paths)} baz danych.")

    def audit_and_optimize_database(self, db_path: Path) -> Dict[str, Any]:
        db_path = Path(db_path)
        if not db_path.exists():
            logger.warning(f"Baza danych nie istnieje pod wskazanym adresem: {db_path}")
            return {"path": str(db_path), "status": "skipped", "reason": "file_not_found"}

        logger.info(f"Rozpoczęto audyt i optymalizację bazy SQLite: {db_path.name}")

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Weryfikacja spójności (PRAGMA integrity_check)
            cursor.execute("PRAGMA integrity_check;")
            integrity_result = cursor.fetchone()[0]

            is_ok = (integrity_result.lower() == "ok")
            if not is_ok:
                logger.error(f"Krytyczny błąd spójności bazy danych {db_path.name}: {integrity_result}")
            else:
                logger.info(f"Spójność bazy {db_path.name} zweryfikowana pomyślnie (OK).")

            # Optymalizacja i defragmentacja (VACUUM / ANALYZE)
            if is_ok:
                cursor.execute("ANALYZE;")
                logger.info(f"Przeprowadzono analizę statystyk optymalizatora dla {db_path.name}.")

            conn.close()

            return {
                "path": str(db_path),
                "status": "healthy" if is_ok else "corrupted",
                "integrity_check": integrity_result,
                "optimized_at": datetime.utcnow().isoformat() + "Z"
            }

        except Exception as e:
            logger.error(f"Błąd podczas konserwacji bazy danych {db_path}: {e}")
            raise DatabaseMaintenanceError(f"Konserwacja bazy nie powiodła się: {e}") from e

    def run_maintenance_cycle(self) -> Dict[str, Any]:
        logger.info("Uruchomiono pełny cykl konserwacji i audytu baz danych w systemie.")
        results = []

        for path in self.db_paths:
            res = self.audit_and_optimize_database(path)
            results.append(res)

        report = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_databases_processed": len(results),
            "results": results
        }

        logger.info("Cykl konserwacji baz danych zakończony pomyślnie.")
        return report