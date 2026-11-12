from typing import Any


class TempestSdip27EmissionsAuditor:
    """Records references for qualified TEMPEST review without simulating measurements."""

    def audit_enclave_emissions(
        self,
        enclave_zone: str,
        measurement_report_ref: str | None = None,
        accredited_assessment_ref: str | None = None,
    ) -> dict[str, Any]:
        zone = enclave_zone.strip()
        if not zone:
            raise ValueError("An enclave zone label is required")
        references = {
            "measurement_report": measurement_report_ref,
            "accredited_assessment": accredited_assessment_ref,
        }
        missing_evidence = [
            name
            for name, reference in references.items()
            if not isinstance(reference, str) or not reference.strip()
        ]
        return {
            "enclave_zone": zone,
            "framework_reference": "NATO SDIP-27 (edition and applicability to be established by qualified authority)",
            "status": "NOT_ASSESSED",
            "evidence_readiness": (
                "REFERENCES_RECORDED_PENDING_QUALIFIED_REVIEW"
                if not missing_evidence
                else "REQUIRED_QUALIFIED_EVIDENCE_MISSING"
            ),
            "evidence_references_supplied": {
                name: isinstance(reference, str) and bool(reference.strip())
                for name, reference in references.items()
            },
            "missing_evidence_types": missing_evidence,
            "limitations": (
                "This module performs no RF measurement or accreditation and cannot "
                "determine TEMPEST classification or compliance. Evidence references "
                "do not establish report authenticity, assessor accreditation, or applicability."
            ),
        }
