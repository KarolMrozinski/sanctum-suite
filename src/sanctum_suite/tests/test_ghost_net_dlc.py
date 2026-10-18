import pytest
from sanctum_suite.dlc.ghost_net.engine import GhostNetC2SimulationEngine


def test_ghost_net_dlc():
    engine = GhostNetC2SimulationEngine()
    res = engine.simulate_covert_channel("ICMP_TUNNELING")
    
    assert res["addon"] == "SANCTUM-DLC-GHOST-NET"
    assert res["status"] == "GHOST_NET_SIMULATION_SUCCESS"
    assert res["protocol"] == "ICMP_TUNNELING"
    assert res["nodes_active"] > 0