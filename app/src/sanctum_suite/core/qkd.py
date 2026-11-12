"""Integration contracts for operator-managed quantum key distribution systems."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class QKDIntegrationError(ValueError):
    """Raised when QKD key material or its required metadata is invalid."""


@dataclass(frozen=True)
class QKDKeyMaterial:
    """Short-lived key material returned by a trusted, authenticated QKD adapter."""

    key_id: str
    peer_id: str
    key: bytes
    expires_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.key_id, str) or not _IDENTIFIER.fullmatch(self.key_id):
            raise QKDIntegrationError("QKD key identifier is invalid")
        if not isinstance(self.peer_id, str) or not _IDENTIFIER.fullmatch(self.peer_id):
            raise QKDIntegrationError("QKD peer identifier is invalid")
        if not isinstance(self.key, bytes) or len(self.key) < 32:
            raise QKDIntegrationError("QKD key material must contain at least 32 bytes")
        if (
            not isinstance(self.expires_at, datetime)
            or self.expires_at.tzinfo is None
            or self.expires_at.utcoffset() is None
        ):
            raise QKDIntegrationError("QKD key expiry must include a timezone")

    def require_fresh(self, *, now: datetime | None = None) -> None:
        current_time = now or datetime.now(timezone.utc)
        if (
            not isinstance(current_time, datetime)
            or current_time.tzinfo is None
            or current_time.utcoffset() is None
        ):
            raise QKDIntegrationError("QKD freshness check time must include a timezone")
        if self.expires_at <= current_time:
            raise QKDIntegrationError("QKD key material has expired")


class QKDKeyProvider(Protocol):
    """Adapter boundary for a vendor QKD KME or trusted key-management gateway."""

    def acquire_key(
        self,
        *,
        peer_id: str,
        purpose: str,
    ) -> QKDKeyMaterial: ...


def derive_qkd_mlkem_hybrid_key(
    *,
    qkd_material: QKDKeyMaterial,
    mlkem_shared_secret: bytes,
    context: bytes,
    salt: bytes,
    now: datetime | None = None,
) -> bytes:
    """Combine fresh QKD and ML-KEM secrets; neither source alone determines the key."""
    qkd_material.require_fresh(now=now)
    if not isinstance(mlkem_shared_secret, bytes) or len(mlkem_shared_secret) != 32:
        raise QKDIntegrationError("ML-KEM shared secret must contain exactly 32 bytes")
    if not isinstance(context, bytes) or not context or len(context) > 1_024:
        raise QKDIntegrationError("Hybrid key context must be 1-1024 bytes")
    if not isinstance(salt, bytes) or len(salt) != 32:
        raise QKDIntegrationError("Hybrid key derivation salt must contain 32 bytes")
    info = (
        b"SANCTUM-QKD-MLKEM-HYBRID-v1\x00"
        + qkd_material.peer_id.encode("ascii")
        + b"\x00"
        + qkd_material.key_id.encode("ascii")
        + b"\x00"
        + hashlib.sha256(context).digest()
    )
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=info,
    ).derive(qkd_material.key + mlkem_shared_secret)


def qkd_capabilities() -> dict[str, str]:
    """Return an explicit unconfigured status until a real QKD adapter is supplied."""
    return {
        "status": "NOT_CONFIGURED",
        "provider": "none",
        "key_establishment": "ML-KEM-768 remains the available algorithmic KEM",
        "limitations": (
            "No QKD hardware, KME, authenticated peer channel, or vendor adapter "
            "is configured. This module does not simulate photon transmission "
            "or certify QKD link security."
        ),
    }
