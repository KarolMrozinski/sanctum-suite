import json

import pytest

from scripts.compare_sbom import compare_documents, compare_files
from scripts.create_release_manifest import create_manifest, verify_manifest


def test_compare_documents_reports_added_removed_and_changed_versions():
    baseline = {
        "components": [
            {"name": "kept", "purl": "pkg:pypi/kept@1.0", "version": "1.0"},
            {"name": "changed", "purl": "pkg:pypi/changed@1.0", "version": "1.0"},
            {"name": "removed", "purl": "pkg:pypi/removed@1.0", "version": "1.0"},
        ]
    }
    current = {
        "components": [
            {"name": "kept", "purl": "pkg:pypi/kept@1.0", "version": "1.0"},
            {"name": "changed", "purl": "pkg:pypi/changed@2.0", "version": "2.0"},
            {"name": "added", "purl": "pkg:pypi/added@1.0", "version": "1.0"},
        ]
    }

    assert compare_documents(current, baseline) == {
        "added": [{"component": "pkg:pypi/added", "versions": ["1.0"]}],
        "removed": [{"component": "pkg:pypi/removed", "versions": ["1.0"]}],
        "version_changes": [
            {
                "component": "pkg:pypi/changed",
                "from": ["1.0"],
                "to": ["2.0"],
            }
        ],
    }


def test_compare_files_marks_missing_baseline_as_explicit(tmp_path):
    current = tmp_path / "current.json"
    current.write_text(json.dumps({"components": []}), encoding="utf-8")

    report = compare_files(current, None)

    assert report["status"] == "no_baseline_sbom"
    assert report["baseline_sha256"] is None
    assert report["changes"] is None


def test_compare_files_rejects_malformed_sbom(tmp_path):
    malformed = tmp_path / "bad.json"
    malformed.write_text('{"components": "not-an-array"}', encoding="utf-8")

    with pytest.raises(ValueError, match="components array"):
        compare_files(malformed, None)


def test_create_manifest_records_hashes_and_sbom_subjects(tmp_path):
    for path in (
        "python/package.whl",
        "dashboard/dashboard.tar.gz",
        "container/image.tar",
        "sbom/sanctum-python-sbom.cdx.json",
        "sbom/sanctum-dashboard-sbom.cdx.json",
        "sbom/sanctum-container-sbom.cdx.json",
        "reports/python-sbom-diff.json",
    ):
        artifact = tmp_path / path
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_bytes(path.encode("utf-8"))

    manifest = create_manifest(
        tmp_path,
        release_tag="v1.2.3",
        source_revision="a" * 40,
        container_image_id="sha256:" + "b" * 64,
    )

    assert manifest["source_revision"] == "a" * 40
    assert manifest["sbom_subjects"]["python"] == {
        "sbom": "sbom/sanctum-python-sbom.cdx.json",
        "artifacts": ["python/package.whl"],
    }
    assert all(len(artifact["sha256"]) == 64 for artifact in manifest["artifacts"])
    (tmp_path / "release-manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    assert verify_manifest(tmp_path)["release_tag"] == "v1.2.3"


def test_verify_manifest_rejects_changed_or_unlisted_files(tmp_path):
    for path in (
        "python/package.whl",
        "dashboard/dashboard.tar.gz",
        "container/image.tar",
        "sbom/sanctum-python-sbom.cdx.json",
        "sbom/sanctum-dashboard-sbom.cdx.json",
        "sbom/sanctum-container-sbom.cdx.json",
        "reports/python-sbom-diff.json",
    ):
        artifact = tmp_path / path
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_bytes(path.encode("utf-8"))
    manifest = create_manifest(
        tmp_path,
        release_tag="v1.2.3",
        source_revision="a" * 40,
        container_image_id="sha256:" + "b" * 64,
    )
    (tmp_path / "release-manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    (tmp_path / "python/package.whl").write_bytes(b"modified")

    with pytest.raises(ValueError, match="digest mismatch"):
        verify_manifest(tmp_path)


def test_create_manifest_rejects_missing_sbom(tmp_path):
    for path in (
        "python/package.whl",
        "dashboard/dashboard.tar.gz",
        "container/image.tar",
        "sbom/sanctum-python-sbom.cdx.json",
        "sbom/sanctum-dashboard-sbom.cdx.json",
        "reports/python-sbom-diff.json",
    ):
        artifact = tmp_path / path
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_bytes(b"test")

    with pytest.raises(ValueError, match="container SBOM"):
        create_manifest(
            tmp_path,
            release_tag="v1.2.3",
            source_revision="a" * 40,
            container_image_id="sha256:" + "b" * 64,
        )
