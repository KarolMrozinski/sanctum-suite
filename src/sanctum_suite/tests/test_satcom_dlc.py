import pytest
from sanctum_suite.dlc.satcom_spoof.engine import SatcomSpoofSimulationEngine


def test_satcom_spoof_dlc_does_not_claim_to_test_satellites():
    engine = SatcomSpoofSimulationEngine()
    res = engine.audit_ccsds_telemetry_link("SAT-LEO-OMEGA-9")
    
    assert res["addon"] == "SANCTUM-DLC-SATCOM-SPOOF"
    assert res["status"] == "NOT_ASSESSED"
    assert res["assessment_performed"] is False
    assert res["target_satellite"] == "SAT-LEO-OMEGA-9"
    assert res["orbital_mechanics"] is None
    assert res["ccsds_telemetry_inspection"] is None
    assert res["uplink_spoofing_assessment"] is None