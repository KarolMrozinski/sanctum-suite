#!/usr/bin/env python3

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (AutonomousAIAgent): %(message)s"
)
logger = logging.getLogger("AutonomousAIAgent")

class AIAgentError(Exception):
    pass

class AutonomousAIAgent:

    def __init__(self, agent_state_dir: Path = Path("/var/lib/sanctum/ai_agent")):
        self.agent_state_dir = Path(agent_state_dir)
        self.agent_state_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Inicjalizacja AutonomousAIAgent w katalogu stanu: {self.agent_state_dir}")

    def evaluate_threat_context(self, telemetry_summary: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Autonomiczny Agent AI analizuje bieżący kontekst zagrożeń...")
        
        active_incidents = telemetry_summary.get("high_severity_incidents_found", 0)
        anomalies_count = telemetry_summary.get("flagged_anomalies_count", 0)
        
        # Logika decyzyjna agenta oparta na regułach autonomicznych
        decision = "NO_ACTION"
        confidence_score = 0.95

        if active_incidents > 0 or anomalies_count > 0:
            decision = "TRIGGER_CONTAINMENT_AND_ALERT"
            logger.warning(f"Agent AI wykrył anomalię! Podjęto autonomiczna decyzję: {decision}")
        else:
            logger.info("Agent AI nie stwierdził zagrożeń wymagających natychmiastowej eskalacji. System stabilny.")

        action_record = {
            "agent_id": "SANCTUM-AI-CORE-v1",
            "evaluated_at": datetime.utcnow().isoformat() + "Z",
            "input_metrics": {
                "active_incidents": active_incidents,
                "anomalies_count": anomalies_count
            },
            "autonomous_decision": decision,
            "confidence_score": confidence_score,
            "status": "executed"
        }

        # Zapis stanu decyzji agenta
        state_file = self.agent_state_dir / f"decision_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            state_file.write_text(json.dumps(action_record, indent=2, sort_keys=True), encoding="utf-8")
        except Exception as e:
            logger.error(f"Nie udało się zapisać stanu decyzji AI: {e}")

        return action_record