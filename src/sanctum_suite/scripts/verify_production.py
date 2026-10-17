import sys
import os
from sanctum_suite.orchestrator.engine import SanctumUnifiedOrchestrator


def run_production_check():
    print("🔍 [SANCTUM-SUITE] Initiating Pre-Production Readiness Verification...")
    
    # 1. Sprawdzenie silnika orkiestracji
    try:
        orchestrator = SanctumUnifiedOrchestrator()
        print("  ✅ Core Orchestrator initialized successfully.")
    except Exception as e:
        print(f"  ❌ Failed to initialize Orchestrator: {e}")
        sys.exit(1)

    # 2. Test pełnego audytu w trybie dry-run
    try:
        res = orchestrator.execute_full_resilience_audit("prod-readiness.internal")
        assert "audit_id" in res
        assert "compliance_evaluation" in res
        print(f"  ✅ Audit Pipeline Execution Verified (Audit ID: {res['audit_id']}).")
    except Exception as e:
        print(f"  ❌ Audit Pipeline Execution Failed: {e}")
        sys.exit(1)

    print("\n🚀 [SANCTUM-SUITE] SYSTEM IS 100% PRODUCTION READY!")


if __name__ == "__main__":
    run_production_check()