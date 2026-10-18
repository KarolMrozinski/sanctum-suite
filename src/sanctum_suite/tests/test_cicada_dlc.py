import pytest
from sanctum_suite.dlc.cicada3301.engine import Cicada3301ChallengeAddon


def test_cicada_3301_dlc_occult_arg():
    addon = Cicada3301ChallengeAddon()
    res = addon.initialize_arg_rabbit_hole("Operator-Omega", "LAZARUS_GROUP")
    
    assert res["addon"] == "SANCTUM-DLC-CICADA-3301"
    assert res["status"] == "ARG_ENVIRONMENT_SPAWNED"
    assert res["simulated_apt_target"] == "LAZARUS_GROUP"
    assert "notpron_audio_visual_layers" in res
    assert "primroses_arithmetic_puzzle" in res
    assert len(res["stages"]) == 4

    # Test weryfikacji etapu ARG
    eval_res = addon.evaluate_arg_solution_step(res["session_id"], 1, "DecodedNotpronAudioToken3301")
    assert eval_res["status"] == "SOLUTION_PROCESSED"
    assert eval_res["solution_correct"] is True