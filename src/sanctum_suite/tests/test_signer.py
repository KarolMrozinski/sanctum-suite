import base64
import hashlib
import json

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from typer.testing import CliRunner

from sanctum_suite import main as cli_main
from sanctum_suite.core.signer import SecurityReportSigner


def _write_key_pair(directory, private_key):
    private_path = directory / "report-private.pem"
    public_path = directory / "report-public.pem"
    private_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    public_path.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return private_path, public_path


def test_development_signer_generates_and_uses_a_matching_key_pair(
    monkeypatch, tmp_path
):
    monkeypatch.delenv("SANCTUM_ENVIRONMENT", raising=False)
    signer = SecurityReportSigner(key_dir=str(tmp_path / ".keys"))
    report = tmp_path / "report.pdf"
    report.write_bytes(b"test report")

    signature_base64 = signer.sign_file(str(report))
    signature = base64.b64decode(signature_base64)
    public_key = serialization.load_pem_public_key(signer.public_key_path.read_bytes())
    public_key.verify(
        signature,
        report.read_bytes(),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )
    assert signer.public_key_fingerprint
    signer.verify_bytes(
        report.read_bytes(),
        signature_base64,
        signer.public_key_path.read_bytes(),
    )


def test_report_signer_rejects_tampered_report(monkeypatch, tmp_path):
    monkeypatch.delenv("SANCTUM_ENVIRONMENT", raising=False)
    signer = SecurityReportSigner(key_dir=str(tmp_path / ".keys"))
    signature = signer.sign_bytes(b"original report")

    with pytest.raises(ValueError, match="verification failed"):
        signer.verify_bytes(
            b"changed report",
            signature,
            signer.public_key_path.read_bytes(),
        )


def test_report_verify_cli_checks_digest_and_signature(monkeypatch, tmp_path):
    monkeypatch.delenv("SANCTUM_ENVIRONMENT", raising=False)
    signer = SecurityReportSigner(key_dir=str(tmp_path / ".keys"))
    unsigned = {"catalog_version": "1.1.0", "certification_status": "NOT_ASSESSED"}
    unsigned_bytes = json.dumps(
        unsigned, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    report = {
        **unsigned,
        "report_sha256": hashlib.sha256(unsigned_bytes).hexdigest(),
    }
    signed_bytes = json.dumps(
        report, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    report["report_signature"] = {
        "algorithm": "RSA-PSS-SHA256",
        "signer_sha256": signer.public_key_fingerprint,
        "signature_base64": signer.sign_bytes(signed_bytes),
    }
    report_path = tmp_path / "signed-report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    result = CliRunner().invoke(
        cli_main.app,
        [
            "report-verify",
            str(report_path),
            "--public-key-file",
            str(signer.public_key_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Verified report" in result.output

    report["certification_status"] = "COMPLIANT"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    tampered = CliRunner().invoke(
        cli_main.app,
        [
            "report-verify",
            str(report_path),
            "--public-key-file",
            str(signer.public_key_path),
        ],
    )
    assert tampered.exit_code != 0
    assert "digest does not match" in tampered.output


def test_production_signer_requires_explicit_key_files(monkeypatch):
    monkeypatch.setenv("SANCTUM_ENVIRONMENT", "air-gapped")
    monkeypatch.delenv("SANCTUM_REPORT_SIGNING_PRIVATE_KEY_FILE", raising=False)
    monkeypatch.delenv("SANCTUM_REPORT_SIGNING_PUBLIC_KEY_FILE", raising=False)

    with pytest.raises(ValueError, match="requires explicit report-signing"):
        SecurityReportSigner()


def test_production_signer_uses_an_operator_supplied_key_pair(
    monkeypatch, tmp_path
):
    private_path, public_path = _write_key_pair(
        tmp_path, rsa.generate_private_key(public_exponent=65537, key_size=2048)
    )
    monkeypatch.setenv("SANCTUM_ENVIRONMENT", "air-gapped")
    monkeypatch.setenv("SANCTUM_REPORT_SIGNING_PRIVATE_KEY_FILE", str(private_path))
    monkeypatch.setenv("SANCTUM_REPORT_SIGNING_PUBLIC_KEY_FILE", str(public_path))
    signer = SecurityReportSigner()
    report = tmp_path / "report.pdf"
    report.write_bytes(b"air-gapped report")

    signature = base64.b64decode(signer.sign_file(str(report)))
    public_key = serialization.load_pem_public_key(public_path.read_bytes())
    public_key.verify(
        signature,
        report.read_bytes(),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )


def test_report_signer_rejects_mismatched_key_pair(monkeypatch, tmp_path):
    private_path, _ = _write_key_pair(
        tmp_path, rsa.generate_private_key(public_exponent=65537, key_size=2048)
    )
    other_public = tmp_path / "other-public.pem"
    other_public.write_bytes(
        rsa.generate_private_key(public_exponent=65537, key_size=2048)
        .public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    monkeypatch.setenv("SANCTUM_ENVIRONMENT", "production")
    monkeypatch.setenv("SANCTUM_REPORT_SIGNING_PRIVATE_KEY_FILE", str(private_path))
    monkeypatch.setenv("SANCTUM_REPORT_SIGNING_PUBLIC_KEY_FILE", str(other_public))

    with pytest.raises(ValueError, match="does not match"):
        SecurityReportSigner()


def test_development_signer_rejects_a_partial_key_pair(monkeypatch, tmp_path):
    monkeypatch.delenv("SANCTUM_ENVIRONMENT", raising=False)
    key_dir = tmp_path / ".keys"
    key_dir.mkdir()
    (key_dir / "sanctum_private.pem").write_text("incomplete", encoding="ascii")

    with pytest.raises(ValueError, match="incomplete"):
        SecurityReportSigner(key_dir=str(key_dir))
