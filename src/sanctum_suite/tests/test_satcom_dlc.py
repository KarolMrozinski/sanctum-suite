import pytest
from sanctum_suite.dlc.satcom_spoof.engine import SatcomSpoofSimulationEngine


def test_satcom_spoof_dlc():
    engine = SatcomSpoofSimulationEngine()
    res = engine.audit_ccsds_telemetry_link("SAT-LEO-ALPHA-4")
    
    assert res["addon"] == "SANCTUM-DLC-SATCOM-SPOOF"
    assert res["status"] == "SATCOM_SPOOF_AUDIT_COMPLETED"
    assert res["target_satellite"] == "SAT-LEO-ALPHA-4"
    assert res["uplink_spoofing_risk"] == "HIGH"