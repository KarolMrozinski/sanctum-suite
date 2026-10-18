import hashlib
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, ed448, padding, rsa


class SovereignTrustChainVerifier:
    """Verifies a supplied signature over module bytes using a supplied public key."""

    def verify_module_integrity(
        self,
        module_name: str,
        binary_content: bytes,
        signature: bytes | None = None,
        public_key_pem: bytes | None = None,
    ) -> dict[str, Any]:
        if not module_name.strip():
            raise ValueError("A module name is required")
        digest = hashlib.sha256(binary_content).hexdigest()
        result: dict[str, Any] = {
            "module_name": module_name,
            "sha256_sum": digest,
            "signature_valid": None,
            "status": "DIGEST_ONLY_NOT_AUTHENTICATED",
        }
        if signature is None and public_key_pem is None:
            return result
        if signature is None or public_key_pem is None:
            raise ValueError("Both a signature and its public key are required")

        public_key = serialization.load_pem_public_key(public_key_pem)
        try:
            if isinstance(public_key, ed25519.Ed25519PublicKey | ed448.Ed448PublicKey):
                public_key.verify(signature, binary_content)
            elif isinstance(public_key, rsa.RSAPublicKey):
                public_key.verify(signature, binary_content, padding.PKCS1v15(), hashes.SHA256())
            elif isinstance(public_key, ec.EllipticCurvePublicKey):
                public_key.verify(signature, binary_content, ec.ECDSA(hashes.SHA256()))
            else:
                raise ValueError("Unsupported public-key type for module verification")
        except InvalidSignature:
            result["signature_valid"] = False
            result["status"] = "SIGNATURE_INVALID"
            return result

        result["signature_valid"] = True
        result["status"] = "SIGNATURE_VALID"
        return result
