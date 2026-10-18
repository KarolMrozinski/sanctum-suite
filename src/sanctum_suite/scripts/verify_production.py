import os
import sys

from fastapi import HTTPException

from sanctum_suite.core.billing import CommercialLicenseManager
from sanctum_suite.core.target_authorization import require_authorized_target


def run_production_check() -> int:
    print("[SANCTUM-SUITE] Checking required audit configuration; no target will be scanned.")
    try:
        authorized_targets = os.environ.get("SANCTUM_AUTHORIZED_TARGETS", "")
        targets = [target.strip() for target in authorized_targets.split(",") if target.strip()]
        if not targets:
            raise ValueError("SANCTUM_AUTHORIZED_TARGETS is empty")
        require_authorized_target(targets[0], "production-preflight")
        entitlement = CommercialLicenseManager().validate_license_key(
            os.environ.get("SANCTUM_LICENSE_KEY")
        )
        print(f"[SANCTUM-SUITE] Signed entitlement validated for tenant {entitlement['tenant_id']}.")
        print("[SANCTUM-SUITE] Configuration preflight passed. This is not a production-readiness sign-off.")
        return 0
    except (HTTPException, ValueError) as error:
        print(f"[SANCTUM-SUITE] Configuration preflight failed: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(run_production_check())
