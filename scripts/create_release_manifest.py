#!/usr/bin/env python3
"""Create a digest inventory that binds release files to their SBOMs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


_REVISION = re.compile(r"^[0-9a-fA-F]{40,64}$")
_IMAGE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
_SUBJECTS = {
    "python": "python/",
    "dashboard": "dashboard/",
    "container": "container/",
}
_SBOMS = {
    "python": "sbom/sanctum-python-sbom.cdx.json",
    "dashboard": "sbom/sanctum-dashboard-sbom.cdx.json",
    "container": "sbom/sanctum-container-sbom.cdx.json",
}


def _digest(path: Path) -> tuple[str, int]:
    hasher = hashlib.sha256()
    size = 0
    with path.open("rb") as artifact:
        while chunk := artifact.read(1024 * 1024):
            hasher.update(chunk)
            size += len(chunk)
    return hasher.hexdigest(), size


def create_manifest(
    directory: Path,
    *,
    release_tag: str,
    source_revision: str,
    container_image_id: str,
) -> dict[str, Any]:
    if not _REVISION.fullmatch(source_revision):
        raise ValueError("source revision must be a 40-64 character Git commit")
    root = directory.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("release directory must be a directory")
    files = sorted(root.rglob("*"))
    if any(path.is_symlink() for path in files):
        raise ValueError("release bundle must not contain symbolic links")
    artifacts = []
    for path in files:
        if path.is_dir() or path.name == "release-manifest.json":
            continue
        if not path.is_file():
            raise ValueError("release bundle may contain only regular files")
        sha256, size_bytes = _digest(path)
        artifacts.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": sha256,
                "size_bytes": size_bytes,
            }
        )
    paths = {artifact["path"] for artifact in artifacts}
    subjects: dict[str, dict[str, Any]] = {}
    for name, directory_prefix in _SUBJECTS.items():
        product_paths = sorted(
            path for path in paths if path.startswith(directory_prefix)
        )
        if not product_paths:
            raise ValueError(f"release is missing {name} artifacts")
        sbom_path = _SBOMS[name]
        if sbom_path not in paths:
            raise ValueError(f"release is missing the {name} SBOM")
        subjects[name] = {"sbom": sbom_path, "artifacts": product_paths}
    if not any(path.startswith("reports/") for path in paths):
        raise ValueError("release is missing SBOM comparison reports")
    if not _IMAGE_ID.fullmatch(container_image_id):
        raise ValueError("container image ID must be a sha256 digest")
    return {
        "schema": "sanctum-release-manifest-v1",
        "release_tag": release_tag,
        "source_revision": source_revision.lower(),
        "container_image": {
            "reference": f"sanctum-suite:{release_tag}",
            "image_id": container_image_id,
        },
        "sbom_subjects": subjects,
        "artifacts": artifacts,
    }


def verify_manifest(directory: Path) -> dict[str, Any]:
    root = directory.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("release directory must be a directory")
    manifest_path = root / "release-manifest.json"
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("schema") != "sanctum-release-manifest-v1":
        raise ValueError("unsupported or invalid release manifest")
    artifacts = document.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("release manifest must list artifacts")
    expected: dict[str, tuple[str, int]] = {}
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise ValueError("release manifest contains an invalid artifact entry")
        relative_path = artifact.get("path")
        path = PurePosixPath(relative_path) if isinstance(relative_path, str) else None
        if (
            path is None
            or path.is_absolute()
            or "\\" in relative_path
            or any(part in {"", ".", ".."} for part in path.parts)
            or relative_path == "release-manifest.json"
            or relative_path in expected
        ):
            raise ValueError("release manifest contains an unsafe or duplicate path")
        sha256 = artifact.get("sha256")
        size = artifact.get("size_bytes")
        if (
            not isinstance(sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", sha256)
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 0
        ):
            raise ValueError("release manifest contains an invalid digest or size")
        expected[relative_path] = (sha256, size)

    actual_paths: set[str] = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("release bundle must not contain symbolic links")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError("release bundle may contain only regular files")
        relative_path = path.relative_to(root).as_posix()
        if relative_path == "release-manifest.json":
            continue
        actual_paths.add(relative_path)
        if relative_path not in expected:
            raise ValueError(f"release contains an unlisted artifact: {relative_path}")
        actual_digest = _digest(path)
        if actual_digest != expected[relative_path]:
            raise ValueError(f"release artifact digest mismatch: {relative_path}")
    if actual_paths != set(expected):
        missing = sorted(set(expected) - actual_paths)
        raise ValueError(f"release is missing listed artifacts: {', '.join(missing)}")
    return document


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--release-tag")
    parser.add_argument("--source-revision")
    parser.add_argument("--container-image-id")
    arguments = parser.parse_args()
    if arguments.verify:
        if any(
            value is not None
            for value in (
                arguments.release_tag,
                arguments.source_revision,
                arguments.container_image_id,
            )
        ):
            parser.error("--verify cannot be combined with manifest creation options")
        verify_manifest(arguments.directory)
    else:
        if not all(
            (
                arguments.release_tag,
                arguments.source_revision,
                arguments.container_image_id,
            )
        ):
            parser.error(
                "manifest creation requires --release-tag, --source-revision, and --container-image-id"
            )
        manifest = create_manifest(
            arguments.directory,
            release_tag=arguments.release_tag,
            source_revision=arguments.source_revision,
            container_image_id=arguments.container_image_id,
        )
        output = arguments.directory / "release-manifest.json"
        output.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
