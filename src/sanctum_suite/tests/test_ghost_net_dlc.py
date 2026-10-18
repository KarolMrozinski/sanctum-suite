import pytest
from sanctum_suite.dlc.ghost_net.engine import GhostNetC2SimulationEngine


def test_ghost_net_dlc_advanced():
    engine = GhostNetC2SimulationEngine()
    res = engine.simulate_covert_channel("DNS_TUNNELING")
    
    assert res["addon"] == "SANCTUM-DLC-GHOST-NET"
    assert res["version"] == "2.0.0-MILITARY-COVERT-C2"
    assert res["status"] == "GHOST_NET_SIMULATION_SUCCESS"
    assert res["protocol"] == "DNS_TUNNELING"
    assert "mesh_telemetry" in res
    assert len(res["dga_generated_nodes"]) == 3
    assert res["exfiltration_details"]["protocol"] == "DNS_TUNNELING"