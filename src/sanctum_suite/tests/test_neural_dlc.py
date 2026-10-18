import pytest
from sanctum_suite.dlc.neural_decoder.engine import NeuralDecoderSimulationEngine


def test_neural_decoder_dlc_reports_unavailable_assessment():
    engine = NeuralDecoderSimulationEngine()
    normal_latencies = [120.5, 115.0, 130.2, 125.4]
    res = engine.evaluate_operator_behavior(normal_latencies, panic_active=False)
    
    assert res["addon"] == "SANCTUM-DLC-NEURAL-DECODER"
    assert res["status"] == "NOT_ASSESSED"
    assert res["analysis_performed"] is False
    assert res["biometric_analysis"] is None
    assert res["threat_assessment"] is None