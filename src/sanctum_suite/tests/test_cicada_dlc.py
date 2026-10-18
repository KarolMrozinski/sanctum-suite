import pytest
from sanctum_suite.dlc.cicada3301.engine import Cicada3301ChallengeAddon


def test_cicada_3301_dlc_addon_expansion():
    addon = Cicada3301ChallengeAddon()
    res = addon.generate_cryptographic_puzzle_layer("Operator-Gamma")
    
    assert res["addon"] == "SANCTUM-DLC-CICADA-3301"
    assert res["status"] == "CICADA_ADDON_EXPANDED"
    assert "steganography_layer" in res
    assert len(res["stages"]) == 3

    # Test weryfikacji rozwiązania
    verification = addon.verify_operator_solution(res["puzzle_id"], "PrimeKey1234")
    assert verification["solution_verified"] is True
    assert verification["enclave_access_granted"] is True