from __future__ import annotations

import base64
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


_MANIFEST_NAME = "MANIFEST.json"
_SIGNATURE_NAME = "MANIFEST.sig"
_FORMAT = "sanctum-offline-release-v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REVISION = re.compile(r"^[0-9a-fA-F]{40,64}$")
_SENSITIVE_DIRECTORIES = {
    ".git",
    ".keys",
    ".venv",
    "node_modules",
    "secrets",
    "__pycache__",
}
_PRIVATE_KEY_MARKERS = (
    b"-----BEGIN PRIVATE KEY-----",
    b"-----BEGIN ENCRYPTED PRIVATE KEY-----",
    b"-----BEGIN RSA PRIVATE KEY-----",
    b"-----BEGIN EC PRIVATE KEY-----",
    b"-----BEGIN OPENSSH PRIVATE KEY-----",
)


def public_key_fingerprint(public_key: Ed25519PublicKey) -> str:
    public_key_der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return hashlib.sha256(public_key_der).hexdigest()


def _hash_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as artifact:
        while chunk := artifact.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _reject_sensitive_artifact(path: Path, relative_path: str) -> None:
    if any(part.lower() in _SENSITIVE_DIRECTORIES for part in Path(relative_path).parts):
        raise ValueError("Release bundle must not contain secret or development directories")
    name = path.name.lower()
    if name.startswith(".env") or path.suffix.lower() in {
        ".pem",
        ".key",
        ".p12",
        ".pfx",
    }:
        raise ValueError("Release bundle must not contain environment or key files")
    with path.open("rb") as artifact:
        header = artifact.read(4096)
    if any(marker in header for marker in _PRIVATE_KEY_MARKERS):
        raise ValueError("Release bundle must not contain private-key material")


def _artifact_inventory(directory: Path) -> list[dict[str, Any]]:
    root = directory.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Release bundle path must be a directory")
    artifacts = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Release bundles must not contain symbolic links")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError("Release bundles may contain only regular files")
        relative_path = path.relative_to(root).as_posix()
        if relative_path in {_MANIFEST_NAME, _SIGNATURE_NAME}:
            continue
        _reject_sensitive_artifact(path, relative_path)
        posix_path = PurePosixPath(relative_path)
        if (
            posix_path.is_absolute()
            or "\\" in relative_path
            or any(part in {"", ".", ".."} for part in posix_path.parts)
            or any(ord(character) < 32 for character in relative_path)
        ):
            raise ValueError("Release bundle contains an unsafe artifact path")
        sha256, size = _hash_file(path)
        artifacts.append(
            {
                "path": relative_path,
                "sha256": sha256,
                "size_bytes": size,
            }
        )
    if not artifacts:
        raise ValueError("Release bundle must contain at least one artifact")
    return artifacts


def create_release_manifest(
    directory: str | Path,
    *,
    source_revision: str,
    private_key: Ed25519PrivateKey,
) -> dict[str, Any]:
    root = Path(directory)
    if not isinstance(source_revision, str) or not _REVISION.fullmatch(source_revision):
        raise ValueError("source_revision must be a 40-64 character Git revision")
    manifest = {
        "format": _FORMAT,
        "source_revision": source_revision.lower(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "signer_sha256": public_key_fingerprint(private_key.public_key()),
        "artifacts": _artifact_inventory(root),
    }
    canonical_manifest = json.dumps(
        manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    signature = base64.b64encode(private_key.sign(canonical_manifest))
    (root / _MANIFEST_NAME).write_bytes(canonical_manifest)
    (root / _SIGNATURE_NAME).write_bytes(signature + b"\n")
    return manifest


def _validate_manifest(document: Any, trusted_fingerprint: str) -> list[dict[str, Any]]:
    if not isinstance(document, dict) or document.get("format") != _FORMAT:
        raise ValueError("Unsupported or invalid release manifest")
    revision = document.get("source_revision")
    if not isinstance(revision, str) or not _REVISION.fullmatch(revision):
        raise ValueError("Release manifest source_revision is invalid")
    created_at = document.get("created_at")
    if not isinstance(created_at, str):
        raise ValueError("Release manifest created_at is invalid")
    try:
        parsed_created_at = datetime.fromisoformat(created_at)
    except ValueError as error:
        raise ValueError("Release manifest created_at is invalid") from error
    if parsed_created_at.tzinfo is None:
        raise ValueError("Release manifest created_at must include a timezone")
    if document.get("signer_sha256") != trusted_fingerprint:
        raise ValueError("Release manifest signer fingerprint does not match trusted key")
    artifacts = document.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("Release manifest must list at least one artifact")
    seen_paths: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise ValueError("Release manifest contains an invalid artifact entry")
        relative_path = artifact.get("path")
        if not isinstance(relative_path, str):
            raise ValueError("Release manifest artifact path is invalid")
        posix_path = PurePosixPath(relative_path)
        if (
            posix_path.is_absolute()
            or "\\" in relative_path
            or any(part in {"", ".", ".."} for part in posix_path.parts)
            or relative_path in {_MANIFEST_NAME, _SIGNATURE_NAME}
            or any(ord(character) < 32 for character in relative_path)
            or relative_path in seen_paths
        ):
            raise ValueError("Release manifest contains an unsafe or duplicate path")
        if (
            not isinstance(artifact.get("sha256"), str)
            or not _SHA256.fullmatch(artifact["sha256"])
        ):
            raise ValueError("Release manifest artifact SHA-256 is invalid")
        size = artifact.get("size_bytes")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise ValueError("Release manifest artifact size is invalid")
        seen_paths.add(relative_path)
    return artifacts


def verify_release_manifest(
    directory: str | Path,
    *,
    public_key: Ed25519PublicKey,
    expected_signer_fingerprint: str,
) -> dict[str, Any]:
    root = Path(directory).resolve(strict=True)
    if (
        not isinstance(expected_signer_fingerprint, str)
        or not _SHA256.fullmatch(expected_signer_fingerprint)
    ):
        raise ValueError("expected_signer_fingerprint must be a SHA-256 hex digest")
    actual_fingerprint = public_key_fingerprint(public_key)
    if actual_fingerprint != expected_signer_fingerprint:
        raise ValueError("Trusted public key fingerprint does not match expectation")
    manifest_path = root / _MANIFEST_NAME
    signature_path = root / _SIGNATURE_NAME
    if manifest_path.is_symlink() or signature_path.is_symlink():
        raise ValueError("Release manifest and signature must not be symbolic links")
    try:
        manifest_bytes = manifest_path.read_bytes()
        signature = base64.b64decode(signature_path.read_bytes().strip(), validate=True)
    except (OSError, ValueError) as error:
        raise ValueError("Release manifest or signature is missing or invalid") from error
    try:
        public_key.verify(signature, manifest_bytes)
    except InvalidSignature as error:
        raise ValueError("Release manifest signature verification failed") from error
    try:
        document = json.loads(manifest_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Signed release manifest is not valid UTF-8 JSON") from error

    expected_artifacts = _validate_manifest(document, actual_fingerprint)
    actual_artifacts = _artifact_inventory(root)
    if actual_artifacts != expected_artifacts:
        raise ValueError(
            "Release bundle artifact inventory, size, or digest does not match manifest"
        )
    return document
