import hashlib
import re
import shutil
from pathlib import Path
from typing import Any


_SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")
_METADATA_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,127}$")
_ISO9660_PVD_OFFSET = 0x8000


class ParrotLabPreflight:
    """Verifies a locally supplied Parrot ISO without launching it or making network calls."""

    TOOL_CANDIDATES = {
        "network": ("nmap", "masscan", "wireshark", "tshark"),
        "web": ("burpsuite", "zaproxy", "sqlmap", "gobuster", "ffuf"),
        "forensics": ("yara", "volatility3", "radare2", "binwalk", "sleuthkit"),
        "password_audit": ("john", "hashcat"),
    }

    ISOLATION_CHECKLIST = (
        "Use a disposable VM with a verified snapshot.",
        "Disable bridged networking; use no network adapter unless the lab explicitly requires one.",
        "Disable shared folders, clipboard, drag-and-drop, USB passthrough, and host integration.",
        "Do not mount host credentials, production data, or sensitive evidence.",
        "Use synthetic targets and data only; document authorization before any active testing.",
    )

    def inspect(
        self,
        iso_path: str | Path,
        expected_sha256: str,
        edition: str,
        version: str,
        architecture: str,
    ) -> dict[str, Any]:
        if not _SHA256_PATTERN.fullmatch(expected_sha256):
            raise ValueError("expected_sha256 must be exactly 64 hexadecimal characters")
        metadata = {
            "edition": edition,
            "version": version,
            "architecture": architecture,
        }
        for name, value in metadata.items():
            if not _METADATA_PATTERN.fullmatch(value):
                raise ValueError(f"{name} must be a non-empty, simple identifier")

        image_path = Path(iso_path).expanduser()
        if not image_path.is_file():
            raise ValueError("Parrot ISO path must refer to an existing file")

        digest = hashlib.sha256()
        with image_path.open("rb") as image:
            image.seek(_ISO9660_PVD_OFFSET)
            descriptor = image.read(7)
            iso9660_signature = (
                len(descriptor) == 7
                and descriptor[0] == 1
                and descriptor[1:6] == b"CD001"
                and descriptor[6] == 1
            )
            image.seek(0)
            for chunk in iter(lambda: image.read(1024 * 1024), b""):
                digest.update(chunk)
        actual_sha256 = digest.hexdigest()
        checksum_matches = actual_sha256.casefold() == expected_sha256.casefold()
        if not iso9660_signature:
            raise ValueError("The supplied file does not contain an ISO9660 primary volume descriptor")
        if not checksum_matches:
            raise ValueError("Parrot ISO SHA-256 does not match the operator-supplied expected digest")

        inventory = {
            category: [
                {"name": tool, "available": shutil.which(tool) is not None}
                for tool in tools
            ]
            for category, tools in self.TOOL_CANDIDATES.items()
        }
        return {
            "status": "CHECKSUM_MATCHED_PENDING_AUTHENTICITY_REVIEW",
            "artifact": {
                "path": str(image_path.resolve()),
                **metadata,
                "format": "ISO9660",
                "sha256": actual_sha256,
                "checksum_matches_operator_value": True,
                "checksum_source_independently_verified": False,
            },
            "host_tool_inventory": inventory,
            "lab_isolation_checklist": list(self.ISOLATION_CHECKLIST),
            "launch_performed": False,
            "network_requests_made": False,
            "limitations": (
                "A matching operator-supplied checksum does not establish publisher authenticity. "
                "Verify the checksum/signature against the official Parrot source independently. "
                "Tool availability describes this host, not the ISO contents or a running VM."
            ),
        }
