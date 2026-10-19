from collections.abc import Mapping
from typing import Any

from sanctum_suite.core.post_quantum_pqc import (
    PostQuantumCryptographicAssuranceEngine,
)


_CHECKS = {
    "ebpf": (
        "kernel_compatibility_checked",
        "verifier_tests_passed",
        "hook_coverage_reviewed",
        "fail_mode_documented",
        "performance_tested",
        "detach_rollback_tested",
    ),
    "rust": (
        "cargo_lock_reviewed",
        "cargo_audit_passed",
        "unsafe_code_reviewed",
        "sbom_available",
    ),
    "spiffe": (
        "trust_domain_configured",
        "svid_rotation_tested",
        "workload_api_access_controlled",
        "mtls_enforced",
        "authorization_policy_reviewed",
    ),
}
_ALLOWED_SECTIONS = {*_CHECKS, "cryptography"}
_LIMITATIONS = (
    "The report evaluates operator-supplied declarations only. It does not inspect "
    "a kernel, Rust project, SPIRE server or workload, deployed cryptographic "
    "protocol, or implementation; reported checks are not independently verified. "
    "This is not a security assessment, migration recommendation, or certification."
)


class SecurityReadinessAudit:
    """Summarizes operator-reported readiness for selected security technologies."""

    def audit(self, declaration: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(declaration, Mapping):
            raise ValueError("Input must be a JSON object")

        unknown_sections = set(declaration) - _ALLOWED_SECTIONS
        if unknown_sections:
            names = ", ".join(sorted(str(name) for name in unknown_sections))
            raise ValueError(f"Unknown readiness section(s): {names}")

        domains: dict[str, dict[str, Any]] = {}
        for section, required_checks in _CHECKS.items():
            if section not in declaration:
                domains[section] = {
                    "status": "NOT_ASSESSED",
                    "checks": {},
                    "missing_checks": list(required_checks),
                }
                continue

            section_data = declaration[section]
            if not isinstance(section_data, Mapping):
                raise ValueError(f"{section} must be an object")
            unknown_checks = set(section_data) - set(required_checks)
            if unknown_checks:
                names = ", ".join(sorted(str(name) for name in unknown_checks))
                raise ValueError(f"Unknown {section} check(s): {names}")

            checks: dict[str, dict[str, Any]] = {}
            missing_checks: list[str] = []
            for check in required_checks:
                if check not in section_data:
                    missing_checks.append(check)
                    continue
                value = section_data[check]
                if not isinstance(value, bool):
                    raise ValueError(f"{section}.{check} must be a boolean")
                checks[check] = {
                    "reported": value,
                    "status": (
                        "OPERATOR_REPORTED_PASS"
                        if value
                        else "OPERATOR_REPORTED_GAP"
                    ),
                }

            if missing_checks:
                status = "INCOMPLETE"
            elif any(not result["reported"] for result in checks.values()):
                status = "GAPS_REPORTED"
            else:
                status = "OPERATOR_REPORTED_READY"
            domains[section] = {
                "status": status,
                "checks": checks,
                "missing_checks": missing_checks,
            }

        if "cryptography" not in declaration:
            domains["cryptography"] = {
                "status": "NOT_ASSESSED",
                "algorithms": [],
                "review_counts": None,
            }
        else:
            crypto_inventory = declaration["cryptography"]
            if not isinstance(crypto_inventory, Mapping):
                raise ValueError("cryptography must be an object")
            unknown_crypto_fields = set(crypto_inventory) - {"inventory"}
            if unknown_crypto_fields:
                names = ", ".join(
                    sorted(str(name) for name in unknown_crypto_fields)
                )
                raise ValueError(f"Unknown cryptography field(s): {names}")
            inventory = crypto_inventory.get("inventory")
            if not isinstance(inventory, list) or len(inventory) > 1_000:
                raise ValueError(
                    "cryptography.inventory must be an array with at most 1000 entries"
                )
            crypto_report = PostQuantumCryptographicAssuranceEngine().audit_cryptographic_primitives(
                inventory
            )
            domains["cryptography"] = {
                "status": (
                    "NOT_ASSESSED"
                    if not inventory
                    else "REVIEW_REQUIRED"
                ),
                "algorithms": crypto_report.get("algorithms", []),
                "review_counts": crypto_report.get("review_counts"),
            }

        assessed = [
            domain
            for domain in domains.values()
            if domain["status"] != "NOT_ASSESSED"
        ]
        return {
            "status": "REVIEW_REQUIRED" if assessed else "NOT_ASSESSED",
            "assessment_scope": "OPERATOR_SUPPLIED_DECLARATIONS",
            "domains": domains,
            "summary": {
                "domains_assessed": len(assessed),
                "domains_not_assessed": len(domains) - len(assessed),
                "operator_reported_ready": sum(
                    domain["status"] == "OPERATOR_REPORTED_READY"
                    for domain in domains.values()
                ),
                "operator_reported_gaps": sum(
                    domain["status"] == "GAPS_REPORTED"
                    for domain in domains.values()
                ),
                "incomplete_assessments": sum(
                    domain["status"] == "INCOMPLETE"
                    for domain in domains.values()
                ),
            },
            "limitations": _LIMITATIONS,
        }
