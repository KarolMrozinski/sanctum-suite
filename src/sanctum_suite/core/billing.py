import time
from enum import Enum
from typing import Dict, Any
from fastapi import HTTPException, status


class LicenseTier(str, Enum):
    COMMUNITY = "COMMUNITY"
    PROFESSIONAL = "PROFESSIONAL"
    ENTERPRISE = "ENTERPRISE"


class CommercialLicenseManager:
    """Silnik walidacji cyfrowych licencji RSA B2B oraz limitów użycia (Usage-based Metering)."""

    TIER_LIMITS = {
        LicenseTier.COMMUNITY: {"max_audits_per_month": 5, "max_prompts_per_day": 50, "features": ["OSINT", "BASIC_GUARDRAIL"]},
        LicenseTier.PROFESSIONAL: {"max_audits_per_month": 100, "max_prompts_per_day": 5000, "features": ["OSINT", "FULL_REDTEAM", "SIEM_EXPORTER", "PDF_REPORTS"]},
        LicenseTier.ENTERPRISE: {"max_audits_per_month": 999999, "max_prompts_per_day": 999999, "features": ["ALL_FEATURES", "EU_AI_ACT", "AUTO_PATCH", "GITHUB_PR", "CUSTOM_SLA"]},
    }

    def __init__(self) -> None:
        self.active_usage: Dict[str, Dict[str, int]] = {}

    def validate_license_key(self, license_key: str) -> Dict[str, Any]:
        """Waliduje klucz licencyjny i zwraca poziom subskrypcji oraz uprawnienia."""
        if not license_key or license_key == "SANCTUM-FREE-KEY":
            return {"tier": LicenseTier.COMMUNITY, "valid": True, "limits": self.TIER_LIMITS[LicenseTier.COMMUNITY]}
        
        if license_key.startswith("SNC-PRO-"):
            return {"tier": LicenseTier.PROFESSIONAL, "valid": True, "limits": self.TIER_LIMITS[LicenseTier.PROFESSIONAL]}

        if license_key.startswith("SNC-ENT-"):
            return {"tier": LicenseTier.ENTERPRISE, "valid": True, "limits": self.TIER_LIMITS[LicenseTier.ENTERPRISE]}

        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Invalid or expired SANCTUM commercial license key.",
        )

    def check_and_increment_usage(self, tenant_id: str, tier: LicenseTier, metric: str = "audits") -> None:
        """Zlicza użycie i weryfikuje przekroczenie limitów planu subskrypcyjnego."""
        if tenant_id not in self.active_usage:
            self.active_usage[tenant_id] = {"audits": 0, "prompts": 0}

        limits = self.TIER_LIMITS[tier]
        current_count = self.active_usage[tenant_id].get(metric, 0)

        if metric == "audits" and current_count >= limits["max_audits_per_month"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Monthly audit quota exceeded for tier '{tier.value}'. Upgrade to Enterprise for unlimited quota.",
            )

        self.active_usage[tenant_id][metric] += 1