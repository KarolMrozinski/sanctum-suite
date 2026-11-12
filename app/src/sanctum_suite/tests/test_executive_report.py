import base64
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

from sanctum_suite import main as cli_main


_PREDICATE_TYPE = "https://slsa.dev/provenance/v1"


def _write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def _write_bundle(path: Path, digest: str) -> None:
    statement = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": "release.tar.gz", "digest": {"sha256": digest}}],
        "predicateType": _PREDICATE_TYPE,
        "predicate": {"buildType": "https://example.test/build"},
    }
    payload = base64.b64encode(json.dumps(statement).encode("utf-8")).decode("ascii")
    _write_json(
        path,
        {
            "dsseEnvelope": {
                "payload": payload,
                "payloadType": "application/vnd.in-toto+json",
                "signatures": [{"sig": "test-only-mocked-signature"}],
            }
        },
    )


def _readiness_declaration() -> dict:
    return {
        "ebpf": {
            "kernel_compatibility_checked": True,
            "verifier_tests_passed": True,
            "hook_coverage_reviewed": True,
            "fail_mode_documented": True,
            "performance_tested": True,
            "detach_rollback_tested": True,
        },
        "rust": {
            "cargo_lock_reviewed": True,
            "cargo_audit_passed": True,
            "unsafe_code_reviewed": True,
            "sbom_available": True,
        },
        "spiffe": {
            "trust_domain_configured": True,
            "svid_rotation_tested": True,
            "workload_api_access_controlled": True,
            "mtls_enforced": True,
            "authorization_policy_reviewed": True,
        },
    }


def test_readiness_supply_chain_and_executive_cli_end_to_end(tmp_path, monkeypatch):
    readiness_input = tmp_path / "readiness-input.json"
    readiness_output = tmp_path / "readiness-report.json"
    _write_json(readiness_input, _readiness_declaration())

    readiness_result = CliRunner().invoke(
        cli_main.app,
        [
            "security-readiness",
            "--input",
            str(readiness_input),
        ],
    )
    assert readiness_result.exit_code == 0, readiness_result.output
    _write_json(readiness_output, json.loads(readiness_result.stdout))

    artifact = tmp_path / "release.tar.gz"
    artifact.write_bytes(b"offline release test artifact")
    bundle = tmp_path / "attestation.json"
    _write_bundle(bundle, hashlib.sha256(artifact.read_bytes()).hexdigest())
    trivy = tmp_path / "trivy.json"
    _write_json(
        trivy,
        {
            "SchemaVersion": 2,
            "ArtifactName": "release.tar.gz",
            "Results": [{"Vulnerabilities": []}],
        },
    )
    grype = tmp_path / "grype.json"
    _write_json(grype, {"schema": "6.0.0", "matches": []})
    monkeypatch.setattr(
        "sanctum_suite.core.supply_chain_verify.subprocess.run",
        lambda command, **kwargs: SimpleNamespace(
            returncode=0, stdout="Verified OK", stderr=""
        ),
    )

    supply_chain_result = CliRunner().invoke(
        cli_main.app,
        [
            "supply-chain-verify",
            "--artifact",
            str(artifact),
            "--attestation-bundle",
            str(bundle),
            "--certificate-identity",
            "https://github.com/example/repo/.github/workflows/release.yml@refs/tags/v1",
            "--certificate-oidc-issuer",
            "https://token.actions.githubusercontent.com",
            "--predicate-type",
            _PREDICATE_TYPE,
            "--trivy-report",
            str(trivy),
            "--grype-report",
            str(grype),
        ],
    )
    assert supply_chain_result.exit_code == 0, supply_chain_result.output
    supply_chain_output = tmp_path / "supply-chain-report.json"
    _write_json(supply_chain_output, json.loads(supply_chain_result.stdout))

    opa_output = tmp_path / "opa-tests.json"
    _write_json(
        opa_output,
        [
            {
                "location": {"file": "authz_test.rego", "row": 10, "col": 1},
                "package": "data.sanctum.api.authz",
                "name": "test_auditor_cannot_write",
                "duration": 12345,
            }
        ],
    )
    json_output = tmp_path / "executive-report.json"
    markdown_output = tmp_path / "executive-report.md"
    executive_result = CliRunner().invoke(
        cli_main.app,
        [
            "generate-executive-report",
            "--readiness-report",
            str(readiness_output),
            "--supply-chain-report",
            str(supply_chain_output),
            "--opa-test-report",
            str(opa_output),
            "--output-json",
            str(json_output),
            "--output-markdown",
            str(markdown_output),
        ],
    )

    assert executive_result.exit_code == 0, executive_result.output
    report = json.loads(json_output.read_text(encoding="utf-8"))
    markdown = markdown_output.read_text(encoding="utf-8")
    assert report["report_type"] == "SANCTUM_EXECUTIVE_SECURITY_EVIDENCE"
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["summary"]["attestation_status"] == "VERIFIED_BY_COSIGN"
    assert report["summary"]["trivy_reported_vulnerabilities"] == 0
    assert report["summary"]["grype_reported_vulnerabilities"] == 0
    assert report["summary"]["opa_test_status"] == "PASSED"
    assert "not a security verdict" in markdown
    assert "OPA policy tests" in markdown


def test_executive_report_marks_policy_failures_and_missing_scans(tmp_path):
    readiness = {
        "status": "REVIEW_REQUIRED",
        "summary": {
            "domains_assessed": 1,
            "domains_not_assessed": 0,
            "operator_reported_ready": 1,
            "operator_reported_gaps": 0,
            "incomplete_assessments": 0,
        },
        "domains": {"rust": {"status": "OPERATOR_REPORTED_READY"}},
    }
    supply_chain = {
        "status": "ATTESTATION_VERIFIED",
        "artifact": {"sha256": "a" * 64},
        "attestation": {
            "signature_status": "VERIFIED_BY_COSIGN",
            "subject_digest_match": True,
        },
        "scan_reports": {
            "trivy": {"status": "NOT_PROVIDED"},
            "grype": {"status": "NOT_PROVIDED"},
        },
    }
    paths = {
        "readiness": tmp_path / "readiness.json",
        "supply": tmp_path / "supply.json",
        "opa": tmp_path / "opa.json",
    }
    _write_json(paths["readiness"], readiness)
    _write_json(paths["supply"], supply_chain)
    _write_json(
        paths["opa"],
        [
            {
                "location": {"file": "authz_test.rego", "row": 10, "col": 1},
                "package": "data.sanctum.api.authz",
                "name": "test_denies_unauthorized",
                "duration": 12345,
                "fail": True,
            }
        ],
    )

    result = CliRunner().invoke(
        cli_main.app,
        [
            "generate-executive-report",
            "--readiness-report",
            str(paths["readiness"]),
            "--supply-chain-report",
            str(paths["supply"]),
            "--opa-test-report",
            str(paths["opa"]),
            "--output-json",
            str(tmp_path / "report.json"),
            "--output-markdown",
            str(tmp_path / "report.md"),
        ],
    )

    assert result.exit_code == 0, result.output
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["summary"]["opa_test_status"] == "FAILED"
    assert report["summary"]["opa_tests_failed"] == 1
    assert report["evidence"]["opa_tests"]["failures"][0]["name"] == (
        "test_denies_unauthorized"
    )
    assert report["evidence"]["opa_tests"]["failures"][0]["error"] == (
        "OPA reported test failure"
    )


def test_executive_report_rejects_invalid_opa_json_without_outputs(tmp_path):
    readiness = tmp_path / "readiness.json"
    supply_chain = tmp_path / "supply.json"
    opa = tmp_path / "opa.json"
    _write_json(
        readiness,
        {
            "status": "NOT_ASSESSED",
            "summary": {
                "domains_assessed": 0,
                "domains_not_assessed": 0,
                "operator_reported_ready": 0,
                "operator_reported_gaps": 0,
                "incomplete_assessments": 0,
            },
            "domains": {},
        },
    )
    _write_json(
        supply_chain,
        {
            "status": "ATTESTATION_VERIFIED",
            "artifact": {"sha256": "b" * 64},
            "attestation": {
                "signature_status": "VERIFIED_BY_COSIGN",
                "subject_digest_match": True,
            },
            "scan_reports": {
                "trivy": {"status": "NOT_PROVIDED"},
                "grype": {"status": "NOT_PROVIDED"},
            },
        },
    )
    _write_json(opa, {"tests": []})
    json_output = tmp_path / "report.json"
    markdown_output = tmp_path / "report.md"

    result = CliRunner().invoke(
        cli_main.app,
        [
            "generate-executive-report",
            "--readiness-report",
            str(readiness),
            "--supply-chain-report",
            str(supply_chain),
            "--opa-test-report",
            str(opa),
            "--output-json",
            str(json_output),
            "--output-markdown",
            str(markdown_output),
        ],
    )

    assert result.exit_code != 0
    assert "OPA test report must be a JSON array" in result.output
    assert not json_output.exists()
    assert not markdown_output.exists()
