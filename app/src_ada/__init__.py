"""Embedded Ada module bundle for SANCTUM-SUITE.

This package exposes the companion ``src-ada`` source tree as a Python-visible module so it is
included in the runtime and can be inspected without losing the original source layout.
"""

from __future__ import annotations

from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _PACKAGE_DIR.parent
_SOURCE_DIR = _PROJECT_ROOT / "src-ada"


def module_directory() -> Path:
    return _SOURCE_DIR


def list_modules() -> list[str]:
    if not _SOURCE_DIR.exists():
        return []
    modules = {path.stem for path in _SOURCE_DIR.iterdir() if path.is_file() and path.suffix.lower() in {".adb", ".ads"}}
    return sorted(modules)


__all__ = ["module_directory", "list_modules"]
