import os
import base64
from typing import Dict, Any
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class ZeroTrustKMSVault:
    """Silnik szyfrowania kopertowego (Envelope Encryption) i zarządzania sekretami."""

    def __init__(self) -> None:
        # Master Key do szyfrowania kluczy roboczych (Data Encryption Keys)
        self.master_key = AESGCM.generate_key(bit_length=256)

    def encrypt_payload(self, raw_data: str) -> Dict[str, str]:
        """Szyfruje dane wrażliwe przy użyciu unikalnego klucza roboczego (DEK)."""
        dek = AESGCM.generate_key(bit_length=256)
        aesgcm_dek = AESGCM(dek)
        nonce_data = os.urandom(12)
        
        ciphertext = aesgcm_dek.encrypt(nonce_data, raw_data.encode("utf-8"), None)

        # Szyfrowanie klucza DEK za pomocą Master Key (Koperta)
        aesgcm_master = AESGCM(self.master_key)
        nonce_dek = os.urandom(12)
        encrypted_dek = aesgcm_master.encrypt(nonce_dek, dek, None)

        return {
            "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
            "nonce_data": base64.b64encode(nonce_data).decode("utf-8"),
            "encrypted_dek": base64.b64encode(encrypted_dek).decode("utf-8"),
            "nonce_dek": base64.b64encode(nonce_dek).decode("utf-8"),
            "key_management": "LOCAL_EPHEMERAL_PROCESS_MEMORY",
            "production_kms_configured": "false",
        }

    def decrypt_payload(self, envelope: Dict[str, str]) -> str:
        """Odszyfrowuje kopertę kryptograficzną i zwraca treść pierwotną."""
        aesgcm_master = AESGCM(self.master_key)
        encrypted_dek = base64.b64decode(envelope["encrypted_dek"])
        nonce_dek = base64.b64decode(envelope["nonce_dek"])
        
        dek = aesgcm_master.decrypt(nonce_dek, encrypted_dek, None)
        aesgcm_dek = AESGCM(dek)
        
        ciphertext = base64.b64decode(envelope["ciphertext"])
        nonce_data = base64.b64decode(envelope["nonce_data"])
        
        decrypted = aesgcm_dek.decrypt(nonce_data, ciphertext, None)
        return decrypted.decode("utf-8")