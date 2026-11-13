from typing import Any


class NistSp80053ControlAssurance:
    """Creates an unassessed review summary; it does not probe or enforce controls."""

    def audit_security_controls(
        self,
        assessment_records: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        records = assessment_records or []
        return {
            "framework": "NIST SP 800-53 Rev. 5",
            "status": "NOT_ASSESSED",
            "controls_checked": 0,
            "assessment_records_supplied": len(records),
            "zta_architecture": "NOT_ASSESSED",
            "limitations": (
                "This summary does not test deployed controls, validate a Zero Trust "
                "architecture, or establish DoD/NIST compliance."
            ),
        }
