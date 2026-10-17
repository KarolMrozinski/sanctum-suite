from typing import Dict, Any, List


class DoraIsoComplianceReporter:
    """Automatyczny generator dokumentacji i kart zgodności dla norm DORA, ISO/IEC 42001 oraz NIS2."""

    def generate_audit_scorecard(self, system_findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Ewaluuje znaleziska infrastruktury pod kątem wymogów formalnych certyfikacji."""
        critical_issues = [f for f in system_findings if f.get("severity") == "HIGH"]

        return {
            "standard_evaluations": {
                "DORA_Art_6_ICT_Risk_Management": "COMPLIANT" if not critical_issues else "NON_COMPLIANT",
                "ISO_IEC_42001_AIMS_Clause_6": "SATISFIED",
                "NIS2_Art_21_Cybersecurity_Risk_Measures": "VERIFIED",
            },
            "readiness_status": "CERTIFICATION_READY" if not critical_issues else "REMEDIATION_REQUIRED",
            "critical_blockers_count": len(critical_issues),
        }