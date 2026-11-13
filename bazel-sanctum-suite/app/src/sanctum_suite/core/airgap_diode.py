import hashlib
import json
import uuid
from typing import Any

from cryptography.hazmat.primitives import serialization

from sanctum_suite.core.trust_chain import SovereignTrustChainVerifier


class AirGapDataDiodeBroker:
    """Prepares a signed-or-unsigned manifest for a manually operated offline transfer."""

    def prepare_offline_package(
        self,
        payload_data: bytes,
        target_enclave: str,
        signature: bytes | None = None,
        public_key_pem: bytes | None = None,
    ) -> dict[str, Any]:
        target = target_enclave.strip()
        if not target:
            raise ValueError("A destination enclave label is required")
        verification = SovereignTrustChainVerifier().verify_module_integrity(
            "offline-transfer-payload",
            payload_data,
            signature,
            public_key_pem,
        )
        if verification["signature_valid"] is False:
            raise ValueError("Offline package signature verification failed")
        signed = verification["signature_valid"] is True
        signer_key_fingerprint = None
        if signed and public_key_pem is not None:
            public_key = serialization.load_pem_public_key(public_key_pem)
            signer_key_der = public_key.public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            signer_key_fingerprint = hashlib.sha256(signer_key_der).hexdigest()
        transfer_id = f"OFFLINE-{uuid.uuid4().hex[:8].upper()}"
        manifest = {
            "manifest_version": "1",
            "transfer_id": transfer_id,
            "target_enclave": target,
            "payload_bytes": len(payload_data),
            "payload_sha256": hashlib.sha256(payload_data).hexdigest(),
            "signature_valid": verification["signature_valid"],
            "signer_public_key_sha256": signer_key_fingerprint,
        }
        canonical_manifest = json.dumps(
            manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
        return {
            "transfer_id": transfer_id,
            "target_enclave": target,
            "payload_bytes": len(payload_data),
            "payload_sha256": manifest["payload_sha256"],
            "signature_valid": verification["signature_valid"],
            "signer_public_key_sha256": signer_key_fingerprint,
            "manifest": manifest,
            "manifest_sha256": hashlib.sha256(canonical_manifest).hexdigest(),
            "status": (
                "SIGNED_PACKAGE_READY_FOR_MANUAL_OFFLINE_TRANSFER"
                if signed
                else "UNSIGNED_MANIFEST_READY_FOR_MANUAL_OFFLINE_TRANSFER"
            ),
            "transmitted": False,
            "physical_diode_verified": False,
            "return_channel_blocked": None,
            "limitations": (
                "A manifest does not transfer data, enforce one-way flow, establish air-gap "
                "isolation, or assess TEMPEST/NATO SDIP-27. A valid signature proves only "
                "that the supplied key signed the payload; key ownership/trust and manifest "
                "authenticity require independent verification."
            ),
        }

    def enforce_unidirectional_transfer(self, payload_data: str, target_enclave: str) -> dict[str, Any]:
        """Compatibility alias; prepares a manifest but never transfers data."""
        return self.prepare_offline_package(payload_data.encode("utf-8"), target_enclave)
