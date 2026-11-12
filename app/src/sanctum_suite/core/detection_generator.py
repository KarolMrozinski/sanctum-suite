#!/usr/bin/env python3

import os
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (DetectionGenerator): %(message)s"
)
logger = logging.getLogger("DetectionGenerator")

class DetectionGeneratorError(Exception):
    pass

class AutomatedDetectionRuleGenerator:

    def __init__(self, rules_output_dir: Path = Path("/var/lib/sanctum/rules")):
        self.rules_output_dir = Path(rules_output_dir)
        self.rules_output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Inicjalizacja AutomatedDetectionRuleGenerator w katalogu: {self.rules_output_dir}")

    def generate_yara_rule_content(self, rule_name: str, target_hash: str) -> str:
        yara_content = f"""/*
    Automatycznie wygenerowana reguła YARA dla Sanctum Suite
    Zagrożenie / IOC: {rule_name}
*/

rule Sanctum_APT_{rule_name} {{
    meta:
        author = "Sanctum-Suite-Engine"
        target_hash = "{target_hash}"
        generated_at = "{datetime.utcnow().isoformat()}Z"
    strings:
        $ioc_hash = "{target_hash}"
    condition:
        any of them
}}
"""
        return yara_content

    def export_detection_rule(self, rule_name: str, target_hash: str) -> Path:
        logger.info(f"Generowanie reguły YARA dla wskaźnika: {rule_name}")
        try:
            filename = self.rules_output_dir / f"apt_rule_{rule_name}.yar"
            content = self.generate_yara_rule_content(rule_name, target_hash)
            
            filename.write_text(content, encoding="utf-8")
            logger.info(f"Reguła detekcyjna została pomyślnie zapisana: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Błąd podczas generowania reguły YARA: {e}")
            raise DetectionGeneratorError(f"Nie udało się wygenerować reguły detekcyjnej: {e}") from e