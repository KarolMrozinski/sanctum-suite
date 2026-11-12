#!/usr/bin/env python3

import os
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (ConfigVault): %(message)s"
)
logger = logging.getLogger("ConfigVault")

class VaultError(Exception):
    pass

class SecureConfigVault:

    def __init__(self, config_path: Path = Path("/var/lib/sanctum/config/node_config.json"), expected_sha256: Optional[str] = None):
        self.config_path = Path(config_path)
        self.expected_sha256 = expected_sha256
        logger.info(f"Inicjalizacja SecureConfigVault ze ścieżki: {self.config_path}")

    def load_and_verify_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Krytyczny błąd: Plik konfiguracyjny węzła nie istnieje: {self.config_path}")

        logger.info(f"Weryfikacja nienaruszalności pliku konfiguracyjnego: {self.config_path.name}")
        
        try:
            raw_data = self.config_path.read_bytes()
            calculated_hash = hashlib.sha256(raw_data).hexdigest()

            if self.expected_sha256 and calculated_hash.lower() != self.expected_sha256.lower():
                raise VaultError(
                    f"Naruszenie nienaruszalności konfiguracji! "
                    f"Oczekiwano: {self.expected_sha256}, Otrzymano: {calculated_hash}"
                )

            config_data = json.loads(raw_data.decode("utf-8"))
            if not isinstance(config_data, dict):
                raise VaultError("Format pliku konfiguracyjnego jest nieprawidłowy (wymagany słownik JSON).")

            logger.info("Konfiguracja węzła została pomyślnie załadowana i zweryfikowana kryptograficznie.")
            return config_data

        except Exception as e:
            logger.error(f"Błąd podczas ładowania konfiguracji z sejfu: {e}")
            raise VaultError(f"Nie udało się załadować konfiguracji: {e}") from e

    def get_secure_setting(self, key: str, default: Any = None) -> Any:
        config = self.load_and_verify_config()
        return config.get(key, default)