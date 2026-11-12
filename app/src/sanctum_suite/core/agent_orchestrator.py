#!/usr/bin/env python3

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (AgentOrchestrator): %(message)s"
)
logger = logging.getLogger("AgentOrchestrator")

class OrchestratorError(Exception):
    pass

class AutonomousAgentOrchestrator:

    def __init__(self, workspace_dir: Path = Path("/var/lib/sanctum")):
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.workspace_dir / "orchestrator_state.json"
        self.operator_override_flag = self.workspace_dir / "operator_override.lock"
        logger.info(f"Inicjalizacja AutonomousAgentOrchestrator w katalogu: {self.workspace_dir}")

    def is_operator_override_active(self) -> bool:
        is_active = self.operator_override_flag.exists()
        if is_active:
            logger.warning("Wykryto aktywną blokadę operatora (Operator Override). Autonomiczne akcje krytyczne wstrzymane.")
        return is_active

    def run_autonomous_cycle(self, telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Uruchomiono autonomiczny cykl decyzyjny agentów systemowych w repozytorium...")

        # Sprawdzenie nadzoru operatora
        operator_locked = self.is_operator_override_active()

        # Ocena stanu przez wbudowane moduły autonomiczne
        incidents = telemetry_data.get("high_severity_incidents_found", 0)
        anomalies = telemetry_data.get("flagged_anomalies_count", 0)

        action_taken = "MONITOR_ONLY"
        requires_attention = False

        if incidents > 0 or anomalies > 0:
            if operator_locked:
                action_taken = "CONTAINMENT_QUEUED_FOR_OPERATOR"
                requires_attention = True
                logger.warning("Wykryto zagrożenie, ale akcja została wstrzymana ze względu na blokadę operatora.")
            else:
                action_taken = "AUTONOMOUS_CONTAINMENT_TRIGGERED"
                requires_attention = True
                logger.warning("Autonomiczny agent podjął natychmiastową akcję obronną bez interwencji operatora.")
        else:
            logger.info("System w stanie stabilnym. Agenci prowadzą ciągły nasłuch w tle.")

        state_report = {
            "orchestrator_run_id": f"ORCH-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "operator_override_active": operator_locked,
            "system_status": "stable" if not requires_attention else "attention_required",
            "autonomous_action": action_taken,
            "metrics_evaluated": {
                "incidents": incidents,
                "anomalies": anomalies
            }
        }

        try:
            self.state_file.write_text(json.dumps(state_report, indent=2, sort_keys=True), encoding="utf-8")
        except Exception as e:
            logger.error(f"Nie udało się zapisać stanu orkiestratora: {e}")

        return state_report