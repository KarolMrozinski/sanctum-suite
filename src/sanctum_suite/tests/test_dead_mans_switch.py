import pytest
from sanctum_suite.core.dead_mans_switch import KernelDeadMansSwitch


def test_dead_mans_switch_nominal():
    switch = KernelDeadMansSwitch(heartbeat_timeout_seconds=5.0)
    switch.pulse_heartbeat()
    res = switch.check_system_integrity(forced_compromise=False)
    
    assert res["status"] == "DEAD_MANS_SWITCH_ARMED_NOMINAL"
    assert res["database_shredded"] is False


def test_dead_mans_switch_triggered():
    switch = KernelDeadMansSwitch()
    res = switch.check_system_integrity(forced_compromise=True)
    
    assert res["status"] == "DEAD_MANS_SWITCH_TRIGGERED"
    assert res["database_shredded"] is True