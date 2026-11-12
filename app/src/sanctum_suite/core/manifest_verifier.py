#!/usr/bin/env python3

import os
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (ManifestVerifier): %(message)s"
)
logger = logging.getLogger("ManifestVerifier")

class VerificationError(Exception):
    pass

class ManifestVerifier:

    def __init__(self, bundle_dir: Path = Path("/var/lib/sanctum/bundles")):
        self.bundle_dir = Path(bundle_dir)
        logger.info(f"Inicjalizacja ManifestVerifier dla katalogu paczek: {self.bundle_dir}")

    def verify_manifest_file(self, manifest_path: Path, expected_root_hash: Optional[str] = None) -> Dict[str, Any]:
        manifest_path = Path(manifest_path)
        if not manifest_path.exists():
            raise FileNotFoundError(f"Plik manifestu nie istnieje: {manifest_path}")

        logger.info(f"Rozpoczęto weryfikację struktury manifestu: {manifest_path.name}")
        
        try:
            raw_content = manifest_path.read_bytes()
            actual_hash = hashlib.sha256(raw_content).hexdigest()

            if expected_root_hash and actual_hash.lower() != expected_root_hash.lower():
                raise VerificationError(
                    f"Krytyczny błąd nienaruszalności manifestu! "
                    f"Oczekiwano: {expected_root_hash}, Otrzymano: {actual_hash}"
                )

            manifest_data = json.loads(raw_content.decode("utf-8"))
            
            artifacts: List[Dict[str, Any]] = manifest_data.get("artifacts", [])
            verified_artifacts = []
            
            for art in artifacts:
                art_name = art.get("name", "unknown")
                art_path = self.bundle_dir / art.get("filename", "")
                expected_art_hash = art.get("sha256", "")

                if not art_path.exists():
                    logger.warning(f"Artefakt z manifestu nie został odnaleziony na dysku: {art_path}")
                    verified_artifacts.append({
                        "name": art_name,
                        "status": "missing",
                        "path": str(art_path)
                    })
                    continue

                art_hash = hashlib.sha256(art_path.read_bytes()).hexdigest()
                is_valid = (art_hash.lower() == expected_art_hash.lower())
                
                if not is_valid:
                    raise VerificationError(
                        f"Naruszenie sumy kontrolnej dla artefaktu {art_name}! "
                        f"Oczekiwano: {expected_art_hash}, Otrzymano: {art_hash}"
                    )

                verified_artifacts.append({
                    "name": art_name,
                    "status": "verified",
                    "sha256": art_hash
                })

            result = {
                "manifest_file": manifest_path.name,
                "manifest_sha256": actual_hash,
                "status": "success",
                "verified_at": datetime.utcnow().isoformat() + "Z",
                "artifacts_summary": verified_artifacts
            }
            
            logger.info(f"Manifest {manifest_path.name} zweryfikowany pomyślnie.")
            return result

        except Exception as e:
            logger.error(f"Błąd weryfikacji manifestu: {e}")
            raise VerificationError(f"Weryfikacja manifestu nie powiodła się: {e}") from e