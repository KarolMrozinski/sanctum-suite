from datetime import datetime, timedelta, timezone

import pytest

from sanctum_suite.core.qkd import (
    QKDIntegrationError,
    QKDKeyMaterial,
    derive_qkd_mlkem_hybrid_key,
    qkd_capabilities,
)


def _material(key: bytes | None = None) -> QKDKeyMaterial:
    return QKDKeyMaterial(
        key_id="key-123",
        peer_id="node-b",
        key=key or b"q" * 32,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=1),
    )


def test_qkd_and_mlkem_secrets_are_both_required_to_derive_hybrid_key():
    material = _material()
    options = {
        "mlkem_shared_secret": b"m" * 32,
        "context": b"checkpoint-transfer",
        "salt": b"s" * 32,
    }

    derived = derive_qkd_mlkem_hybrid_key(qkd_material=material, **options)

    assert len(derived) == 32
    assert derived != derive_qkd_mlkem_hybrid_key(
        qkd_material=_material(b"r" * 32), **options
    )
    assert derived != derive_qkd_mlkem_hybrid_key(
        qkd_material=material,
        **{**options, "mlkem_shared_secret": b"n" * 32},
    )


def test_qkd_hybrid_derivation_rejects_expired_material_and_invalid_secrets():
    material = QKDKeyMaterial(
        key_id="old-key",
        peer_id="node-b",
        key=b"q" * 32,
        expires_at=datetime(2026, 10, 19, tzinfo=timezone.utc),
    )
    with pytest.raises(QKDIntegrationError, match="expired"):
        derive_qkd_mlkem_hybrid_key(
            qkd_material=material,
            mlkem_shared_secret=b"m" * 32,
            context=b"test",
            salt=b"s" * 32,
            now=datetime(2026, 10, 20, tzinfo=timezone.utc),
        )
    with pytest.raises(QKDIntegrationError, match="exactly 32"):
        derive_qkd_mlkem_hybrid_key(
            qkd_material=_material(),
            mlkem_shared_secret=b"short",
            context=b"test",
            salt=b"s" * 32,
        )


def test_qkd_status_is_explicit_when_no_vendor_adapter_is_configured():
    status = qkd_capabilities()

    assert status["status"] == "NOT_CONFIGURED"
    assert "does not simulate" in status["limitations"]
