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
                "cve_mapping": {
                    "strength": "Strong for CVE correlation, exploitation context, and dependency risk scoring",
                    "use_cases": ["runtime vulnerability correlation", "SBOM import into scanning platforms", "VEX advisory mapping"],
                },
                "compliance_fit": [
                    "NIST SSDF",
                    "OWASP SAMM",
                    "SLSA provenance review",
                    "DORA platform security controls",
                ],
            }
        elif normalized in {"spdx", "spdx-2", "spdx2"}:
            preferred = "SPDX"
            evidence = {
                "best_for": "license and component provenance tracking across complex ecosystems",
                "metadata_fields": ["spdxVersion", "dataLicense", "SPDXID", "name", "documentNamespace"],
                "cve_mapping": {
                    "strength": "Strong for license provenance, component lineage, and policy evidence trails",
                    "use_cases": ["license review", "component provenance", "documented supply-chain evidence"],
                },
                "compliance_fit": [
                    "NIS2 traceability",
                    "ISO 27001 software asset ownership",
                    "software bill-of-materials evidence for legal/compliance review",
                    "DORA and audit evidence pack",
                ],
            }
        else:
            preferred = "CycloneDX"
            evidence = {
                "best_for": "default release artifact planning and vulnerability correlation",
                "metadata_fields": ["bomFormat", "specVersion", "version", "metadata"],
                "cve_mapping": {
                    "strength": "Default recommendation for vulnerability-driven release gates",
                    "use_cases": ["CVE triage", "dependency risk scoring", "automated vulnerability dashboards"],
                },
                "compliance_fit": [
                    "OWASP dependency review",
                    "SLSA provenance review",
                    "platform vulnerability management",
                ],
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
            "cve_mapping": evidence["cve_mapping"],
            "compliance_fit": evidence["compliance_fit"],
            "recommendations": [
                "Generate CycloneDX for software supply-chain metadata and runtime vulnerability correlation.",
                "Use SPDX where license and provenance metadata require stronger legal/compliance detail.",
                "Keep SBOM generation and verification inside the controlled release pipeline, not as ad hoc runtime output.",
                "Map every SBOM to CVE/known risk references and attach a compliance reviewer before release promotion.",
            ],
            "verification_gate": {
                "mode": "PLAN_ONLY",
                "required": True,
                "checks": [
                    "Verify that the SBOM matches the built artifact digest and release commit.",
                    "Compare the SBOM component set against vulnerability feeds and deny critical issues for production promotion.",
                    "Confirm that the chosen SPDX or CycloneDX format is accepted by the target compliance policy and release review board.",
                ],
            },
        }

    def assess_release_verification_pipeline(self, release_stage: str = "release") -> dict[str, Any]:
        stage_name = (release_stage or "release").strip() or "release"
        return {
            "status": "PLAN_ONLY",
            "release_stage": stage_name,
            "pipeline": {
                "mode": "PLAN_ONLY_WITH_VERIFICATION_GATES",
                "gates": [
                    "Artifact signed with Cosign/Sigstore and verified against the expected certificate identity.",
                    "Attestation bundle validated with an in-toto statement and matching subject digest.",
                    "SBOM generated in the approved format and compared to the release artifact at the same commit SHA.",
                    "Vulnerability feeds are reconciled with the SBOM and critical findings block promotion.",
                    "Compliance reviewer approves the evidence package before production deployment.",
                ],
            },
            "recommendations": [
                "Treat verification as a release policy gate, not merely a report artifact.",
                "Keep enforcement logic independent from artifact generation to avoid bypasses in the pipeline.",
                "Record the evidence package for audit and maintain a clear owner for every exception.",
            ],
        }

    assess_sbom_compatibility = assess_sbom_format


class CycloneDXSPDXManager(SbomFormatManager):
    """Backward-compatible alias for SBOM format assessment."""

    def assess_sbom_compatibility(self, sbom_format: str = "CycloneDX") -> dict[str, Any]:
        return super().assess_sbom_format(sbom_format=sbom_format)
