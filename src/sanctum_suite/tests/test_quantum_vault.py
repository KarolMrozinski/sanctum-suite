import pytest
from sanctum_suite.core.quantum_ram_vault import QuantumSafeRamVaultEngine


def test_quantum_ram_vault_nominal():
    vault = QuantumSafeRamVaultEngine()
    res = vault.inspect_memory_integrity(debug_probe_active=False)
    
    assert res["status"] == "ENCLAVE_SECURE_NOMINAL"
    assert res["secure_memory_wiped"] is False


def test_quantum_ram_vault_breach():
    vault = QuantumSafeRamVaultEngine()
    res = vault.inspect_memory_integrity(debug_probe_active=True)
    
    assert res["status"] == "ENCLAVE_BREACH_DETECTED"
    assert res["secure_memory_wiped"] is True