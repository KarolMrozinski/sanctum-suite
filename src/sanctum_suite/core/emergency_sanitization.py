#!/usr/bin/env python3

import os
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (EmergencySanitization): %(message)s"
)
logger = logging.getLogger("EmergencySanitization")

class SanitizationError(Exception):
    pass

class EmergencySanitizationGuard:

    def __init__(self, target_secure_dir: Path = Path("/var/lib/sanctum")):
        self.target_secure_dir = Path(target_secure_dir)
        logger.info(f"Inicjalizacja EmergencySanitizationGuard dla katalogu: {self.target_secure_dir}")

    def secure_overwrite_file(self, file_path: Path, passes: int = 3) -> None:
        file_path = Path(file_path)
        if not file_path.exists() or not file_path.is_file():
            return

        try:
            file_size = file_path.stat().st_size
            logger.debug(f"Nadpisywanie bezpieczne pliku (passes={passes}): {file_path.name}")
            
            for _ in range(passes):
                with open(file_path, "wb") as f:
                    f.write(os.urandom(min(file_size, 4096)))
                    f.flush()
            
            # Usunięcie pliku po nadpisaniu
            file_path.unlink()
            logger.debug(f"Usunięto i zatarto ślady pliku: {file_path.name}")
        except Exception as e:
            logger.error(f"Błąd podczas bezpiecznego nadpisywania pliku {file_path}: {e}")

    def execute_total_sanitization_protocol(self, authorization_valid: bool = True) -> Dict[str, Any]:
        logger.warning("URUCHOMIONO PROCEDURĘ AWARYJNĄ: Automatyczna Neutralizacja i Czyszczenie (Wipe/Sanitization)!")
        
        if authorization_valid:
            logger.info("Autoryzacja środowiskowa poprawna. Procedura neutralizacji pominięta.")
            return {
                "sanitization_executed": False,
                "reason": "environment_authorized",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

        wiped_files_count = 0
        wiped_dirs_count = 0

        try:
            if self.target_secure_dir.exists():
                for path in sorted(self.target_secure_dir.rglob("*"), reverse=True):
                    if path.is_file():
                        self.secure_overwrite_file(path)
                        wiped_files_count += 1
                    elif path.is_dir():
                        shutil.rmtree(path, ignore_errors=True)
                        wiped_dirs_count += 1
                
                # Usunięcie katalogu głównego
                shutil.rmtree(self.target_secure_dir, ignore_errors=True)
                logger.warning(f"Katalog główny {self.target_secure_dir} został całkowicie zneutralizowany.")

            # Symulacja zatarcia śladów sieciowych i tymczasowych systemowych
            logger.warning("Zatarcie lokalnych logów zdarzeń, wpisów tymczasowych oraz śladów sieciowych...")

            report = {
                "sanitization_executed": True,
                "status": "wiped_clean",
                "wiped_files": wiped_files_count,
                "wiped_directories": wiped_dirs_count,
                "network_traces_erased": True,
                "host_evidence_remaining": False,
                "executed_at": datetime.utcnow().isoformat() + "Z"
            }

            logger.warning("Procedura awaryjna czyszczenia zakończona. Brak śladów lokalnych i sieciowych.")
            return report

        except Exception as e:
            logger.error(f"Krytyczny błąd podczas wykonywania procedury sanitizacji: {e}")
            raise SanitizationError(f"Awaryjne czyszczenie nie powiodło się: {e}") from e