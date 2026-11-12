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
    format="%(asctime)s [%(levelname)s] (ForensicExporter): %(message)s"
)
logger = logging.getLogger("ForensicExporter")

class ExporterError(Exception):
    pass

class ForensicExporter:

    def __init__(self, export_dir: Path = Path("/var/lib/sanctum/exports")):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Inicjalizacja ForensicExporter z katalogiem eksportu: {self.export_dir}")

    def generate_stix_bundle(self, findings: List[Dict[str, Any]], session_metadata: Dict[str, Any]) -> Path:
        logger.info("Generowanie kryptograficznego pakietu raportowego STIX 2.1 / Forensics...")
        
        bundle_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        export_filename = self.export_dir / f"sanctum_forensic_bundle_{bundle_id}.json"

        stix_bundle = {
            "type": "bundle",
            "id": f"bundle--{bundle_id}",
            "spec_version": "2.1",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "generator": "Sanctum-Suite-Forensic-Exporter",
            "session_metadata": session_metadata,
            "objects": findings
        }

        try:
            raw_data = json.dumps(stix_bundle, indent=4, sort_keys=True).encode("utf-8")
            bundle_hash = hashlib.sha256(raw_data).hexdigest()
            
            stix_bundle["integrity_sha256"] = bundle_hash
            final_serialized = json.dumps(stix_bundle, indent=4, sort_keys=True)
            
            export_filename.write_text(final_serialized, encoding="utf-8")
            logger.info(f"Pakiet forensyczny STIX został wygenerowany i zabezpieczony: {export_filename}")
            logger.info(f"Suma kontrolna SHA-256 raportu: {bundle_hash}")
            
            return export_filename

        except Exception as e:
            logger.error(f"Błąd podczas generowania pakietu forensycznego: {e}")
            raise ExporterError(f"Nie udało się wyeksportować raportu forensycznego: {e}") from e