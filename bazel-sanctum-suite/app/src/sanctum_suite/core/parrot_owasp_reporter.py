from typing import Any


class ParrotOwaspReporter:
    """Summarizes caller-supplied assessment states without certifying environments."""

    def generate_compliance_scorecard(
        self,
        owasp_data: dict[str, Any],
        nist_data: dict[str, Any],
        environment: dict[str, str | None] | None = None,
    ) -> dict[str, Any]:
        return {
            "report_title": "SANCTUM-SUITE Assessment Summary",
            "environment": environment or {"os_name": None, "os_version": None},
            "owasp_status": owasp_data.get("status", "NOT_ASSESSED"),
            "nist_status": nist_data.get("status", "NOT_ASSESSED"),
            "resilience_index": None,
            "certified_for_production": False,
            "limitations": (
                "This summary is not a certification, production-readiness determination, "
                "or substitute for independent framework assessment."
            ),
        }
