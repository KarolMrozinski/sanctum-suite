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
    format="%(asctime)s [%(levelname)s] (TelemetryBuffer): %(message)s"
)
logger = logging.getLogger("TelemetryBuffer")

class BufferError(Exception):
    pass

class TelemetryBuffer:

    def __init__(self, buffer_dir: Path = Path("/var/lib/sanctum/telemetry"), max_buffer_size: int = 1000):
        self.buffer_dir = Path(buffer_dir)
        self.max_buffer_size = max_buffer_size
        self._memory_buffer: List[Dict[str, Any]] = []
        self.buffer_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Inicjalizacja TelemetryBuffer w katalogu: {self.buffer_dir}")

    def push_event(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = datetime.utcnow().isoformat() + "Z"
        event_record = {
            "timestamp": timestamp,
            "event_type": event_type,
            "payload": payload
        }
        
        raw_data = json.dumps(event_record, sort_keys=True).encode("utf-8")
        event_hash = hashlib.sha256(raw_data).hexdigest()
        event_record["record_hash"] = event_hash

        self._memory_buffer.append(event_record)
        logger.debug(f"Zarejestrowano zdarzenie telemetrii: {event_type} [Hash: {event_hash[:12]}...]")

        if len(self._memory_buffer) >= self.max_buffer_size:
            self.flush_to_disk()

        return event_record

    def flush_to_disk(self) -> Path:
        if not self._memory_buffer:
            logger.debug("Bufor pamięci jest pusty. Pomijam zrzut na dysk.")
            return None

        batch_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        file_path = self.buffer_dir / f"telemetry_batch_{batch_id}.json"

        batch_data = {
            "batch_id": batch_id,
            "flushed_at": datetime.utcnow().isoformat() + "Z",
            "record_count": len(self._memory_buffer),
            "events": self._memory_buffer
        }

        try:
            serialized = json.dumps(batch_data, indent=4, sort_keys=True)
            file_path.write_text(serialized, encoding="utf-8")
            logger.info(f"Zrzucono {len(self._memory_buffer)} rekordów telemetrii do pliku: {file_path}")
            
            # Czyszczenie bufora pamięci po pomyślnym zrzucie
            self._memory_buffer.clear()
            return file_path
        except Exception as e:
            logger.error(f"Błąd podczas zrzucania bufora telemetrii na dysk: {e}")
            raise BufferError(f"Nie udało się zapisać bufora telemetrii: {e}") from e

    def get_buffered_count(self) -> int:
        return len(self._memory_buffer)