import hashlib

import pytest

from sanctum_suite.core.parrot_lab import ParrotLabPreflight


def create_iso(path):
    image = bytearray(0x8006)
    image[0x8000:0x8007] = b"\x01CD001\x01"
    path.write_bytes(image)
    return path


def test_parrot_lab_preflight_verifies_iso_and_reports_non_executing_inventory(
    tmp_path,
):
    iso_path = create_iso(tmp_path / "parrot-security.iso")
    expected_sha256 = hashlib.sha256(iso_path.read_bytes()).hexdigest()

    result = ParrotLabPreflight().inspect(
        iso_path=iso_path,
        expected_sha256=expected_sha256,
        edition="Security",
        version="operator-selected",
        architecture="amd64",
    )

    assert result["status"] == "CHECKSUM_MATCHED_PENDING_AUTHENTICITY_REVIEW"
    assert result["artifact"]["format"] == "ISO9660"
    assert result["artifact"]["checksum_matches_operator_value"] is True
    assert result["artifact"]["checksum_source_independently_verified"] is False
    assert set(result["host_tool_inventory"]) == {
        "network",
        "web",
        "forensics",
        "password_audit",
    }
    assert result["lab_isolation_checklist"]
    assert result["launch_performed"] is False
    assert result["network_requests_made"] is False


@pytest.mark.parametrize(
    ("expected_sha256", "message"),
    [
        ("not-a-digest", "64 hexadecimal characters"),
        ("0" * 64, "does not match"),
    ],
)
def test_parrot_lab_preflight_rejects_invalid_or_mismatched_digest(
    tmp_path, expected_sha256, message
):
    iso_path = create_iso(tmp_path / "parrot.iso")

    with pytest.raises(ValueError, match=message):
        ParrotLabPreflight().inspect(
            iso_path=iso_path,
            expected_sha256=expected_sha256,
            edition="Security",
            version="operator-selected",
            architecture="amd64",
        )


def test_parrot_lab_preflight_rejects_non_iso(tmp_path):
    invalid_image = tmp_path / "not-an-iso"
    invalid_image.write_bytes(b"not an ISO")
    digest = hashlib.sha256(invalid_image.read_bytes()).hexdigest()

    with pytest.raises(ValueError, match="ISO9660"):
        ParrotLabPreflight().inspect(
            iso_path=invalid_image,
            expected_sha256=digest,
            edition="Security",
            version="operator-selected",
            architecture="amd64",
        )


def test_parrot_lab_preflight_rejects_unsafe_metadata(tmp_path):
    iso_path = create_iso(tmp_path / "parrot.iso")
    digest = hashlib.sha256(iso_path.read_bytes()).hexdigest()

    with pytest.raises(ValueError, match="version"):
        ParrotLabPreflight().inspect(
            iso_path=iso_path,
            expected_sha256=digest,
            edition="Security",
            version="2026/10",
            architecture="amd64",
        )
