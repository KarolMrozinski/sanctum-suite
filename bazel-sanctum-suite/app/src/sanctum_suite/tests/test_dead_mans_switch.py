import pytest
from sanctum_suite.core.dead_mans_switch import KernelDeadMansSwitch


def test_dead_mans_switch_nominal():
    switch = KernelDeadMansSwitch(heartbeat_timeout_seconds=5.0)
    assert switch.pulse_heartbeat() is False
    res = switch.check_system_integrity(forced_compromise=False)
    
    assert res["status"] == "NOT_IMPLEMENTED"
    assert res["monitoring_active"] is False
    assert res["cascading_wipe_executed"] is False
    assert res["database_shredded"] is False


def test_dead_mans_switch_triggered():
    switch = KernelDeadMansSwitch()
    res = switch.check_system_integrity(forced_compromise=True)
    
    assert res["status"] == "NOT_IMPLEMENTED"
    assert res["cascading_wipe_executed"] is False
    assert res["database_shredded"] is False