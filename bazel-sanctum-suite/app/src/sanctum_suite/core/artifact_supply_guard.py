#!/usr/bin/env python3

import os
import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (ArtifactSupplyGuard): %(message)s"
)
logger = logging.getLogger("ArtifactSupplyGuard")

class SupplyChainError(Exception):
    pass

class ArtifactSupplyGuard:

    def __init__(self, artifacts_dir: Path = Path("/var/lib/sanctum/artifacts")):
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Inicjalizacja ArtifactSupplyGuard w katalogu: {self.artifacts_dir}")

    def verify_artifact_manifest(self, manifest_filename: str, expected_sha256: str) -> Dict[str, Any]:
        manifest_path = self.artifacts_dir / manifest_filename
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest artefaktu nie istnieje: {manifest_path}")

        logger.info(f"Weryfikacja sumy kontrolnej artefaktu oprogramowania: {manifest_filename}")

        try:
            raw_data = manifest_path.read_bytes()
            calculated_hash = hashlib.sha256(raw_data).hexdigest()

            is_valid = (calculated_hash.lower() == expected_sha256.lower())
            if not is_valid:
                logger.error(
                    f"Krytyczny błąd łańcucha dostaw: Naruszenie sumy kontrolnej artefaktu {manifest_filename}! "
                    f"Oczekiwano: {expected_sha256}, Otrzymano: {calculated_hash}"
                )
            else:
                logger.info(f"Artefakt {manifest_filename} zweryfikowany pomyślnie (SHA-256 OK).")

            return {
                "manifest_filename": manifest_filename,
                "expected_sha256": expected_sha256,
                "calculated_sha256": calculated_hash,
                "integrity_valid": is_valid,
                "verified_at": datetime.utcnow().isoformat() + "Z"
            }

        except Exception as e:
            logger.error(f"Błąd podczas weryfikacji artefaktu: {e}")
            raise SupplyChainError(f"Weryfikacja łańcucha dostaw nie powiodła się: {e}") from e