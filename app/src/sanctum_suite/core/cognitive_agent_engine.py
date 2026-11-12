#!/usr/bin/env python3
# ==============================================================================
# Sanctum Suite: Enterprise Cognitive Autonomous Agent Engine
# Wysokowydajny silnik agentowy do analizy zagrożeń w środowiskach Air-Gapped
# ==============================================================================

import os
import sys
import json
import logging
import hashlib
import threading
import queue
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

# Konfiguracja rygorystycznego logowania bezpieczeństwa
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] (CognitiveAgentEngine): %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("CognitiveAgentEngine")


class AgentEngineError(Exception):
    """Bazowy wyjątek dla krytycznych błędów silnika agentowego."""
    pass


class UnauthorizedActionException(AgentEngineError):
    """Wyjątek rzucany w przypadku próby naruszenia polityki bezpieczeństwa Air-Gap."""
    pass


class TelemetryEventRecord:
    """Reprezentuje pojedyncze zdarzenie telemetrii systemowej lub sieciowej."""
    
    def __init__(self, event_type: str, source_ip: str, destination_ip: str, payload_size: int, metadata: Dict[str, Any]):
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.event_id = f"EVT-SANCTUM-{hashlib.sha256(f'{self.timestamp}-{source_ip}-{destination_ip}'.encode()).hexdigest()[:16].upper()}"
        self.event_type = event_type
        self.source_ip = source_ip
        self.destination_ip = destination_ip
        self.payload_size = payload_size
        self.metadata = metadata
        self.is_processed = False
        self.risk_score = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "source_ip": self.source_ip,
            "destination_ip": self.destination_ip,
            "payload_size": self.payload_size,
            "metadata": self.metadata,
            "risk_score": self.risk_score,
            "is_processed": self.is_processed
        }


class CognitiveAgentEngine:
    """
    Główny silnik autonomiczny koordynujący analizę anomalii, wykrywanie wektorów ataków
    oraz automatyczną generację reguł zaradczych w odizolowanym środowisku.
    """

    def __init__(self, workspace_dir: str = "/var/lib/sanctum/cognitive", strict_mode: bool = True):
        self.workspace_path = Path(workspace_dir)
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        self.strict_mode = strict_mode
        
        self.event_queue: queue.Queue = queue.Queue(maxsize=10000)
        self.active_threats: Dict[str, Dict[str, Any]] = {}
        self.mitigation_rules: List[Dict[str, Any]] = []
        
        self._shutdown_event = threading.Event()
        self._worker_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self._worker_thread.start()
        
        logger.info(f"Initialized CognitiveAgentEngine. Workspace: {self.workspace_path}, Strict Air-Gap: {self.strict_mode}")

    def ingest_telemetry(self, event_type: str, source_ip: str, destination_ip: str, payload_size: int, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Przyjmuje nową telemetrię i umieszcza w kolejce przetwarzania współbieżnego."""
        if metadata is None:
            metadata = {}
            
        record = TelemetryEventRecord(event_type, source_ip, destination_ip, payload_size, metadata)
        try:
            self.event_queue.put_nowait(record)
            logger.debug(f"Ingested telemetry event: {record.event_id} [{event_type}]")
            return record.event_id
        except queue.Full:
            logger.error("CRITICAL: Telemetry event queue is full! Dropping packet to prevent memory exhaustion.")
            raise AgentEngineError("Telemetry queue overflow")

    def _processing_loop(self) -> None:
        """Wewnętrzna pętla robocza wątku analitycznego w tle."""
        logger.info("Cognitive background telemetry processing loop started.")
        while not self._shutdown_event.is_set():
            try:
                record: TelemetryEventRecord = self.event_queue.get(timeout=1.0)
                self._analyze_event_semantics(record)
                self.event_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error during cognitive event analysis: {str(e)}")

    def _analyze_event_semantics(self, record: TelemetryEventRecord) -> None:
        """Analizuje semantykę zdarzenia pod kątem naruszeń polityki i anomalii behawioralnych."""
        risk = 0.0
        notes = []

        # Weryfikacja reguł Air-Gapped dla adresów IP
        if self.strict_mode:
            if not self._is_private_or_loopback(record.source_ip):
                risk += 0.85
                notes.append(f"External non-private source IP detected: {record.source_ip}")

            if not self._is_private_or_loopback(record.destination_ip):
                risk += 0.85
                notes.append(f"External non-private destination IP detected: {record.destination_ip}")

        # Analiza rozmiaru ładunku pod kątem bufora / overflow
        if record.payload_size > 65535:
            risk += 0.60
            notes.append(f"Excessive payload size ({record.payload_size} bytes) indicates potential buffer overflow.")

        record.risk_score = min(risk, 1.0)
        record.is_processed = True

        if record.risk_score >= 0.75:
            self._handle_high_severity_threat(record, notes)
        else:
            logger.debug(f"Event {record.event_id} processed safely. Risk score: {record.risk_score}")

    def _is_private_or_loopback(self, ip_address: str) -> bool:
        """Sprawdza, czy adres IP należy do przestrzeni prywatnej lub lokalnej pętli zwrotnej."""
        if ip_address.startswith("10.") or ip_address.startswith("127.") or ip_address.startswith("192.168."):
            return True
        if ip_address.startswith("172."):
            try:
                second_octet = int(ip_address.split(".")[1])
                if 16 <= second_octet <= 31:
                    return True
            except (IndexError, ValueError):
                pass
        return False

    def _handle_high_severity_threat(self, record: TelemetryEventRecord, notes: List[str]) -> None:
        """Obsługuje wykryte zagrożenia o wysokim priorytetem, generując automatyczne reguły blokady."""
        threat_id = f"THREAT-{record.event_id}"
        threat_data = {
            "threat_id": threat_id,
            "detected_at": datetime.now(timezone.utc).isoformat(),
            "source_event": record.to_dict(),
            "indicators": notes,
            "status": "MITIGATED_AUTOMATICALLY"
        }
        
        self.active_threats[threat_id] = threat_data
        logger.warning(f"HIGH SEVERITY THREAT DETECTED AND MITIGATED: {threat_id}. Indicators: {notes}")
        
        # Synteza reguły blokady
        self._synthesize_countermeasure_rule(threat_id, record.source_ip)

    def _synthesize_countermeasure_rule(self, threat_id: str, offending_ip: str) -> None:
        """Automatycznie syntetyzuje regułę blokady iptables / eBPF dla złośliwego źródła."""
        rule_content = f"""# Sanctum Suite Automated Countermeasure Rule
# Threat ID: {threat_id}
# Action: DROP traffic from offending host
iptables -A INPUT -s {offending_ip} -j DROP
ip6tables -A INPUT -s {offending_ip} -j DROP
"""
        rule_filename = self.workspace_path / f"block-{threat_id}.sh"
        rule_filename.write_text(rule_content, encoding="utf-8")
        
        rule_metadata = {
            "threat_id": threat_id,
            "offending_ip": offending_ip,
            "rule_path": str(rule_filename),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self.mitigation_rules.append(rule_metadata)
        logger.info(f"Countermeasure rule successfully synthesized and saved to {rule_filename}")

    def get_engine_status(self) -> Dict[str, Any]:
        """Zwraca pełny raport ze stanu pracy silnika agentowego."""
        return {
            "workspace": str(self.workspace_path),
            "strict_mode": self.strict_mode,
            "queued_events": self.event_queue.qsize(),
            "active_threats_count": len(self.active_threats),
            "synthesized_rules_count": len(self.mitigation_rules),
            "engine_status": "RUNNING"
        }

    def shutdown(self) -> None:
        """Bezpiecznie wyłącza silnik agentowy i wątki w tle."""
        logger.info("Shutting down CognitiveAgentEngine...")
        self._shutdown_event.set()
        self._worker_thread.join(timeout=3.0)
        logger.info("CognitiveAgentEngine successfully shut down.")