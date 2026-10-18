import pytest
from sanctum_suite.core.darknet_apt_shield import DarknetAptShieldEngine


def test_darknet_apt_shield():
    engine = DarknetAptShieldEngine()
    res = engine.scan_for_apt_anomalies("TEST-HASH-12345")
    
    assert res["status"] == "DARKNET_APT_SHIELD_SECURED"
    assert res["sandbox_evasion_detected"] is False
    assert res["apt_threat_level"] == "ZERO"