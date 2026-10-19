from __future__ import annotations

import base64
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


_MAX_JSON_BYTES = 25 * 1024 * 1024
_STATEMENT_TYPES = {
    "https://in-toto.io/Statement/v0.1",
    "https://in-toto.io/Statement/v1",
}
_SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "NEGLIGIBLE", "UNKNOWN")
_HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class SupplyChainVerificationError(ValueError):
    """Raised when supplied evidence cannot be safely verified or reviewed."""


def _read_json(path: Path, label: str) -> Any:
    try:
        if path.stat().st_size > _MAX_JSON_BYTES:
            raise SupplyChainVerificationError(
                f"{label} must not exceed {_MAX_JSON_BYTES // (1024 * 1024)} MiB"
            )
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SupplyChainVerificationError(f"Cannot read {label}: {error}") from error


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as artifact:
            for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise SupplyChainVerificationError(
            f"Cannot read artifact for digest: {error}"
        ) from error
    return digest.hexdigest()


def _verified_statement(
    bundle_path: Path,
    expected_digest: str,
    expected_predicate_type: str,
) -> dict[str, Any]:
    bundle = _read_json(bundle_path, "Cosign bundle")
    if not isinstance(bundle, dict):
        raise SupplyChainVerificationError("Cosign bundle must be a JSON object")
    envelope = bundle.get("dsseEnvelope")
    if not isinstance(envelope, dict):
        raise SupplyChainVerificationError(
            "Cosign bundle must use the Sigstore bundle format with dsseEnvelope"
        )
    payload = envelope.get("payload")
    if not isinstance(payload, str):
        raise SupplyChainVerificationError(
            "Cosign bundle DSSE envelope is missing its payload"
        )
    try:
        statement = json.loads(base64.b64decode(payload, validate=True))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SupplyChainVerificationError(
            f"Cosign bundle contains an invalid in-toto payload: {error}"
        ) from error
    if not isinstance(statement, dict):
        raise SupplyChainVerificationError("in-toto statement must be a JSON object")
    if statement.get("_type") not in _STATEMENT_TYPES:
        raise SupplyChainVerificationError("Unsupported in-toto statement type")
    if statement.get("predicateType") != expected_predicate_type:
        raise SupplyChainVerificationError(
            "in-toto predicateType does not match the requested predicate type"
        )
    subjects = statement.get("subject")
    if not isinstance(subjects, list) or not subjects:
        raise SupplyChainVerificationError(
            "in-toto statement must contain at least one subject"
        )

    subject_digests: set[str] = set()
    for subject in subjects:
        if not isinstance(subject, dict):
            raise SupplyChainVerificationError(
                "in-toto statement contains an invalid subject"
            )
        digests = subject.get("digest")
        if not isinstance(digests, dict):
            raise SupplyChainVerificationError(
                "in-toto subject is missing its digest"
            )
        sha256 = digests.get("sha256")
        if not isinstance(sha256, str) or not _HEX_SHA256.fullmatch(sha256):
            raise SupplyChainVerificationError(
                "in-toto subject must contain a lowercase SHA-256 digest"
            )
        subject_digests.add(sha256)

    if expected_digest not in subject_digests:
        raise SupplyChainVerificationError(
            "in-toto subject digest does not match the supplied artifact"
        )
    return statement


def _summarize_trivy(path: Path) -> dict[str, Any]:
    report = _read_json(path, "Trivy report")
    if not isinstance(report, dict) or not isinstance(report.get("Results"), list):
        raise SupplyChainVerificationError(
            "Trivy report must contain a Results array"
        )
    counts = {severity: 0 for severity in _SEVERITIES}
    total = 0
    for result in report["Results"]:
        if not isinstance(result, dict):
            raise SupplyChainVerificationError("Trivy Results entries must be objects")
        vulnerabilities = result.get("Vulnerabilities") or []
        if not isinstance(vulnerabilities, list):
            raise SupplyChainVerificationError(
                "Trivy Vulnerabilities must be an array"
            )
        for vulnerability in vulnerabilities:
            if not isinstance(vulnerability, dict):
                raise SupplyChainVerificationError(
                    "Trivy vulnerability entries must be objects"
                )
            severity = vulnerability.get("Severity", "UNKNOWN")
            if not isinstance(severity, str):
                raise SupplyChainVerificationError(
                    "Trivy vulnerability Severity must be a string"
                )
            normalized = severity.upper()
            if normalized not in counts:
                normalized = "UNKNOWN"
            counts[normalized] += 1
            total += 1
    return {
        "status": "REPORT_PARSED_NOT_INDEPENDENTLY_VERIFIED",
        "reported_vulnerabilities": total,
        "by_severity": counts,
        "artifact_name": report.get("ArtifactName"),
        "report_schema_version": report.get("SchemaVersion"),
    }


def _summarize_grype(path: Path) -> dict[str, Any]:
    report = _read_json(path, "Grype report")
    if not isinstance(report, dict) or not isinstance(report.get("matches"), list):
        raise SupplyChainVerificationError(
            "Grype report must contain a matches array"
        )
    counts = {severity: 0 for severity in _SEVERITIES}
    for match in report["matches"]:
        if not isinstance(match, dict):
            raise SupplyChainVerificationError("Grype matches entries must be objects")
        vulnerability = match.get("vulnerability")
        if not isinstance(vulnerability, dict):
            raise SupplyChainVerificationError(
                "Grype match must contain a vulnerability object"
            )
        severity = vulnerability.get("severity", "UNKNOWN")
        if not isinstance(severity, str):
            raise SupplyChainVerificationError(
                "Grype vulnerability severity must be a string"
            )
        normalized = severity.upper()
        if normalized not in counts:
            normalized = "UNKNOWN"
        counts[normalized] += 1
    return {
        "status": "REPORT_PARSED_NOT_INDEPENDENTLY_VERIFIED",
        "reported_vulnerabilities": len(report["matches"]),
        "by_severity": counts,
        "report_schema_version": report.get("schema"),
        "source": report.get("source"),
    }


class SupplyChainArtifactVerifier:
    """Verifies a local artifact attestation with Cosign and reviews scan reports."""

    def verify(
        self,
        *,
        artifact: Path,
        attestation_bundle: Path,
        certificate_identity: str,
        certificate_oidc_issuer: str,
        predicate_type: str,
        trivy_report: Path | None = None,
        grype_report: Path | None = None,
        cosign_command: str = "cosign",
    ) -> dict[str, Any]:
        if not artifact.is_file():
            raise SupplyChainVerificationError("Artifact must be an existing file")
        if not attestation_bundle.is_file():
            raise SupplyChainVerificationError(
                "Attestation bundle must be an existing file"
            )
        if not certificate_identity.strip() or not certificate_oidc_issuer.strip():
            raise SupplyChainVerificationError(
                "Expected certificate identity and OIDC issuer are required"
            )
        if not predicate_type.strip():
            raise SupplyChainVerificationError("Expected predicate type is required")
        if not cosign_command.strip():
            raise SupplyChainVerificationError("Cosign command must not be empty")

        artifact_digest = _file_sha256(artifact)
        command = [
            cosign_command,
            "verify-blob-attestation",
            "--new-bundle-format",
            "--bundle",
            str(attestation_bundle),
            "--certificate-identity",
            certificate_identity,
            "--certificate-oidc-issuer",
            certificate_oidc_issuer,
            "--type",
            predicate_type,
            str(artifact),
        ]
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise SupplyChainVerificationError(
                f"Cosign verification could not be completed: {error}"
            ) from error
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            if len(detail) > 2_000:
                detail = detail[:2_000] + "..."
            raise SupplyChainVerificationError(
                f"Cosign attestation verification failed: {detail or 'no error details'}"
            )

        statement = _verified_statement(
            attestation_bundle,
            artifact_digest,
            predicate_type,
        )
        scans = {
            "trivy": (
                _summarize_trivy(trivy_report)
                if trivy_report is not None
                else {"status": "NOT_PROVIDED"}
            ),
            "grype": (
                _summarize_grype(grype_report)
                if grype_report is not None
                else {"status": "NOT_PROVIDED"}
            ),
        }
        return {
            "status": "ATTESTATION_VERIFIED",
            "artifact": {
                "path": str(artifact),
                "sha256": artifact_digest,
            },
            "attestation": {
                "signature_status": "VERIFIED_BY_COSIGN",
                "certificate_identity": certificate_identity,
                "certificate_oidc_issuer": certificate_oidc_issuer,
                "predicate_type": statement["predicateType"],
                "statement_type": statement["_type"],
                "subject_digest_match": True,
            },
            "scan_reports": scans,
            "limitations": (
                "Cosign verifies the supplied attestation against the requested "
                "certificate identity and OIDC issuer. Scan reports are operator-"
                "supplied, structurally parsed only, and not cryptographically "
                "authenticated or bound to the artifact by this command. Missing "
                "reports are not treated as clean scans. Vulnerability counts are "
                "not a security verdict or a policy gate."
            ),
        }
