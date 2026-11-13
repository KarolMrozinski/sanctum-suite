#!/usr/bin/env python3

import os
import shutil
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (ResourceWatcher): %(message)s"
)
logger = logging.getLogger("ResourceWatcher")

class WatcherError(Exception):
    pass

class SystemResourceWatcher:

    def __init__(self, target_path: Path = Path("/var/lib/sanctum")):
        self.target_path = Path(target_path)
        logger.info(f"Inicjalizacja SystemResourceWatcher dla ścieżki: {self.target_path}")

    def check_disk_space(self) -> Dict[str, Any]:
        if not self.target_path.exists():
            # Fallback dla katalogu głównego jeśli ścieżka systemowa nie istnieje w trybie testowym
            check_target = Path("/")
        else:
            check_target = self.target_path

        try:
            total, used, free = shutil.disk_usage(check_target)
            total_mb = total / (1024 * 1024)
            used_mb = used / (1024 * 1024)
            free_mb = free / (1024 * 1024)
            percent_used = round((used / total) * 100, 2)

            metrics = {
                "path": str(check_target),
                "total_mb": round(total_mb, 2),
                "used_mb": round(used_mb, 2),
                "free_mb": round(free_mb, 2),
                "percent_used": percent_used,
                "status": "warning" if percent_used > 90 else "healthy"
            }
            logger.info(f"Sprawdzenie przestrzeni dyskowej: {percent_used}% zajęte.")
            return metrics
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania przestrzeni dyskowej: {e}")
            raise WatcherError(f"Nie udało się pobrać metryk dysku: {e}") from e

    def generate_health_snapshot(self) -> Dict[str, Any]:
        logger.info("Generowanie migawki stanu zasobów systemowych...")
        disk_metrics = self.check_disk_space()

        snapshot = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "disk": disk_metrics,
            "overall_status": disk_metrics.get("status", "healthy")
        }
        logger.info("Migawka stanu zasobów wygenerowana pomyślnie.")
        return snapshot