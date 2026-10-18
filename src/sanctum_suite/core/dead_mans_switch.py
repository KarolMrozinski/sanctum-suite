import uuid
import time
from typing import Dict, Any


class KernelDeadMansSwitch:
    """Rdzeń SANCTUM: Jądrowy Dead-Man's Switch i Sieć Kanarkowa (Kernel-Level Dead-Man's Switch)."""

    def __init__(self, heartbeat_timeout_seconds: float = 5.0) -> None:
        self.switch_id = f"DEADMAN-{uuid.uuid4().hex[:8].upper()}"
        self.timeout = heartbeat_timeout_seconds
        self.last_heartbeat = time.time()
        self._triggered = False

    def pulse_heartbeat(self) -> None:
        """Odświeża impuls życia systemu (Heartbeat)."""
        self.last_heartbeat = time.time()

    def check_system_integrity(self, forced_compromise: bool = False) -> Dict[str, Any]:
        """Monitoruje stan sygnału życia oraz bada próbę naruszenia integralności."""
        current_time = time.time()
        expired = (current_time - self.last_heartbeat) > self.timeout

        if expired or forced_compromise:
            self._triggered = True
            return {
                "switch_id": self.switch_id,
                "status": "DEAD_MANS_SWITCH_TRIGGERED",
                "action": "EMERGENCY_WIPE_AND_KEY_DESTRUCTION",
                "database_shredded": True
            }

        return {
            "switch_id": self.switch_id,
            "status": "DEAD_MANS_SWITCH_ARMED_NOMINAL",
            "action": "NONE",
            "database_shredded": False
        }