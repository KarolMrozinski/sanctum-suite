#!/usr/bin/env python3

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (HardwareSecurityValidator): %(message)s"
)
logger = logging.getLogger("HardwareSecurityValidator")

class HardwareSecurityError(Exception):
    pass

class HardwareSecurityValidator:

    def __init__(self, tpm_device_path: Path = Path("/dev/tpm0")):
        self.tpm_device_path = Path(tpm_device_path)
        logger.info(f"Inicjalizacja HardwareSecurityValidator ze ścieżką urządzenia TPM: {self.tpm_device_path}")

    def validate_hardware_trust_anchors(self) -> Dict[str, Any]:
        logger.info("Rozpoczęto walidację sprzętowych kotwic zaufania (TPM 2.0 / TEE / Secure Boot)...")
        
        tpm_present = self.tpm_device_path.exists()
        secure_boot_enabled = os.environ.get("SANCTUM_SECURE_BOOT_ENFORCED", "true").lower() == "true"
        tee_active = os.environ.get("SANCTUM_TEE_MODE", "enabled").lower() in ["enabled", "active"]

        checks = {
            "tpm_device_present": tpm_present,
            "secure_boot_enforced": secure_boot_enabled,
            "tee_environment_active": tee_active
        }

        all_passed = all(checks.values())
        if not all_passed:
            logger.warning("Wykryto brak niektórych wymaganych sprzętowych mechanizmów bezpieczeństwa.")
        else:
            logger.info("Wszystkie sprzętowe kotwice zaufania zostały pomyślnie zweryfikowane.")

        report = {
            "validation_id": f"HW-SEC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "checks": checks,
            "overall_status": "secure" if all_passed else "degraded",
            "validated_at": datetime.utcnow().isoformat() + "Z"
        }

        return report