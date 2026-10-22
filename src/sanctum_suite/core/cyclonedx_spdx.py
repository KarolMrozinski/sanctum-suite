from __future__ import annotations

from typing import Any


class SbomFormatManager:
    """Models CycloneDX and SPDX SBOM usage as a planning-only recommendation engine."""

    def assess_sbom_format(self, sbom_format: str = "CycloneDX") -> dict[str, Any]:
        requested_format = (sbom_format or "CycloneDX").strip() or "CycloneDX"
        normalized = requested_format.lower()

        if normalized in {"cyclonedx", "cdx"}:
            preferred = "CycloneDX"
            evidence = {
                "best_for": "application and dependency inventory with VEX and vulnerability context",
                "metadata_fields": ["bomFormat", "specVersion", "serialNumber", "version", "metadata"],
            }
        elif normalized in {"spdx", "spdx-2", "spdx2"}:
            preferred = "SPDX"
            evidence = {
                "best_for": "license and component provenance tracking across complex ecosystems",
                "metadata_fields": ["spdxVersion", "dataLicense", "SPDXID", "name", "documentNamespace"],
            }
        else:
            preferred = "CycloneDX"
            evidence = {
                "best_for": "default release artifact planning and vulnerability correlation",
                "metadata_fields": ["bomFormat", "specVersion", "version", "metadata"],
            }

        return {
            "status": "PLAN_ONLY",
            "preferred_format": preferred,
            "requested_format": requested_format,
            "supported_formats": ["CycloneDX", "SPDX"],
            "best_fit": evidence,
            "required_fields": [
                "component identities",
                "dependency graph or package list",
                "licenses or provenance metadata",
                "vulnerability references when available",
            ],
            "recommendations": [
                "Generate CycloneDX for software supply-chain metadata and runtime vulnerability correlation.",
                "Use SPDX where license and provenance metadata require stronger legal/compliance detail.",
                "Keep SBOM generation and verification inside the controlled release pipeline, not as ad hoc runtime output.",
            ],
        }

    assess_sbom_compatibility = assess_sbom_format


class CycloneDXSPDXManager(SbomFormatManager):
    """Backward-compatible alias for SBOM format assessment."""

    def assess_sbom_compatibility(self, sbom_format: str = "CycloneDX") -> dict[str, Any]:
        return super().assess_sbom_format(sbom_format=sbom_format)
