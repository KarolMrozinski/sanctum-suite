import pytest
from sanctum_suite.core.behavioral_sentinel import AutonomousBehavioralSentinel


def test_behavioral_sentinel_normal():
    sentinel = AutonomousBehavioralSentinel(entropy_threshold=7.5)
    metrics = [4.2, 5.1, 3.8, 4.9] # Normalny poziom złożoności operacji
    res = sentinel.evaluate_system_entropy(metrics)
    
    assert res["metric_threshold_exceeded"] is False
    assert res["anomaly_detected"] is None
    assert res["autonomous_action_taken"] == "NONE"


def test_behavioral_sentinel_high_entropy_anomaly():
    sentinel = AutonomousBehavioralSentinel(entropy_threshold=7.5)
    metrics = [8.9, 9.1, 8.5] # Podejrzanie wysoka entropia (np. szyfrowanie ransomware / eksfiltracja)
    res = sentinel.evaluate_system_entropy(metrics)
    
    assert res["metric_threshold_exceeded"] is True
    assert res["anomaly_detected"] is None
    assert res["autonomous_action_taken"] == "NONE"