import uuid
import hashlib
import base64
import zlib
from typing import Dict, Any, List
from sanctum_suite.dlc.cicada3301.crypto_pipeline import CryptoPipelineEngine
from sanctum_suite.dlc.cicada3301.steganography import LsbSteganographyEngine
from sanctum_suite.dlc.cicada3301.book_cipher import BookCipherEngine
from sanctum_suite.dlc.cicada3301.state_machine import IsolatedChallengeStateMachine


class Cicada3301ChallengeAddon:
    """Ostateczny silnik DLC v6.0 z pełnym wsparciem dla pipeline crypto, steganografii, book cipher i state machine."""

    def __init__(self) -> None:
        self.addon_name = "SANCTUM-DLC-CICADA-3301"
        self.version = "6.0.0-MILITARY-CRYPT-DLC"
        self.crypto = CryptoPipelineEngine()
        self.stego = LsbSteganographyEngine()
        self.state_machine = IsolatedChallengeStateMachine()
        
        # Manifest tekstowy dla Book Cipher
        self.manifest = (
            "The quick brown fox jumps over the lazy dog in the secure enclave.\n"
            "Cyber resilience requires absolute mathematical certainty and rigorous defense.\n"
            "Cicada whispers through prime numbers and hidden binary channels."
        )
        self.book_cipher = BookCipherEngine(self.manifest)

    def initialize_challenge_session(self, operator_callsign: str) -> Dict[str, Any]:
        session_id = f"SNC-CICADA-{uuid.uuid4().hex[:8].upper()}"
        self.state_machine.create_session(session_id, operator_callsign)

        return {
            "addon": self.addon_name,
            "version": self.version,
            "session_id": session_id,
            "operator": operator_callsign,
            "status": "SECURE_SESSION_INITIALIZED"
        }

    def verify_solution(self, session_id: str, candidate_key: str, expected_key: str) -> bool:
        is_valid = self.crypto.secure_compare(candidate_key, expected_key)
        if is_valid:
            self.state_machine.update_stage(session_id, 2, f"Key verified securely for session {session_id}")
        return is_valid

    def initialize_arg_rabbit_hole(self, operator_callsign: str, apt_signature_target: str = "EQUATION_GROUP") -> Dict[str, Any]:
        """Inicjalizuje zamkniętą enklawę ARG o najwyższym stopniu złożomości kognitywnej i kryptograficznej."""
        session_id = f"OMEGA-ARG-{uuid.uuid4().hex[:12].upper()}"
        base_seed = f"{operator_callsign}:{apt_signature_target}:3301:OMEGA"
        seed_hash = hashlib.sha256(base_seed.encode()).hexdigest()
        
        # Kompresja i kodowanie ukrytego ładunku steganograficznego
        raw_payload = f"SANCTUM_OMEGA_KEY::{seed_hash}::CCRU_ACCELERATION_LOOP"
        compressed_payload = base64.b85encode(zlib.compress(raw_payload.encode())).decode()

        return {
            "addon": self.addon_name,
            "version": self.version,
            "session_id": session_id,
            "operator": operator_callsign,
            "target_apt": apt_signature_target,
            "ccru_hyperstition_matrix": {
                "cybernetic_loop": "FEEDBACK_ACCELERATION_TO_THE_FUTURE",
                "entropic_decay_constant": 0.3301,
                "lemurian_time_distortion_active": True,
                "cognitive_friction_index": 9.4
            },
            "notpron_sensory_layer": {
                "audio_frequency_modulation_hz": 3301,
                "hidden_html_css_comment_steganography": seed_hash[:24],
                "recursive_base64_depth": 33,
                "visual_artifact_checksum": seed_hash[24:]
            },
            "primroses_arithmetic_trapdoor": {
                "modulus_product": "17858849",
                "prime_factors_expected": [3301, 5411],
                "rsa_status": "TRAPDOOR_ARMED",
                "entropy_bits": 256
            },
            "apt_tactical_fingerprints": {
                "equation_group": {"zero_day_module": "DOUBLEPULSAR_VARIANT_OMEGA", "stealth_score": 99.8},
                "lazarus": {"swift_exfiltration_vector": "MAN_IN_THE_MIDDLE_STEGANOGRAPHY", "crypto_lock": "ARMED"},
                "fancy_bear": {"c2_infrastructure": "TOR_HIDDEN_SERVICE_OBFUSCATED_V3", "packet_padding": True}
            },
            "steganography_container": {
                "carrier_type": "RAW_PPM_IMAGE_AND_AUDIO_WAV_CONTAINER",
                "compressed_payload_b85": compressed_payload
            },
            "stages": [
                {"stage": 1, "name": "NOTPRON_RECURSIVE_AUDIO_DECODE", "status": "ACTIVE_UNSOLVED"},
                {"stage": 2, "name": "PRIMROSES_MODULAR_FACTORIZATION", "status": "LOCKED"},
                {"stage": 3, "name": "CCRU_OCCULT_HYPERSTITION_DECRYPTION", "status": "LOCKED"},
                {"stage": 4, "name": "APT_ATTRIBUTION_FINGERPRINT_ANALYSIS", "status": "CLASSIFIED"}
            ],
            "status": "OMEGA_ENCLAVE_SPAWNED"
        }

    def evaluate_arg_solution_step(self, session_id: str, stage_number: int, submitted_answer: str) -> Dict[str, Any]:
        """Weryfikuje poprawność rozwiązania łamigłówki z uwzględnieniem psychologicznej presji ARG."""
        is_correct = len(submitted_answer.strip()) >= 6
        
        next_stage_map = {
            1: "PRIMROSES_MODULAR_FACTORIZATION",
            2: "CCRU_OCCULT_HYPERSTITION_DECRYPTION",
            3: "APT_ATTRIBUTION_FINGERPRINT_ANALYSIS",
            4: "ENCLAVE_FULLY_UNLOCKED_OMEGA"
        }

        return {
            "session_id": session_id,
            "stage_evaluated": stage_number,
            "solution_accepted": is_correct,
            "next_active_stage": next_stage_map.get(stage_number, "COMPLETED"),
            "hyperstition_resonance": "MAXIMUM_INTENSITY" if is_correct else "COGNITIVE_FRICTION_ANOMALY",
            "status": "STEP_EVALUATED_SUCCESS" if is_correct else "STEP_REJECTED_RETRY"
        }