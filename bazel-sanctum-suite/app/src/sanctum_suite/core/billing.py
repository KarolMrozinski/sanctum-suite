import base64
import binascii
import json
import os
import re
import sqlite3
from collections.abc import Mapping
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import HTTPException, status


class LicenseTier(str, Enum):
    COMMUNITY = "COMMUNITY"
    PROFESSIONAL = "PROFESSIONAL"
    ENTERPRISE = "ENTERPRISE"


_TOKEN_PART_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
_USAGE_PERIODS = {"audits": "month", "prompts": "day"}
_LIMIT_KEYS = {"audits": "max_audits_per_month", "prompts": "max_prompts_per_day"}
_REQUIRED_FEATURES = {"audits": "audit", "prompts": "prompt-inspection"}


class CommercialLicenseManager:
    """Validates signed offline entitlements and meters usage in SQLite."""

    def __init__(
        self,
        public_key_pem: bytes | None = None,
        db_path: str | Path | None = None,
    ) -> None:
        configured_public_key = os.environ.get("SANCTUM_LICENSE_PUBLIC_KEY")
        self.public_key_pem = public_key_pem or (
            configured_public_key.encode("utf-8") if configured_public_key else None
        )
        configured_db_path = os.environ.get("SANCTUM_BILLING_DB")
        self.db_path = str(
            db_path
            or configured_db_path
            or (Path.home() / ".sanctum-suite" / "usage.sqlite3")
        )

    @staticmethod
    def _decode_segment(segment: str) -> bytes:
        if not _TOKEN_PART_PATTERN.fullmatch(segment):
            raise ValueError("License token contains an invalid base64url segment")
        try:
            return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))
        except binascii.Error as error:
            raise ValueError("License token contains invalid base64url data") from error

    def validate_license_key(self, license_key: str | None) -> dict[str, Any]:
        if self.public_key_pem is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Signed license verification is not configured",
            )
        if not license_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No signed license token is configured",
            )
        if len(license_key) > 16_384:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="SANCTUM license token exceeds the size limit",
            )
        try:
            public_key = serialization.load_pem_public_key(self.public_key_pem)
        except (ValueError, TypeError) as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Configured SANCTUM license public key is invalid",
            ) from error
        if not isinstance(public_key, Ed25519PublicKey):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Configured SANCTUM license public key must use Ed25519",
            )
        parts = license_key.split(".")
        if len(parts) != 2:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Invalid SANCTUM license token",
            )

        encoded_payload, encoded_signature = parts
        try:
            payload_bytes = self._decode_segment(encoded_payload)
            signature = self._decode_segment(encoded_signature)
            public_key.verify(signature, encoded_payload.encode("ascii"))
            claims = json.loads(payload_bytes)
        except InvalidSignature as error:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Invalid SANCTUM license signature",
            ) from error
        except (ValueError, TypeError, binascii.Error, json.JSONDecodeError) as error:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Malformed SANCTUM license token",
            ) from error
        except (IndexError, UnicodeDecodeError) as error:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Malformed SANCTUM license token",
            ) from error

        if not isinstance(claims, dict):
            raise HTTPException(status_code=402, detail="License claims must be an object")
        tenant_id = claims.get("tenant_id")
        license_id = claims.get("license_id")
        expires_at = claims.get("exp")
        try:
            tier = LicenseTier(claims.get("tier"))
        except ValueError as error:
            raise HTTPException(status_code=402, detail="Unknown SANCTUM license tier") from error
        if (
            not isinstance(tenant_id, str)
            or not tenant_id
            or len(tenant_id) > 64
            or not isinstance(license_id, str)
            or len(license_id) > 128
            or not license_id
            or not isinstance(expires_at, int)
            or isinstance(expires_at, bool)
        ):
            raise HTTPException(status_code=402, detail="Required SANCTUM license claims are missing")
        if expires_at <= int(datetime.now(timezone.utc).timestamp()):
            raise HTTPException(status_code=402, detail="SANCTUM license has expired")

        limits = claims.get("limits")
        features = claims.get("features")
        if not isinstance(limits, dict) or not isinstance(features, list):
            raise HTTPException(status_code=402, detail="SANCTUM license entitlements are malformed")
        normalized_limits: dict[str, int] = {}
        for metric, claim_name in _LIMIT_KEYS.items():
            value = limits.get(claim_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise HTTPException(
                    status_code=402,
                    detail=f"License limit '{claim_name}' must be a non-negative integer",
                )
            normalized_limits[claim_name] = value
        if not all(isinstance(feature, str) and feature for feature in features):
            raise HTTPException(status_code=402, detail="License features must be non-empty strings")

        return {
            "license_id": license_id,
            "tenant_id": tenant_id,
            "tier": tier,
            "valid": True,
            "expires_at": expires_at,
            "limits": normalized_limits,
            "features": features,
        }

    def check_and_increment_usage(
        self,
        tenant_id: str,
        entitlement: Mapping[str, Any],
        metric: str = "audits",
    ) -> None:
        if metric not in _USAGE_PERIODS:
            raise ValueError(f"Unsupported usage metric: {metric}")
        if tenant_id != entitlement.get("tenant_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usage tenant does not match the signed entitlement",
            )
        required_feature = _REQUIRED_FEATURES[metric]
        if required_feature not in entitlement.get("features", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Signed entitlement does not include feature '{required_feature}'",
            )
        limit_name = _LIMIT_KEYS[metric]
        limit = entitlement["limits"][limit_name]
        now = datetime.now(timezone.utc)
        period = now.strftime("%Y-%m") if _USAGE_PERIODS[metric] == "month" else now.strftime("%Y-%m-%d")
        database_path = Path(self.db_path).expanduser()
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(database_path, timeout=10) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS license_usage (
                    tenant_id TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    period TEXT NOT NULL,
                    usage_count INTEGER NOT NULL CHECK (usage_count >= 0),
                    PRIMARY KEY (tenant_id, metric, period)
                )
                """
            )
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT usage_count FROM license_usage
                WHERE tenant_id = ? AND metric = ? AND period = ?
                """,
                (tenant_id, metric, period),
            ).fetchone()
            current = int(row[0]) if row else 0
            if current >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Signed entitlement quota exceeded for metric '{metric}'",
                )
            connection.execute(
                """
                INSERT INTO license_usage (tenant_id, metric, period, usage_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT (tenant_id, metric, period)
                DO UPDATE SET usage_count = usage_count + 1
                """,
                (tenant_id, metric, period),
            )
