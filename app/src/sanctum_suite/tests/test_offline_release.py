import base64
import hashlib
import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from typer.testing import CliRunner

from sanctum_suite.core.offline_release import (
    create_release_manifest,
    public_key_fingerprint,
    verify_release_manifest,
)
from sanctum_suite.main import app


def _keys():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    fingerprint = public_key_fingerprint(public_key)
    return private_key, public_key, fingerprint


def test_signed_offline_manifest_verifies_exact_release_inventory(tmp_path):
    artifact_dir = tmp_path / "bundle"
    artifact_dir.mkdir()
    image = artifact_dir / "sanctum-image.tar"
    image.write_bytes(b"OCI image archive")
    sbom = artifact_dir / "sbom.json"
    sbom.write_text('{"components":[]}', encoding="utf-8")
    private_key, public_key, fingerprint = _keys()

    manifest = create_release_manifest(
        artifact_dir,
        source_revision="a" * 40,
        private_key=private_key,
    )
    verified = verify_release_manifest(
        artifact_dir,
        public_key=public_key,
        expected_signer_fingerprint=fingerprint,
    )

    assert verified == manifest
    assert [artifact["path"] for artifact in verified["artifacts"]] == [
        "sanctum-image.tar",
        "sbom.json",
    ]
    assert verified["artifacts"][0]["sha256"] == hashlib.sha256(
        b"OCI image archive"
    ).hexdigest()
    assert (artifact_dir / "MANIFEST.json").is_file()
    assert (artifact_dir / "MANIFEST.sig").is_file()


def test_verifier_rejects_modified_added_and_removed_artifacts(tmp_path):
    artifact_dir = tmp_path / "bundle"
    artifact_dir.mkdir()
    artifact = artifact_dir / "package.whl"
    artifact.write_bytes(b"original")
    private_key, public_key, fingerprint = _keys()
    create_release_manifest(
        artifact_dir,
        source_revision="b" * 40,
        private_key=private_key,
    )

    artifact.write_bytes(b"modified")
    with pytest.raises(ValueError, match="inventory, size, or digest"):
        verify_release_manifest(
            artifact_dir,
            public_key=public_key,
            expected_signer_fingerprint=fingerprint,
        )

    artifact.write_bytes(b"original")
    (artifact_dir / "unexpected.txt").write_text("extra", encoding="utf-8")
    with pytest.raises(ValueError, match="inventory, size, or digest"):
        verify_release_manifest(
            artifact_dir,
            public_key=public_key,
            expected_signer_fingerprint=fingerprint,
        )

    (artifact_dir / "unexpected.txt").unlink()
    artifact.unlink()
    with pytest.raises(ValueError, match="at least one artifact"):
        verify_release_manifest(
            artifact_dir,
            public_key=public_key,
            expected_signer_fingerprint=fingerprint,
        )


def test_verifier_rejects_untrusted_key_and_manifest_tampering(tmp_path):
    artifact_dir = tmp_path / "bundle"
    artifact_dir.mkdir()
    (artifact_dir / "image.tar").write_bytes(b"image")
    private_key, public_key, fingerprint = _keys()
    _, other_public_key, other_fingerprint = _keys()
    create_release_manifest(
        artifact_dir,
        source_revision="c" * 40,
        private_key=private_key,
    )

    with pytest.raises(ValueError, match="fingerprint does not match"):
        verify_release_manifest(
            artifact_dir,
            public_key=other_public_key,
            expected_signer_fingerprint=fingerprint,
        )
    with pytest.raises(ValueError, match="Trusted public key"):
        verify_release_manifest(
            artifact_dir,
            public_key=public_key,
            expected_signer_fingerprint=other_fingerprint,
        )

    manifest_path = artifact_dir / "MANIFEST.json"
    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8").replace(
            '"source_revision":"cccc', '"source_revision":"dddd'
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="signature verification failed"):
        verify_release_manifest(
            artifact_dir,
            public_key=public_key,
            expected_signer_fingerprint=fingerprint,
        )


def test_release_manifest_rejects_unsafe_artifact_paths(tmp_path):
    artifact_dir = tmp_path / "bundle"
    artifact_dir.mkdir()
    (artifact_dir / "image.tar").write_bytes(b"image")
    private_key, public_key, fingerprint = _keys()
    create_release_manifest(
        artifact_dir,
        source_revision="d" * 40,
        private_key=private_key,
    )
    manifest_path = artifact_dir / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"][0]["path"] = "../outside"
    manifest_bytes = json.dumps(
        manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    manifest_path.write_bytes(manifest_bytes)
    (artifact_dir / "MANIFEST.sig").write_bytes(
        base64.b64encode(private_key.sign(manifest_bytes))
    )

    with pytest.raises(ValueError, match="unsafe or duplicate path"):
        verify_release_manifest(
            artifact_dir,
            public_key=public_key,
            expected_signer_fingerprint=fingerprint,
        )


def test_release_manifest_refuses_sensitive_files(tmp_path):
    artifact_dir = tmp_path / "bundle"
    artifact_dir.mkdir()
    (artifact_dir / "image.tar").write_bytes(b"image")
    (artifact_dir / "operator.pem").write_text(
        "-----BEGIN PRIVATE KEY-----", encoding="ascii"
    )
    private_key, _, _ = _keys()

    with pytest.raises(ValueError, match="environment or key files"):
        create_release_manifest(
            artifact_dir,
            source_revision="f" * 40,
            private_key=private_key,
        )


def test_offline_release_cli_creates_and_verifies_bundle(tmp_path):
    artifact_dir = tmp_path / "bundle"
    artifact_dir.mkdir()
    (artifact_dir / "oci-image.tar").write_bytes(b"container image")
    private_key, public_key, fingerprint = _keys()
    private_key_file = tmp_path / "signing-key.pem"
    private_key_file.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    public_key_file = tmp_path / "trusted-key.pem"
    public_key_file.write_bytes(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    runner = CliRunner()

    created = runner.invoke(
        app,
        [
            "offline-release-create",
            str(artifact_dir),
            "--source-revision",
            "e" * 40,
            "--private-key-file",
            str(private_key_file),
        ],
    )
    assert created.exit_code == 0, created.output
    assert fingerprint in created.output

    verified = runner.invoke(
        app,
        [
            "offline-release-verify",
            str(artifact_dir),
            "--public-key-file",
            str(public_key_file),
            "--expected-signer-fingerprint",
            fingerprint,
        ],
    )
    assert verified.exit_code == 0, verified.output
    assert "Verified 1 artifact(s)" in verified.output


def test_offline_release_cli_rejects_signing_key_inside_bundle(tmp_path):
    artifact_dir = tmp_path / "bundle"
    artifact_dir.mkdir()
    (artifact_dir / "image.tar").write_bytes(b"container image")
    private_key = Ed25519PrivateKey.generate()
    private_key_file = artifact_dir / "signing-key.pem"
    private_key_file.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    result = CliRunner().invoke(
        app,
        [
            "offline-release-create",
            str(artifact_dir),
            "--source-revision",
            "a" * 40,
            "--private-key-file",
            str(private_key_file),
        ],
    )

    assert result.exit_code != 0
    assert "must be stored outside the bundle" in result.output
