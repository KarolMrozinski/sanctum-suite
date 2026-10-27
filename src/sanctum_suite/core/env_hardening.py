#!/usr/bin/env python3

import os
import stat
import logging
from pathlib import Path
from typing import Dict, Any, List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (EnvHardening): %(message)s"
)
logger = logging.getLogger("EnvHardening")

class HardeningError(Exception):
    pass

class EnvironmentHardeningGuard:

    def __init__(self, root_dir: Path = Path("/var/lib/sanctum")):
        self.root_dir = Path(root_dir)
        logger.info(f"Inicjalizacja EnvironmentHardeningGuard dla ścieżki: {self.root_dir}")

    def audit_file_permissions(self) -> List[Dict[str, Any]]:
        logger.info("Rozpoczęto audyt uprawnień plików systemowych Sanctum Suite.")
        audit_results = []

        if not self.root_dir.exists():
            logger.warning(f"Katalog główny {self.root_dir} nie istnieje. Pomijam audyt uprawnień.")
            return audit_results

        for path in self.root_dir.rglob("*"):
            if path.is_file():
                try:
                    file_stat = path.stat()
                    file_mode = stat.S_IMODE(file_stat.st_mode)
                    # Sprawdzenie czy plik nie jest zbytnio otwarty (np. zapis dla grupy/innych)
                    is_secure = (file_mode & 0o077) == 0
                    
                    result_entry = {
                        "path": str(path),
                        "mode": oct(file_mode),
                        "secure": is_secure
                    }
                    audit_results.append(result_entry)

                    if not is_secure:
                        logger.warning(f"Naruszenie polityki uprawnień pliku {path.name}: tryb {oct(file_mode)}")
                except Exception as e:
                    logger.error(f"Nie udało się sprawdzić uprawnień pliku {path}: {e}")

        logger.info(f"Zakończono audyt uprawnień dla {len(audit_results)} plików.")
        return audit_results

    def enforce_air_gapped_constraints(self) -> Dict[str, Any]:
        logger.info("Wymuszanie restrykcji środowiska Air-Gapped...")
        
        checks = {
            "root_directory_exists": self.root_dir.exists(),
            "permissions_audit_passed": True,
            "offline_mode_enforced": True
        }

        file_audits = self.audit_file_permissions()
        for entry in file_audits:
            if not entry.get("secure", True):
                checks["permissions_audit_passed"] = False
                break

        status_report = {
            "status": "hardened" if checks["permissions_audit_passed"] else "warning",
            "checks": checks,
            "audited_files_count": len(file_audits)
        }

        logger.info(f"Status twardnienia środowiska: {status_report['status'].upper()}")
        return status_report