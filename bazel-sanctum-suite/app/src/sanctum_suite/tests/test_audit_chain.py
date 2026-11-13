import hashlib
import json
import uuid

from typer.testing import CliRunner

from sanctum_suite import main
from sanctum_suite.core.audit_chain import (
    canonical_json,
    create_audit_checkpoint,
    verify_audit_checkpoint,
)
from sanctum_suite.core.signer import SecurityReportSigner


def _make_signed_checkpoint(tmp_path):
    signer = SecurityReportSigner(key_dir=str(tmp_path / "keys"))
    archive = tmp_path / "archive"
    event_id = str(uuid.uuid4())
    key = f"api-access/2026/10/19/{event_id}.json"
    body = canonical_json(
        {
            "event_id": event_id,
            "event_type": "request_started",
            "occurred_at": "2026-10-19T10:00:00+00:00",
        }
    )
    record_path = archive / key
    record_path.parent.mkdir(parents=True)
    record_path.write_bytes(body)
    checkpoint = create_audit_checkpoint(
        bucket="sanctum-audit-worm",
        records=[
            {
                "key": key,
                "version_id": "worm-version-1",
                "record_sha256": hashlib.sha256(body).hexdigest(),
            }
        ],
        signer=signer,
        created_at="2026-10-19T10:00:01+00:00",
    )
    checkpoint_path = tmp_path / "checkpoint.json"
    checkpoint_path.write_bytes(canonical_json(checkpoint))
    return signer, archive, checkpoint, checkpoint_path


def test_signed_audit_checkpoint_verifies_offline(tmp_path):
    signer, archive, checkpoint, checkpoint_path = _make_signed_checkpoint(tmp_path)
    result = CliRunner().invoke(
        main.app,
        [
            "audit-verify",
            str(checkpoint_path),
            "--archive-directory",
            str(archive),
            "--public-key-file",
            str(signer.public_key_path),
            "--pqc-public-key-file",
            str(signer.pqc_public_key_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Verified 1 audit object version" in result.output
    assert checkpoint["chain_head_sha256"] != "0" * 64


def test_legacy_rsa_checkpoint_remains_verifiable(tmp_path):
    signer, archive, checkpoint, _checkpoint_path = _make_signed_checkpoint(tmp_path)
    legacy = {key: value for key, value in checkpoint.items() if key != "signature"}
    legacy["signature"] = {
        "algorithm": "RSA-PSS-SHA256",
        "signer_sha256": signer.public_key_fingerprint,
        "signature_base64": signer.sign_bytes(canonical_json(legacy)),
    }

    result = verify_audit_checkpoint(
        checkpoint=legacy,
        archive_directory=archive,
        public_key_pem=signer.public_key_path.read_bytes(),
    )

    assert result["record_count"] == 1


def test_audit_verifier_rejects_tampered_archive_record(tmp_path):
    signer, archive, _checkpoint, checkpoint_path = _make_signed_checkpoint(tmp_path)
    record_path = next(archive.rglob("*.json"))
    record = json.loads(record_path.read_bytes())
    record["event_type"] = "request_completed"
    record_path.write_bytes(canonical_json(record))

    result = CliRunner().invoke(
        main.app,
        [
            "audit-verify",
            str(checkpoint_path),
            "--archive-directory",
            str(archive),
            "--public-key-file",
            str(signer.public_key_path),
            "--pqc-public-key-file",
            str(signer.pqc_public_key_path),
        ],
    )

    assert result.exit_code != 0
    assert "digest or schema does not match" in result.output


def test_audit_verifier_rejects_modified_hash_link(tmp_path):
    signer, archive, checkpoint, checkpoint_path = _make_signed_checkpoint(tmp_path)
    checkpoint["records"][0]["previous_hash"] = "f" * 64
    checkpoint_path.write_bytes(canonical_json(checkpoint))

    result = CliRunner().invoke(
        main.app,
        [
            "audit-verify",
            str(checkpoint_path),
            "--archive-directory",
            str(archive),
            "--public-key-file",
            str(signer.public_key_path),
            "--pqc-public-key-file",
            str(signer.pqc_public_key_path),
        ],
    )

    assert result.exit_code != 0
    assert "signature verification failed" in result.output


def test_audit_checkpoint_cli_exports_and_signs_snapshot(monkeypatch, tmp_path):
    signer = SecurityReportSigner(key_dir=str(tmp_path / "keys"))
    event_id = str(uuid.uuid4())
    key = f"api-access/2026/10/19/{event_id}.json"
    body = canonical_json(
        {
            "event_id": event_id,
            "event_type": "request_completed",
            "occurred_at": "2026-10-19T10:00:00+00:00",
        }
    )

    class SnapshotStore:
        bucket = "sanctum-audit-worm"

        def read_audit_records(self):
            return [
                {
                    "key": key,
                    "version_id": "worm-version-1",
                    "record_sha256": hashlib.sha256(body).hexdigest(),
                    "body": body,
                }
            ]

    monkeypatch.setattr(main, "MinioImmutableAuditStore", SnapshotStore)
    monkeypatch.setattr(main, "SecurityReportSigner", lambda: signer)
    archive = tmp_path / "export"
    checkpoint_path = tmp_path / "signed-checkpoint.json"
    result = CliRunner().invoke(
        main.app,
        [
            "audit-checkpoint",
            "--archive-directory",
            str(archive),
            "--checkpoint-file",
            str(checkpoint_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert (archive / key).read_bytes() == body
    checkpoint = json.loads(checkpoint_path.read_bytes())
    assert checkpoint["record_count"] == 1
