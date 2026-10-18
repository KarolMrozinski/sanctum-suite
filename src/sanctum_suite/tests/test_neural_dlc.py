import pytest
from sanctum_suite.dlc.neural_decoder.engine import NeuralDecoderSimulationEngine


def test_neural_decoder_dlc_advanced():
    engine = NeuralDecoderSimulationEngine()
    # Prawidłowy rytm pisania (latencje w milisekundach)
    normal_latencies = [120.5, 115.0, 130.2, 125.4]
    res = engine.evaluate_operator_behavior(normal_latencies, panic_active=False)
    
    assert res["addon"] == "SANCTUM-DLC-NEURAL-DECODER"
    assert res["version"] == "2.0.0-NEURAL-GUARDIAN"
    assert res["status"] == "NEURAL_DECODER_AUDIT_COMPLETED"
    assert res["biometric_analysis"]["coercion_stress_detected"] is False
    assert res["threat_assessment"]["status"] == "ENCLAVE_SECURE_NOMINAL"