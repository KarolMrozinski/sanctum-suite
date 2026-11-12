#!/usr/bin/env python3

import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from sanctum_suite.core.secure_asset_loader import SecureAssetLoader
from sanctum_suite.core.apt_indicator_engine import APTIndicatorEngine
from sanctum_suite.core.ai_model_loader import SecureAIModelManager
from sanctum_suite.core.telemetry_buffer import TelemetryBuffer
from sanctum_suite.core.manifest_verifier import ManifestVerifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (SystemOrchestrator): %(message)s"
)
logger = logging.getLogger("SystemOrchestrator")

class OrchestrationError(Exception):
    pass

class SystemOrchestrator:

    def __init__(self, root_dir: Path = Path("/var/lib/sanctum")):
        self.root_dir = Path(root_dir)
        self.asset_loader = SecureAssetLoader(self.root_dir)
        self.apt_engine = APTIndicatorEngine(self.root_dir / "threat_intel" / "threat_intel_feed.db")
        self.ai_manager = SecureAIModelManager(self.root_dir / "models")
        self.telemetry = TelemetryBuffer(self.root_dir / "telemetry")
        self.verifier = ManifestVerifier(self.root_dir / "bundles")
        
        logger.info(f"Inicjalizacja SystemOrchestrator z katalogiem głównym: {self.root_dir}")

    def run_system_preflight(self) -> Dict[str, Any]:
        logger.info("Rozpoczęto pełny audyt wstępny (pre-flight check) środowiska systemowego.")
        
        status_report = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "root_directory": str(self.root_dir),
            "checks": {},
            "overall_status": "healthy"
        }

        try:
            # 1. Sprawdzenie katalogów bazowych
            threat_db = self.root_dir / "threat_intel" / "threat_intel_feed.db"
            ai_model = self.root_dir / "models" / "local_anomaly_detector.onnx"
            
            status_report["checks"]["threat_intel_db_exists"] = threat_db.exists()
            status_report["checks"]["ai_model_exists"] = ai_model.exists()

            if not threat_db.exists() or not ai_model.exists():
                status_report["overall_status"] = "degraded"
                logger.warning("Wykryto brak kluczowych ciężkich zasobów w systemie.")

            # Rejestracja zdarzenia w buforze telemetrii
            self.telemetry.push_event("SYSTEM_PREFLIGHT_EXECUTED", status_report)
            logger.info("Pre-flight check zakończony pomyślnie.")
            return status_report

        except Exception as e:
            logger.error(f"Krytyczny błąd podczas pre-flight check: {e}")
            raise OrchestrationError(f"System pre-flight failed: {e}") from e

    def execute_threat_analysis_pipeline(self, indicator_hashes: List[str]) -> Dict[str, Any]:
        logger.info(f"Uruchomiono potok analizy zagrożeń dla {len(indicator_hashes)} wskaźników.")
        
        try:
            results = self.apt_engine.batch_query(indicator_hashes)
            
            analysis_summary = {
                "analyzed_count": len(indicator_hashes),
                "matches_found": sum(1 for r in results if r.get("matched", False)),
                "results": results,
                "executed_at": datetime.utcnow().isoformat() + "Z"
            }

            self.telemetry.push_event("THREAT_ANALYSIS_COMPLETED", analysis_summary)
            return analysis_summary

        except Exception as e:
            logger.error(f"Błąd wykonania potoku analizy zagrożeń: {e}")
            raise OrchestrationError(f"Threat analysis pipeline failed: {e}") from e

    def shutdown(self) -> None:
        logger.info("Rozpoczęto procedurę bezpiecznego zamknięcia SystemOrchestrator.")
        try:
            self.telemetry.flush_to_disk()
            logger.info("Zrzut bufora telemetrii zakończony. System gotowy do zamknięcia.")
        except Exception as e:
            logger.error(f"Błąd podczas zamykania orkiestratora: {e}")