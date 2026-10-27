#!/usr/bin/env python3

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (ExfiltrationGuard): %(message)s"
)
logger = logging.getLogger("ExfiltrationGuard")

class ExfiltrationGuardError(Exception):
    pass

class AdvancedExfiltrationGuard:

    def __init__(self, telemetry_log_path: Path = Path("/var/lib/sanctum/telemetry/events.jsonl")):
        self.telemetry_log_path = Path(telemetry_log_path)
        logger.info(f"Inicjalizacja AdvancedExfiltrationGuard z dziennikiem: {self.telemetry_log_path}")

    def analyze_transfer_patterns(self, transfer_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        logger.info(f"Rozpoczęto analizę behawioralną dla {len(transfer_events)} operacji transferu danych.")
        
        flagged_transfers = []
        threshold_bytes = 50 * 1024 * 1024  # Próg 50 MB dla podejrzanie dużych transferów lokalnych

        for event in transfer_events:
            transfer_size = event.get("size_bytes", 0)
            destination = event.get("destination", "local")
            
            if transfer_size > threshold_bytes:
                flagged_entry = {
                    "event_id": event.get("event_id", "UNKNOWN"),
                    "size_bytes": transfer_size,
                    "destination": destination,
                    "risk_level": "HIGH",
                    "reason": "Przekroczono bezpieczny próg objętości transferu w środowisku odizolowanym.",
                    "detected_at": datetime.utcnow().isoformat() + "Z"
                }
                flagged_transfers.append(flagged_entry)
                logger.warning(f"Wykryto potencjalną eksfiltrację danych! Rozmiar: {transfer_size} bajtów -> {destination}")

        report = {
            "analysis_id": f"EXFIL-GUARD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "total_transfers_analyzed": len(transfer_events),
            "flagged_anomalies_count": len(flagged_transfers),
            "anomalies": flagged_transfers,
            "status": "secure" if len(flagged_transfers) == 0 else "threat_detected",
            "evaluated_at": datetime.utcnow().isoformat() + "Z"
        }

        logger.info(f"Analiza eksfiltracji zakończona. Status: {report['status'].upper()}")
        return report