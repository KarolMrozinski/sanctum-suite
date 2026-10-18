import pytest
from sanctum_suite.dlc.cicada3301.engine import Cicada3301ChallengeAddon
from sanctum_suite.dlc.cicada3301.engine import Cicada3301ChallengeAddon
from sanctum_suite.dlc.cicada3301.steganography import LsbSteganographyEngine
from sanctum_suite.dlc.cicada3301.book_cipher import BookCipherEngine


def test_cicada_3301_dlc_omega_engine():
    addon = Cicada3301ChallengeAddon()
    res = addon.initialize_arg_rabbit_hole("Operator-Omega", "EQUATION_GROUP")
    
    assert res["addon"] == "SANCTUM-DLC-CICADA-3301"
    assert res["version"] == "5.0.0-OMEGA-HYPERSTITION"
    assert res["status"] == "OMEGA_ENCLAVE_SPAWNED"
    assert res["target_apt"] == "EQUATION_GROUP"
    assert "notpron_sensory_layer" in res
    assert "primroses_arithmetic_trapdoor" in res
    assert "steganography_container" in res
    assert len(res["stages"]) == 4

    # Test przechodzenia kolejnych etapów ARG
    step_res = addon.evaluate_arg_solution_step(res["session_id"], 1, "OmegaPrimeFactorization3301")
    assert step_res["solution_accepted"] is True
    assert step_res["next_active_stage"] == "PRIMROSES_MODULAR_FACTORIZATION"
    assert step_res["status"] == "STEP_EVALUATED_SUCCESS"

def test_complete_cicada_dlc_suite():
    addon = Cicada3301ChallengeAddon()
    session = addon.initialize_challenge_session("Operator-Delta")
    assert session["status"] == "SECURE_SESSION_INITIALIZED"

    # Test bezpiecznego porównania odpornego na timing attacks
    assert addon.verify_solution(session["session_id"], "Secret3301", "Secret3301") is True
    assert addon.verify_solution(session["session_id"], "WrongKey", "Secret3301") is False

    # Test stenografii LSB
    stego = LsbSteganographyEngine()
    carrier = bytearray(b"\x00" * 2000) # Zwiększony bufor nośny
    payload = b"CLASSIFIED_PAYLOAD_3301"
    
    embedded = stego.hide_payload(carrier, payload)
    extracted = stego.extract_payload(embedded)
    assert extracted == payload

    # Test Book Cipher
    bc = BookCipherEngine("alpha beta gamma delta alpha")
    indices = bc.encrypt_to_indices("alpha")
    assert len(indices) == 2
    resolved = bc.decrypt_from_indices(indices)
    assert "alpha" in resolved    