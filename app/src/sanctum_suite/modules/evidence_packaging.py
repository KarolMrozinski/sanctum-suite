from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


class AuditEvidenceBundle:
    """Creates a review-friendly evidence archive for external auditors."""

    def __init__(self, audit_id: str, scope: str, *, generated_by: str = "sanctum-suite") -> None:
        self.audit_id = audit_id
        self.scope = scope
        self.generated_by = generated_by
        self.generated_at = datetime.now(timezone.utc).isoformat()
        self.files: list[dict[str, str]] = []

    def add_file(self, path: str | Path, *, kind: str, description: str = "") -> None:
        file_path = Path(path)
        payload = file_path.read_bytes() if file_path.exists() else b""
        self.files.append(
            {
                "path": str(file_path),
                "kind": kind,
                "description": description,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": str(len(payload)),
            }
        )

    def add_files(self, paths: Iterable[str | Path], *, kind: str, description: str = "") -> None:
        for item in paths:
            self.add_file(item, kind=kind, description=description)

    def as_dict(self) -> dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "scope": self.scope,
            "generated_by": self.generated_by,
            "generated_at": self.generated_at,
            "files": self.files,
        }

    def write_manifest(self, directory: str | Path) -> Path:
        root = Path(directory)
        root.mkdir(parents=True, exist_ok=True)
        manifest_path = root / f"{self.audit_id}-manifest.json"
        manifest_path.write_text(json.dumps(self.as_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return manifest_path


EvidencePackageGenerator = AuditEvidenceBundle
