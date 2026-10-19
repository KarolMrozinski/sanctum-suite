#!/usr/bin/env python3
"""Compare CycloneDX component inventories for release review."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _read_document(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    document = json.loads(raw)
    if not isinstance(document, dict):
        raise ValueError(f"{path} must contain a CycloneDX JSON object")
    if not isinstance(document.get("components"), list):
        raise ValueError(f"{path} must contain a CycloneDX components array")
    return document, hashlib.sha256(raw).hexdigest()


def _components(document: dict[str, Any]) -> dict[str, set[str]]:
    inventory: dict[str, set[str]] = {}
    pending = list(document["components"])
    while pending:
        component = pending.pop()
        if not isinstance(component, dict):
            raise ValueError("CycloneDX components must be JSON objects")
        name = component.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("CycloneDX component is missing its name")
        purl = component.get("purl")
        group = component.get("group")
        if isinstance(purl, str) and purl:
            package, separator, qualifiers = purl.partition("?")
            package_type, slash, package_name = package[4:].partition("/")
            package_name, version_separator, _version = package_name.rpartition("@")
            if not version_separator:
                package_name = package[4:].partition("/")[2]
            identity = f"pkg:{package_type}/{package_name}"
            if separator:
                identity += f"?{qualifiers}"
            if not slash or not package_type or not package_name:
                identity = purl
        else:
            identity = (
                f"{group}:{name}" if isinstance(group, str) and group else name
            )
        version = component.get("version", "")
        if not isinstance(version, str):
            raise ValueError(f"CycloneDX component {identity!r} has an invalid version")
        inventory.setdefault(identity, set()).add(version)
        nested = component.get("components", [])
        if not isinstance(nested, list):
            raise ValueError(f"CycloneDX component {identity!r} has invalid nested components")
        pending.extend(nested)
    return inventory


def compare_documents(
    current: dict[str, Any], baseline: dict[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    current_inventory = _components(current)
    baseline_inventory = _components(baseline)
    current_names = set(current_inventory)
    baseline_names = set(baseline_inventory)
    shared_names = current_names & baseline_names
    return {
        "added": [
            {"component": name, "versions": sorted(current_inventory[name])}
            for name in sorted(current_names - baseline_names)
        ],
        "removed": [
            {"component": name, "versions": sorted(baseline_inventory[name])}
            for name in sorted(baseline_names - current_names)
        ],
        "version_changes": [
            {
                "component": name,
                "from": sorted(baseline_inventory[name]),
                "to": sorted(current_inventory[name]),
            }
            for name in sorted(shared_names)
            if current_inventory[name] != baseline_inventory[name]
        ],
    }


def compare_files(current_path: Path, baseline_path: Path | None) -> dict[str, Any]:
    current, current_digest = _read_document(current_path)
    if baseline_path is None:
        return {
            "schema": "sanctum-sbom-diff-v1",
            "status": "no_baseline_sbom",
            "current_sha256": current_digest,
            "baseline_sha256": None,
            "changes": None,
        }
    baseline, baseline_digest = _read_document(baseline_path)
    return {
        "schema": "sanctum-sbom-diff-v1",
        "status": "compared",
        "current_sha256": current_digest,
        "baseline_sha256": baseline_digest,
        "changes": compare_documents(current, baseline),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current", required=True, type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    report = compare_files(arguments.current, arguments.baseline)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
