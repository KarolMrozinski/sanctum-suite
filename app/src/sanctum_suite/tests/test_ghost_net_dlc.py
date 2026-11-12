import pytest
from sanctum_suite.dlc.ghost_net.engine import GhostNetC2SimulationEngine


def test_ghost_net_dlc_is_disabled_without_network_side_effects():
    engine = GhostNetC2SimulationEngine()
    res = engine.simulate_covert_channel("DNS_TUNNELING")
    
    assert res["addon"] == "SANCTUM-DLC-GHOST-NET"
    assert res["status"] == "NOT_IMPLEMENTED"
    assert res["simulation_started"] is False
    assert res["protocol"] == "DNS_TUNNELING"
    assert res["mesh_telemetry"] is None
    assert res["dga_generated_nodes"] is None
    assert res["exfiltration_details"] is None