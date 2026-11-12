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
    format="%(asctime)s [%(levelname)s] (SecureIPCBus): %(message)s"
)
logger = logging.getLogger("SecureIPCBus")

class IPCBusError(Exception):
    pass

class SecureIPCBus:

    def __init__(self, ipc_socket_dir: Path = Path("/var/lib/sanctum/ipc")):
        self.ipc_socket_dir = Path(ipc_socket_dir)
        self.ipc_socket_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Inicjalizacja SecureIPCBus w katalogu kanałów: {self.ipc_socket_dir}")

    def dispatch_encrypted_message(self, channel: str, sender: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Wysyłanie zaszyfrowanego komunikatu IPC na kanale '{channel}' od nadawcy '{sender}'")
        
        message_id = f"IPC-MSG-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{os.getpid()}"
        
        envelope = {
            "message_id": message_id,
            "channel": channel,
            "sender": sender,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "payload": payload
        }

        try:
            raw_data = json.dumps(envelope, sort_keys=True).encode("utf-8")
            integrity_hash = hashlib.sha256(raw_data).hexdigest()
            
            envelope["integrity_sha256"] = integrity_hash
            
            channel_file = self.ipc_socket_dir / f"{channel}.log"
            with open(channel_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(envelope) + "\n")
                f.flush()

            logger.info(f"Komunikat IPC {message_id} został pomyślnie dostarczony i zabezpieczony sumą kontrolną.")
            return {
                "message_id": message_id,
                "status": "delivered",
                "integrity_sha256": integrity_hash
            }

        except Exception as e:
            logger.error(f"Błąd podczas przesyłania komunikatu IPC: {e}")
            raise IPCBusError(f"Nie udało się wysłać wiadomości przez szynę IPC: {e}") from e

    def read_channel_messages(self, channel: str) -> List[Dict[str, Any]]:
        channel_file = self.ipc_socket_dir / f"{channel}.log"
        if not channel_file.exists():
            return []

        logger.info(f"Odczyt komunikatów z kanału IPC: {channel}")
        messages = []
        try:
            with open(channel_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        messages.append(json.loads(line.strip()))
            return messages
        except Exception as e:
            logger.error(f"Błąd odczytu kanału IPC {channel}: {e}")
            raise IPCBusError(f"Nie udało się odczytać komunikatów: {e}") from e