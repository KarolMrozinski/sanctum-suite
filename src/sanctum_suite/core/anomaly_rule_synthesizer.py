#!/usr/bin/env python3

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (AnomalyRuleSynthesizer): %(message)s"
)
logger = logging.getLogger("AnomalyRuleSynthesizer")

class RuleSynthesizerError(Exception):
    """Custom exception for synthesis errors."""
    pass

class AnomalyRuleSynthesizer:
    """
    Synthesizes detection rules (Sigma/YARA format) automatically based on 
    anomalous telemetry patterns detected by autonomous agents in air-gapped environments.
    """

    def __init__(self, rules_output_dir: Path = Path("/var/lib/sanctum/rules")):
        self.rules_output_dir = Path(rules_output_dir)
        self.rules_output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized AnomalyRuleSynthesizer. Output dir: {self.rules_output_dir}")

    def synthesize_sigma_rule(self, anomaly_signature: str, indicators: List[str]) -> Dict[str, Any]:
        """
        Generates a Sigma rule structure from detected behavioral anomalies.
        """
        logger.info(f"Synthesizing Sigma rule for signature: '{anomaly_signature}'...")
        
        rule_id = f"SANCTUM-SIGMA-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        sigma_content = f"""title: Autonomous Detection - {anomaly_signature}
id: {rule_id}
status: experimental
description: Auto-generated behavioral anomaly detection rule by Sanctum Suite AI.
author: Sanctum Autonomous Agent
date: {datetime.utcnow().strftime('%Y/%m/%d')}
logsource:
    category: process_creation
    product: linux
detection:
    selection:
        CommandLine|contains:
"""
        for ind in indicators:
            sigma_content += f"            - '{ind}'\n"
            
        sigma_content += """    condition: selection
falsepositives:
    - Unknown administrative scripts
level: high
"""

        rule_file_path = self.rules_output_dir / f"{rule_id}.yml"
        rule_file_path.write_text(sigma_content, encoding="utf-8")
        logger.info(f"Sigma rule successfully synthesized and saved to: {rule_file_path}")

        return {
            "rule_id": rule_id,
            "file_path": str(rule_file_path),
            "status": "synthesized",
            "created_at": datetime.utcnow().isoformat() + "Z"
        }