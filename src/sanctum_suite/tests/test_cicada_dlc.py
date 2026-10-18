import pytest
from sanctum_suite.dlc.cicada3301.engine import Cicada3301ChallengeAddon


def test_cicada_3301_dlc_hyperstition_engine():
    addon = Cicada3301ChallengeAddon()
    res = addon.initialize_arg_rabbit_hole("Operator-Zeta", "EQUATION_GROUP")
    
    assert res["addon"] == "SANCTUM-DLC-CICADA-3301"
    assert res["version"] == "4.0.0-HYPERSTITION-CORE"
    assert res["status"] == "HYPERSTITION_ENCLAVE_SPAWNED"
    assert res["target_apt"] == "EQUATION_GROUP"
    assert "notpron_sensory_layer" in res
    assert "primroses_arithmetic_trapdoor" in res
    assert "steganography_container" in res
    assert len(res["stages"]) == 4

    # Test przechodzenia kolejnych etapów ARG
    step_res = addon.evaluate_arg_solution_step(res["session_id"], 1, "CorrectPrimeFactorizationSolution3301")
    assert step_res["solution_accepted"] is True
    assert step_res["next_active_stage"] == "PRIMROSES_MODULAR_FACTORIZATION"
    assert step_res["status"] == "STEP_EVALUATED_SUCCESS"