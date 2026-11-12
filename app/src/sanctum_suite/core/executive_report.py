import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_MAX_REPORT_BYTES = 25 * 1024 * 1024
_HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_READINESS_DOMAIN_STATUSES = {
    "NOT_ASSESSED",
    "OPERATOR_REPORTED_READY",
    "GAPS_REPORTED",
    "INCOMPLETE",
    "REVIEW_REQUIRED",
}
_LIMITATIONS = [
    "This report aggregates supplied reports; it does not independently rerun or authenticate them.",
    "Readiness checks are operator declarations. A collected evidence status is not a security verdict, certification, or regulatory compliance determination.",
    "Trivy and Grype reports are structurally summarized only; they are not cryptographically authenticated or bound to the artifact.",
    "OPA results show test outcomes only and do not prove policy completeness or correct deployment.",
]


class ExecutiveReportError(ValueError):
    """Raised when an input report is missing, malformed, or inconsistent."""


def _read_report(path: Path, label: str) -> Any:
    try:
        if path.stat().st_size > _MAX_REPORT_BYTES:
            raise ExecutiveReportError(
                f"{label} must not exceed {_MAX_REPORT_BYTES // (1024 * 1024)} MiB"
            )
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ExecutiveReportError(f"Cannot read {label}: {error}") from error


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ExecutiveReportError(f"{label} must be a JSON object")
    return value


def load_executive_report_inputs(
    readiness_path: Path,
    supply_chain_path: Path,
    opa_test_path: Path,
) -> dict[str, Any]:
    readiness = _require_object(
        _read_report(readiness_path, "readiness report"), "Readiness report"
    )
    readiness_status = readiness.get("status")
    if not isinstance(readiness_status, str) or readiness_status not in {
        "REVIEW_REQUIRED",
        "NOT_ASSESSED",
    }:
        raise ExecutiveReportError("Readiness report has an unsupported status")
    readiness_summary = _require_object(
        readiness.get("summary"), "Readiness report summary"
    )
    readiness_domains = _require_object(
        readiness.get("domains"), "Readiness report domains"
    )
    for key in (
        "domains_assessed",
        "domains_not_assessed",
        "operator_reported_ready",
        "operator_reported_gaps",
        "incomplete_assessments",
    ):
        if (
            not isinstance(readiness_summary.get(key), int)
            or isinstance(readiness_summary[key], bool)
            or readiness_summary[key] < 0
        ):
            raise ExecutiveReportError(
                f"Readiness report summary.{key} must be a non-negative integer"
            )
    if any(
        not isinstance(domain, dict)
        or not isinstance(domain.get("status"), str)
        or domain["status"] not in _READINESS_DOMAIN_STATUSES
        for domain in readiness_domains.values()
    ):
        raise ExecutiveReportError("Readiness report contains an invalid domain status")
    assessed = [
        domain
        for domain in readiness_domains.values()
        if domain["status"] != "NOT_ASSESSED"
    ]
    expected_summary = {
        "domains_assessed": len(assessed),
        "domains_not_assessed": len(readiness_domains) - len(assessed),
        "operator_reported_ready": sum(
            domain["status"] == "OPERATOR_REPORTED_READY" for domain in assessed
        ),
        "operator_reported_gaps": sum(
            domain["status"] == "GAPS_REPORTED" for domain in assessed
        ),
        "incomplete_assessments": sum(
            domain["status"] == "INCOMPLETE" for domain in assessed
        ),
    }
    if any(readiness_summary[key] != value for key, value in expected_summary.items()):
        raise ExecutiveReportError(
            "Readiness report summary does not match its domain results"
        )
    expected_status = "REVIEW_REQUIRED" if assessed else "NOT_ASSESSED"
    if readiness["status"] != expected_status:
        raise ExecutiveReportError(
            "Readiness report status does not match its domain results"
        )

    supply_chain = _require_object(
        _read_report(supply_chain_path, "supply-chain report"),
        "Supply-chain report",
    )
    if supply_chain.get("status") != "ATTESTATION_VERIFIED":
        raise ExecutiveReportError(
            "Supply-chain report must have status ATTESTATION_VERIFIED"
        )
    attestation = _require_object(
        supply_chain.get("attestation"), "Supply-chain attestation"
    )
    if (
        attestation.get("signature_status") != "VERIFIED_BY_COSIGN"
        or attestation.get("subject_digest_match") is not True
    ):
        raise ExecutiveReportError(
            "Supply-chain report does not contain verified Cosign subject evidence"
        )
    artifact = _require_object(
        supply_chain.get("artifact"), "Supply-chain artifact"
    )
    if not isinstance(artifact.get("sha256"), str) or not _HEX_SHA256.fullmatch(
        artifact["sha256"]
    ):
        raise ExecutiveReportError(
            "Supply-chain artifact must contain a lowercase SHA-256 digest"
        )
    scan_reports = _require_object(
        supply_chain.get("scan_reports"), "Supply-chain scan_reports"
    )
    for scanner in ("trivy", "grype"):
        scan = _require_object(
            scan_reports.get(scanner), f"Supply-chain {scanner} report"
        )
        scan_status = scan.get("status")
        if not isinstance(scan_status, str) or scan_status not in {
            "NOT_PROVIDED",
            "REPORT_PARSED_NOT_INDEPENDENTLY_VERIFIED",
        }:
            raise ExecutiveReportError(
                f"Supply-chain {scanner} report has an unsupported status"
            )
        if scan_status == "REPORT_PARSED_NOT_INDEPENDENTLY_VERIFIED" and (
            not isinstance(scan.get("reported_vulnerabilities"), int)
            or isinstance(scan["reported_vulnerabilities"], bool)
            or scan["reported_vulnerabilities"] < 0
        ):
            raise ExecutiveReportError(
                f"Supply-chain {scanner} report must contain a non-negative "
                "reported_vulnerabilities count"
            )

    opa_tests = _read_report(opa_test_path, "OPA test report")
    if not isinstance(opa_tests, list):
        raise ExecutiveReportError("OPA test report must be a JSON array")
    failures = []
    for index, test in enumerate(opa_tests):
        if (
            not isinstance(test, dict)
            or not isinstance(test.get("package"), str)
            or not isinstance(test.get("name"), str)
        ):
            raise ExecutiveReportError(
                f"OPA test report entry {index} must contain package and name strings"
            )
        failed = test.get("fail", False)
        if not isinstance(failed, bool):
            raise ExecutiveReportError(
                f"OPA test report entry {index} fail must be a boolean"
            )
        error = test.get("error")
        if error is not None and not isinstance(error, str):
            raise ExecutiveReportError(
                f"OPA test report entry {index} error must be a string"
            )
        if failed or error is not None:
            if error is None:
                error = "OPA reported test failure"
            failures.append(
                {
                    "package": test["package"],
                    "name": test["name"],
                    "error": error,
                }
            )

    return {
        "readiness": readiness,
        "supply_chain": supply_chain,
        "opa_tests": {
            "status": (
                "PASSED"
                if opa_tests and not failures
                else "FAILED"
                if failures
                else "NOT_ASSESSED"
            ),
            "total": len(opa_tests),
            "passed": len(opa_tests) - len(failures),
            "failed": len(failures),
            "failures": failures,
        },
    }


def build_executive_report(inputs: dict[str, Any]) -> dict[str, Any]:
    readiness = inputs["readiness"]
    readiness_summary = readiness["summary"]
    domains = readiness["domains"]
    supply_chain = inputs["supply_chain"]
    scans = supply_chain["scan_reports"]
    opa_tests = inputs["opa_tests"]

    readiness_needs_review = (
        readiness.get("status") != "REVIEW_REQUIRED"
        or readiness_summary["domains_assessed"] == 0
        or readiness_summary["domains_not_assessed"] > 0
        or readiness_summary["operator_reported_gaps"] > 0
        or readiness_summary["incomplete_assessments"] > 0
        or any(
            domain["status"] != "OPERATOR_REPORTED_READY"
            for domain in domains.values()
        )
    )
    scans_complete = (
        scans["trivy"]["status"] == "REPORT_PARSED_NOT_INDEPENDENTLY_VERIFIED"
    )
    review_required = (
        readiness_needs_review
        or not scans_complete
        or opa_tests["status"] != "PASSED"
    )

    return {
        "report_type": "SANCTUM_EXECUTIVE_SECURITY_EVIDENCE",
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z"),
        "status": "REVIEW_REQUIRED" if review_required else "EVIDENCE_COLLECTED",
        "summary": {
            "readiness_status": readiness["status"],
            "readiness_domains_assessed": readiness_summary["domains_assessed"],
            "readiness_domains_not_assessed": readiness_summary["domains_not_assessed"],
            "readiness_operator_reported_ready": readiness_summary[
                "operator_reported_ready"
            ],
            "readiness_operator_reported_gaps": readiness_summary[
                "operator_reported_gaps"
            ],
            "readiness_incomplete_assessments": readiness_summary[
                "incomplete_assessments"
            ],
            "attestation_status": supply_chain["attestation"]["signature_status"],
            "artifact_sha256": supply_chain.get("artifact", {}).get("sha256"),
            "trivy_status": scans["trivy"]["status"],
            "trivy_reported_vulnerabilities": scans["trivy"].get(
                "reported_vulnerabilities"
            ),
            "grype_status": scans["grype"]["status"],
            "grype_reported_vulnerabilities": scans["grype"].get(
                "reported_vulnerabilities"
            ),
            "opa_test_status": opa_tests["status"],
            "opa_tests_total": opa_tests["total"],
            "opa_tests_passed": opa_tests["passed"],
            "opa_tests_failed": opa_tests["failed"],
        },
        "evidence": {
            "readiness": readiness,
            "supply_chain": supply_chain,
            "opa_tests": opa_tests,
        },
        "limitations": _LIMITATIONS,
    }


def render_executive_report_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# SANCTUM Executive Security Evidence Report",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "This report consolidates supplied security evidence for audit review. "
        "It is not a compliance or security verdict.",
        "",
        "## Summary",
        "",
        "| Area | Result | Details |",
        "| --- | --- | --- |",
        (
            "| Security readiness | "
            f"`{summary['readiness_status']}` | "
            f"{summary['readiness_domains_assessed']} assessed, "
            f"{summary['readiness_domains_not_assessed']} not assessed, "
            f"{summary['readiness_operator_reported_gaps']} reported gaps, "
            f"{summary['readiness_incomplete_assessments']} incomplete |"
        ),
        (
            "| Supply-chain attestation | "
            f"`{summary['attestation_status']}` | "
            f"Artifact SHA-256: `{summary['artifact_sha256'] or 'not supplied'}` |"
        ),
        (
            "| Trivy | "
            f"`{summary['trivy_status']}` | "
            f"{summary['trivy_reported_vulnerabilities'] if summary['trivy_reported_vulnerabilities'] is not None else 'not supplied'} "
            "reported vulnerabilities |"
        ),
        (
            "| Grype | "
            f"`{summary['grype_status']}` | "
            f"{summary['grype_reported_vulnerabilities'] if summary['grype_reported_vulnerabilities'] is not None else 'not supplied'} "
            "reported vulnerabilities |"
        ),
        (
            "| OPA policy tests | "
            f"`{summary['opa_test_status']}` | "
            f"{summary['opa_tests_passed']}/{summary['opa_tests_total']} passed; "
            f"{summary['opa_tests_failed']} failed |"
        ),
        "",
        "## Limitations",
        "",
    ]
    lines.extend(f"- {limitation}" for limitation in report["limitations"])
    if report["evidence"]["opa_tests"]["failures"]:
        lines.extend(["", "## OPA test failures", ""])
        lines.extend(
            f"- `{failure['package']}.{failure['name']}`: {failure['error']}"
            for failure in report["evidence"]["opa_tests"]["failures"]
        )
    return "\n".join(lines) + "\n"
