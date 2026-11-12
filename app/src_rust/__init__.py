"""Embedded Rust module bundle for SANCTUM-SUITE."""

from __future__ import annotations

from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _PACKAGE_DIR.parent
_SOURCE_DIR = _PROJECT_ROOT / "src-rust"


def module_directory() -> Path:
    return _SOURCE_DIR


def list_modules() -> list[str]:
    if not _SOURCE_DIR.exists():
        return []
    modules_dir = _SOURCE_DIR / "src"
    if not modules_dir.exists():
        return []
    modules = {path.stem for path in modules_dir.iterdir() if path.is_file() and path.suffix.lower() == ".rs"}
    return sorted(modules)


__all__ = ["module_directory", "list_modules"]
