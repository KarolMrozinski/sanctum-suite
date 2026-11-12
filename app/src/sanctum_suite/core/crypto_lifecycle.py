#!/usr/bin/env python3

import os
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (CryptoLifecycle): %(message)s"
)
logger = logging.getLogger("CryptoLifecycle")

class CryptoError(Exception):
    pass

class CryptoLifecycleManager:

    def __init__(self, keys_dir: Path = Path("/var/lib/sanctum/keys")):
        self.keys_dir = Path(keys_dir)
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Inicjalizacja CryptoLifecycleManager z katalogiem kluczy: {self.keys_dir}")

    def verify_key_material(self, key_filename: str, expected_sha256: str) -> bool:
        key_path = self.keys_dir / key_filename
        if not key_path.exists():
            raise FileNotFoundError(f"Klucz kryptograficzny nie istnieje w ścieżce systemowej: {key_path}")

        logger.info(f"Weryfikacja nienaruszalności materiału kluczowego: {key_filename}")

        try:
            raw_key = key_path.read_bytes()
            calculated_hash = hashlib.sha256(raw_key).hexdigest()

            is_valid = (calculated_hash.lower() == expected_sha256.lower())
            if not is_valid:
                logger.error(
                    f"Krytyczny błąd: Naruszenie nienaruszalności klucza {key_filename}! "
                    f"Oczekiwano: {expected_sha256}, Otrzymano: {calculated_hash}"
                )
                return False

            logger.info(f"Klucz {key_filename} zweryfikowany kryptograficznie pomyślnie.")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas weryfikacji klucza: {e}")
            raise CryptoError(f"Weryfikacja klucza nie powiodła się: {e}") from e

    def get_key_metadata(self, key_filename: str) -> Dict[str, Any]:
        key_path = self.keys_dir / key_filename
        if not key_path.exists():
            raise FileNotFoundError(f"Plik klucza nie istnieje: {key_path}")

        stat = key_path.stat()
        raw_key = key_path.read_bytes()
        key_hash = hashlib.sha256(raw_key).hexdigest()

        return {
            "key_filename": key_filename,
            "size_bytes": stat.st_size,
            "sha256": key_hash,
            "status": "active",
            "checked_at": datetime.utcnow().isoformat() + "Z"
        }