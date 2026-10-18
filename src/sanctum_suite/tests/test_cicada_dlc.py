import pytest
from sanctum_suite.dlc.cicada3301.engine import Cicada3301ChallengeAddon


def test_cicada_3301_dlc_addon():
    addon = Cicada3301ChallengeAddon()
    res = addon.generate_cryptographic_puzzle_layer("Operator-Alpha")
    assert res["addon"] == "SANCTUM-DLC-CICADA-3301"
    assert res["status"] == "CICADA_ADDON_ACTIVE"
    assert len(res["stages"]) == 3