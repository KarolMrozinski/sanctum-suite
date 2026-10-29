"""Registry for companion language modules bundled alongside the Python package."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

_LANGUAGE_SPECS: dict[str, dict[str, Any]] = {
    "ada": {"directory": "src-ada", "suffixes": {".adb", ".ads"}},
    "apl": {"directory": "src-apl", "suffixes": {".apl"}},
    "hals": {"directory": "src-hals", "suffixes": {".hals"}},
    "rust": {"directory": "src-rust", "suffixes": {".rs"}, "subdir": "src"},
}


@dataclass(frozen=True)
class LanguageModuleRecord:
    """Normalized description for a companion-language module discovered in the repo."""

    capability_id: str
    language: str
    module_name: str
    source_dir: str
    source_path: str
    status: str = "DISCOVERED"


class CapabilityRegistry:
    """Discover and expose all companion modules as runtime capability records."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root is not None else Path(__file__).resolve().parents[3]

    def discover(self) -> list[LanguageModuleRecord]:
        return discover_language_module_capabilities(self.root)

    def as_capability_map(self) -> dict[str, dict[str, str]]:
        records = self.discover()
        return {record.capability_id: {
            "language": record.language,
            "module_name": record.module_name,
            "source_dir": record.source_dir,
            "source_path": record.source_path,
            "status": record.status,
        } for record in records}


def discover_language_module_capabilities(root: Path | str | None = None) -> list[LanguageModuleRecord]:
    """Return every companion-language module as a capability record."""

    project_root = Path(root) if root is not None else Path(__file__).resolve().parents[3]
    records: list[LanguageModuleRecord] = []

    for language, spec in _LANGUAGE_SPECS.items():
        source_dir = project_root / spec["directory"]
        if not source_dir.exists():
            continue

        search_dir = source_dir
        if spec.get("subdir"):
            search_dir = source_dir / spec["subdir"]
        if not search_dir.exists():
            continue

        discovered_by_module: dict[tuple[str, str], LanguageModuleRecord] = {}
        for item in sorted(search_dir.iterdir(), key=lambda path: path.name.lower()):
            if not item.is_file():
                continue
            if item.suffix.lower() not in spec["suffixes"]:
                continue
            module_name = item.stem
            key = (language, module_name)
            if key in discovered_by_module:
                continue
            capability_id = f"security-capability:{language}-module:{module_name.lower()}"
            discovered_by_module[key] = LanguageModuleRecord(
                capability_id=capability_id,
                language=language,
                module_name=module_name,
                source_dir=str(source_dir),
                source_path=str(item),
                status="DISCOVERED",
            )

        records.extend(sorted(discovered_by_module.values(), key=lambda record: record.module_name.lower()))

    return sorted(records, key=lambda record: (record.language, record.module_name.lower()))


__all__ = ["CapabilityRegistry", "LanguageModuleRecord", "discover_language_module_capabilities"]
