import base64
import json
import time
from collections.abc import Sequence
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from sanctum_suite.core.billing import LicenseTier


def issue_license_token(
    private_key: Ed25519PrivateKey,
    *,
    license_id: str,
    tenant_id: str,
    tier: LicenseTier | str,
    expires_at: int,
    max_audits_per_month: int,
    max_prompts_per_day: int,
    features: Sequence[str],
) -> str:
    if not isinstance(license_id, str) or not license_id or len(license_id) > 128:
        raise ValueError("license_id must contain between 1 and 128 characters")
    if not isinstance(tenant_id, str) or not tenant_id or len(tenant_id) > 64:
        raise ValueError("tenant_id must contain between 1 and 64 characters")
    try:
        normalized_tier = LicenseTier(tier)
    except ValueError as error:
        raise ValueError("tier must be a supported SANCTUM license tier") from error
    if not isinstance(expires_at, int) or isinstance(expires_at, bool) or expires_at <= int(time.time()):
        raise ValueError("expires_at must be a future Unix timestamp")
    limits = (max_audits_per_month, max_prompts_per_day)
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in limits):
        raise ValueError("License limits must be non-negative integers")
    if isinstance(features, (str, bytes)) or len(features) > 32:
        raise ValueError("features must be a sequence of at most 32 feature names")
    normalized_features = list(features)
    if not all(
        isinstance(feature, str) and 0 < len(feature.strip()) <= 100
        for feature in normalized_features
    ):
        raise ValueError("features must contain non-empty strings")

    claims: dict[str, Any] = {
        "license_id": license_id,
        "tenant_id": tenant_id,
        "tier": normalized_tier.value,
        "exp": expires_at,
        "limits": {
            "max_audits_per_month": max_audits_per_month,
            "max_prompts_per_day": max_prompts_per_day,
        },
        "features": [feature.strip() for feature in normalized_features],
    }
    payload = json.dumps(claims, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")
    signature = private_key.sign(encoded_payload.encode("ascii"))
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
    return f"{encoded_payload}.{encoded_signature}"
