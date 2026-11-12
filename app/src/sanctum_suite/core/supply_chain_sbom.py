from typing import Any


class SupplyChainSbomAuditEngine:
    """Reports SBOM analysis as unperformed until a scanner is configured."""

    def audit_software_bill_of_materials(self, sbom_manifest_path: str) -> dict[str, Any]:
        return {
            "manifest_path": sbom_manifest_path,
            "status": "NOT_SCANNED",
            "scanner_configured": False,
            "dependencies_scanned": None,
            "vulnerable_components_found": None,
            "supply_chain_risk_score": None,
            "compliance_status": "NOT_ASSESSED",
            "components": None,
        }
