import pytest
from sanctum_suite.dlc.satcom_spoof.engine import SatcomSpoofSimulationEngine


def test_satcom_spoof_dlc_advanced():
    engine = SatcomSpoofSimulationEngine()
    res = engine.audit_ccsds_telemetry_link("SAT-LEO-OMEGA-9")
    
    assert res["addon"] == "SANCTUM-DLC-SATCOM-SPOOF"
    assert res["version"] == "2.0.0-ORBITAL-DEFENDER"
    assert res["status"] == "SATCOM_SPOOF_AUDIT_COMPLETED"
    assert res["target_satellite"] == "SAT-LEO-OMEGA-9"
    assert "orbital_mechanics" in res
    assert "ccsds_telemetry_inspection" in res
    assert res["uplink_spoofing_assessment"]["status"] == "UPLINK_VULNERABILITY_CONFIRMED"