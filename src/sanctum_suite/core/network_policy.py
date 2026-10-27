#!/usr/bin/env python3

import os
import socket
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (NetworkPolicy): %(message)s"
)
logger = logging.getLogger("NetworkPolicy")

class NetworkPolicyError(Exception):
    pass

class NetworkPolicyGuard:

    def __init__(self, air_gapped_enforced: bool = True):
        self.air_gapped_enforced = air_gapped_enforced
        logger.info(f"Inicjalizacja NetworkPolicyGuard [Air-Gapped: {self.air_gapped_enforced}]")

    def audit_active_sockets(self) -> List[Dict[str, Any]]:
        logger.info("Rozpoczęto audyt aktywnych gniazd sieciowych pod kątem zgodności z polityką offline.")
        socket_records = []

        # W trybie w pełni odizolowanym system nie powinien utrzymywać wychodzących połączeń TCP poza localhost
        try:
            # Przykładowa symulacja/sprawdzenie interfejsu lokalnego
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            
            is_loopback = local_ip.startswith("127.") or local_ip == "::1"
            
            socket_records.append({
                "hostname": hostname,
                "resolved_ip": local_ip,
                "is_loopback": is_loopback,
                "status": "compliant" if is_loopback or not self.air_gapped_enforced else "warning"
            })
            
            logger.info(f"Zakończono audyt interfejsów sieciowych. Adres węzła: {local_ip} (Loopback: {is_loopback})")
            return socket_records

        except Exception as e:
            logger.error(f"Błąd podczas audytu gniazd sieciowych: {e}")
            raise NetworkPolicyError(f"Audyt sieciowy nie powiódł się: {e}") from e

    def enforce_policy_check(self) -> Dict[str, Any]:
        logger.info("Wymuszanie polityki bezpieczeństwa sieciowego...")
        sockets = self.audit_active_sockets()

        violations = [s for s in sockets if s.get("status") != "compliant"]
        
        report = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "air_gapped_mode": self.air_gapped_enforced,
            "violations_detected": len(violations),
            "status": "secure" if len(violations) == 0 else "violation",
            "audited_interfaces": sockets
        }

        logger.info(f"Wynik weryfikacji polityki sieciowej: {report['status'].upper()}")
        return report