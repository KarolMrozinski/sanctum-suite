import json
import time

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from typer.testing import CliRunner

from sanctum_suite.core.billing import CommercialLicenseManager, LicenseTier
from sanctum_suite.core.license_issuer import issue_license_token
from sanctum_suite.main import app


def _public_key_pem(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def test_offline_license_issuer_creates_verifiable_token(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    token = issue_license_token(
        private_key,
        license_id="license-001",
        tenant_id="tenant-001",
        tier=LicenseTier.PROFESSIONAL,
        expires_at=int(time.time()) + 3_600,
        max_audits_per_month=10,
        max_prompts_per_day=100,
        features=["audit", "prompt-inspection"],
    )

    claims = CommercialLicenseManager(
        public_key_pem=_public_key_pem(private_key),
        db_path=tmp_path / "usage.sqlite3",
    ).validate_license_key(token)

    assert claims["license_id"] == "license-001"
    assert claims["tenant_id"] == "tenant-001"
    assert claims["tier"] == LicenseTier.PROFESSIONAL
    assert claims["features"] == ["audit", "prompt-inspection"]


def test_offline_license_issuer_rejects_expired_and_invalid_claims():
    private_key = Ed25519PrivateKey.generate()
    with pytest.raises(ValueError, match="future Unix timestamp"):
        issue_license_token(
            private_key,
            license_id="license-001",
            tenant_id="tenant-001",
            tier=LicenseTier.COMMUNITY,
            expires_at=int(time.time()) - 1,
            max_audits_per_month=1,
            max_prompts_per_day=1,
            features=["audit"],
        )
    with pytest.raises(ValueError, match="non-negative"):
        issue_license_token(
            private_key,
            license_id="license-001",
            tenant_id="tenant-001",
            tier=LicenseTier.COMMUNITY,
            expires_at=int(time.time()) + 3_600,
            max_audits_per_month=-1,
            max_prompts_per_day=1,
            features=["audit"],
        )


def test_issue_license_cli_outputs_token_and_public_key(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    key_file = tmp_path / "issuer.pem"
    key_file.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    result = CliRunner().invoke(
        app,
        [
            "issue-license",
            "--private-key-file",
            str(key_file),
            "--license-id",
            "license-cli",
            "--tenant-id",
            "tenant-cli",
            "--tier",
            "COMMUNITY",
            "--expires-in-days",
            "30",
            "--max-audits-per-month",
            "2",
            "--max-prompts-per-day",
            "20",
        ],
    )

    assert result.exit_code == 0, result.output
    output = json.loads(result.stdout)
    assert output["license_token"]
    assert output["verification_public_key_pem"].startswith("-----BEGIN PUBLIC KEY-----")
    claims = CommercialLicenseManager(
        public_key_pem=output["verification_public_key_pem"].encode("ascii"),
        db_path=tmp_path / "usage.sqlite3",
    ).validate_license_key(output["license_token"])
    assert claims["tenant_id"] == "tenant-cli"
