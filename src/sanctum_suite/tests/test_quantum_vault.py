import pytest
from sanctum_suite.core.quantum_ram_vault import QuantumSafeRamVaultEngine


def test_quantum_ram_vault_reports_unavailable_attestation():
    vault = QuantumSafeRamVaultEngine()
    res = vault.inspect_memory_integrity(debug_probe_active=False)
    
    assert res["status"] == "NOT_IMPLEMENTED"
    assert res["attestation_valid"] is None
    assert res["hardware_integration_required"] is True
    assert res["zeroization_performed"] is False


def test_quantum_ram_vault_does_not_fake_probe_detection():
    vault = QuantumSafeRamVaultEngine()
    res = vault.inspect_memory_integrity(debug_probe_active=True)
    
    assert res["status"] == "NOT_IMPLEMENTED"
    assert res["debug_probe_detection"] == "NOT_IMPLEMENTED"
    assert vault.zeroize_vault() is False