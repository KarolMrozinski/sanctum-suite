#!/usr/bin/env python3

import os
import sqlite3
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (APTIndicatorEngine): %(message)s"
)
logger = logging.getLogger("APTIndicatorEngine")

class SecurityError(Exception):
    pass

class APTIndicatorEngine:
    
    def __init__(self, db_path: Path = Path("/var/lib/sanctum/threat_intel/threat_intel_feed.db"), expected_sha256: Optional[str] = None):
        self.db_path = Path(db_path)
        self.expected_sha256 = expected_sha256
        self._cache: Dict[str, Dict[str, Any]] = {}
        logger.info(f"Inicjalizacja APTIndicatorEngine ze ścieżki: {self.db_path}")

    def verify_database_integrity(self) -> bool:
        if not self.db_path.exists():
            raise FileNotFoundError(f"Krytyczny błąd: Baza Threat Intel nie istnieje pod adresem {self.db_path}")
            
        if not self.expected_sha256:
            logger.warning("Brak zdefiniowanego oczekiwanego hasha SHA-256 dla bazy Threat Intel. Pomijam weryfikację kryptograficzną.")
            return True
            
        sha256_hash = hashlib.sha256()
        try:
            with open(self.db_path, "rb") as f:
                for byte_block in iter(lambda: f.read(65536), b""):
                    sha256_hash.update(byte_block)
            calculated_hash = sha256_hash.hexdigest()
            
            if calculated_hash.lower() != self.expected_sha256.lower():
                raise SecurityError(
                    f"Naruszenie nienaruszalności bazy Threat Intel! "
                    f"Oczekiwano: {self.expected_sha256}, Otrzymano: {calculated_hash}"
                )
            logger.info("Weryfikacja kryptograficzna SHA-256 bazy Threat Intel zakończona pomyślnie.")
            return True
        except Exception as e:
            logger.error(f"Błąd podczas weryfikacji sumy kontrolnej bazy: {e}")
            raise SecurityError(f"Weryfikacja bazy nie powiodła się: {e}") from e

    def _get_connection(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise FileNotFoundError(f"Baza danych nie jest dostępna: {self.db_path}")
        
        uri = f"file:{self.db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    def query_indicator(self, indicator_hash: str) -> Dict[str, Any]:
        clean_hash = indicator_hash.strip().lower()
        
        if clean_hash in self._cache:
            logger.debug(f"Znaleziono wskaźnik {clean_hash} w pamięci podręcznej (cache).")
            return self._cache[clean_hash]

        self.verify_database_integrity()

        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='indicators';")
            table_exists = cursor.fetchone()
            
            if not table_exists:
                conn.close()
                result = {
                    "status": "warning",
                    "matched": False,
                    "indicator": clean_hash,
                    "note": "Tabela 'indicators' nie istnieje w bazie. Wymagane pełne sprovizionowanie."
                }
                return result

            cursor.execute(
                """
                SELECT campaign, confidence, first_seen, threat_actor, vector 
                FROM indicators 
                WHERE hash = ? LIMIT 1;
                """, 
                (clean_hash,)
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                result = {
                    "matched": True,
                    "indicator": clean_hash,
                    "campaign": row["campaign"],
                    "confidence": row["confidence"],
                    "first_seen": row["first_seen"],
                    "threat_actor": row["threat_actor"],
                    "vector": row["vector"],
                    "queried_at": datetime.utcnow().isoformat() + "Z"
                }
            else:
                result = {
                    "matched": False,
                    "indicator": clean_hash,
                    "queried_at": datetime.utcnow().isoformat() + "Z"
                }

            self._cache[clean_hash] = result
            return result

        except sqlite3.Error as db_err:
            logger.error(f"Błąd bazy danych SQLite podczas zapytania IOC: {db_err}")
            raise SecurityError(f"Błąd silnika bazy danych: {db_err}") from db_err

    def batch_query(self, indicator_hashes: List[str]) -> List[Dict[str, Any]]:
        logger.info(f"Rozpoczęto masowe przetwarzanie {len(indicator_hashes)} wskaźników APT.")
        results = []
        for h in indicator_hashes:
            try:
                res = self.query_indicator(h)
                results.append(res)
            except Exception as e:
                results.append({
                    "matched": False,
                    "indicator": h,
                    "error": str(e)
                })
        logger.info("Zakończono masowe przetwarzanie wskaźników.")
        return results