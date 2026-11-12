from typing import Any


class DoraIsoComplianceReporter:
    """Summarizes findings for review without asserting certification readiness."""

    def generate_audit_scorecard(self, system_findings: list[dict[str, Any]]) -> dict[str, Any]:
        findings_requiring_review = [
            finding
            for finding in system_findings
            if str(finding.get("severity", "")).upper() in {"HIGH", "CRITICAL"}
        ]
        return {
            "standard_evaluations": {
                "DORA_Art_6_ICT_Risk_Management": "NOT_ASSESSED",
                "ISO_IEC_42001_AIMS_Clause_6": "NOT_ASSESSED",
                "NIS2_Art_21_Cybersecurity_Risk_Measures": "NOT_ASSESSED",
            },
            "readiness_status": "NOT_ASSESSED",
            "findings_requiring_review": len(findings_requiring_review),
            "limitations": (
                "Technical findings do not determine organizational applicability, "
                "control effectiveness, or certification readiness."
            ),
        }
