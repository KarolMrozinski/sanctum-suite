import base64
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from sanctum_suite import main as cli_main
from sanctum_suite.core.supply_chain_verify import (
    SupplyChainArtifactVerifier,
    SupplyChainVerificationError,
)


PREDICATE_TYPE = "https://slsa.dev/provenance/v1"


def _write_bundle(path: Path, artifact_digest: str) -> None:
    statement = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": "release.tar.gz", "digest": {"sha256": artifact_digest}}],
        "predicateType": PREDICATE_TYPE,
        "predicate": {"buildType": "https://example.test/build"},
    }
    path.write_text(
        json.dumps(
            {
                "dsseEnvelope": {
                    "payload": base64.b64encode(
                        json.dumps(statement).encode("utf-8")
                    ).decode("ascii"),
                    "payloadType": "application/vnd.in-toto+json",
                    "signatures": [{"sig": "verified-by-fake-cosign"}],
                }
            }
        ),
        encoding="utf-8",
    )


def _fake_cosign_success(monkeypatch, command_capture=None):
    def run(command, **kwargs):
        if command_capture is not None:
            command_capture.extend(command)
        assert kwargs["shell"] is False
        assert kwargs["timeout"] == 120
        return SimpleNamespace(returncode=0, stdout="Verified OK", stderr="")

    monkeypatch.setattr(
        "sanctum_suite.core.supply_chain_verify.subprocess.run", run
    )


def test_verifier_checks_identity_and_in_toto_subject_and_summarizes_scans(
    tmp_path, monkeypatch
):
    artifact = tmp_path / "release.tar.gz"
    artifact.write_bytes(b"test release artifact")
    artifact_digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    bundle = tmp_path / "attestation.sigstore.json"
    _write_bundle(bundle, artifact_digest)
    trivy = tmp_path / "trivy.json"
    trivy.write_text(
        json.dumps(
            {
                "SchemaVersion": 2,
                "ArtifactName": "release.tar.gz",
                "Results": [
                    {
                        "Vulnerabilities": [
                            {"VulnerabilityID": "CVE-2026-1234", "Severity": "HIGH"},
                            {"VulnerabilityID": "CVE-2026-1235", "Severity": "critical"},
                        ]
                    },
                    {"Vulnerabilities": None},
                ],
            }
        ),
        encoding="utf-8",
    )
    grype = tmp_path / "grype.json"
    grype.write_text(
        json.dumps(
            {
                "schema": "6.0.0",
                "matches": [
                    {"vulnerability": {"id": "CVE-2026-1234", "severity": "High"}},
                    {"vulnerability": {"id": "CVE-2026-1235", "severity": "Critical"}},
                    {"vulnerability": {"id": "CVE-2026-1236", "severity": "Unknown"}},
                ],
            }
        ),
        encoding="utf-8",
    )
    command = []
    _fake_cosign_success(monkeypatch, command)

    report = SupplyChainArtifactVerifier().verify(
        artifact=artifact,
        attestation_bundle=bundle,
        certificate_identity="https://github.com/org/repo/.github/workflows/build.yml@refs/tags/v1",
        certificate_oidc_issuer="https://token.actions.githubusercontent.com",
        predicate_type=PREDICATE_TYPE,
        trivy_report=trivy,
        grype_report=grype,
    )

    assert report["status"] == "ATTESTATION_VERIFIED"
    assert report["attestation"]["signature_status"] == "VERIFIED_BY_COSIGN"
    assert report["attestation"]["subject_digest_match"] is True
    assert "--new-bundle-format" in command
    assert "--certificate-identity" in command
    assert (
        report["scan_reports"]["trivy"]["by_severity"]["HIGH"] == 1
    )
    assert (
        report["scan_reports"]["trivy"]["by_severity"]["CRITICAL"] == 1
    )
    assert report["scan_reports"]["grype"]["reported_vulnerabilities"] == 3
    assert report["scan_reports"]["grype"]["by_severity"]["UNKNOWN"] == 1
    assert (
        report["scan_reports"]["grype"]["status"]
        == "REPORT_PARSED_NOT_INDEPENDENTLY_VERIFIED"
    )


def test_verifier_rejects_subject_digest_or_predicate_mismatch(tmp_path, monkeypatch):
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"artifact")
    bundle = tmp_path / "bundle.json"
    _write_bundle(bundle, "0" * 64)
    _fake_cosign_success(monkeypatch)
    verifier = SupplyChainArtifactVerifier()
    args = {
        "artifact": artifact,
        "attestation_bundle": bundle,
        "certificate_identity": "trusted-identity",
        "certificate_oidc_issuer": "https://issuer.example",
        "predicate_type": PREDICATE_TYPE,
    }

    with pytest.raises(SupplyChainVerificationError, match="digest does not match"):
        verifier.verify(**args)

    _write_bundle(bundle, hashlib.sha256(artifact.read_bytes()).hexdigest())
    with pytest.raises(SupplyChainVerificationError, match="predicateType"):
        verifier.verify(**{**args, "predicate_type": "https://example.test/other"})


def test_verifier_fails_closed_when_cosign_verification_fails(tmp_path, monkeypatch):
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"artifact")
    bundle = tmp_path / "bundle.json"
    _write_bundle(bundle, hashlib.sha256(artifact.read_bytes()).hexdigest())
    monkeypatch.setattr(
        "sanctum_suite.core.supply_chain_verify.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=1, stdout="", stderr="certificate identity mismatch"
        ),
    )

    with pytest.raises(
        SupplyChainVerificationError, match="certificate identity mismatch"
    ):
        SupplyChainArtifactVerifier().verify(
            artifact=artifact,
            attestation_bundle=bundle,
            certificate_identity="trusted-identity",
            certificate_oidc_issuer="https://issuer.example",
            predicate_type=PREDICATE_TYPE,
        )


def test_verifier_requires_valid_scan_report_shape(tmp_path, monkeypatch):
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"artifact")
    bundle = tmp_path / "bundle.json"
    _write_bundle(bundle, hashlib.sha256(artifact.read_bytes()).hexdigest())
    trivy = tmp_path / "trivy.json"
    trivy.write_text(json.dumps({"Results": "invalid"}), encoding="utf-8")
    _fake_cosign_success(monkeypatch)

    with pytest.raises(SupplyChainVerificationError, match="Results array"):
        SupplyChainArtifactVerifier().verify(
            artifact=artifact,
            attestation_bundle=bundle,
            certificate_identity="trusted-identity",
            certificate_oidc_issuer="https://issuer.example",
            predicate_type=PREDICATE_TYPE,
            trivy_report=trivy,
        )


def test_supply_chain_verify_cli_emits_json_report(tmp_path, monkeypatch):
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"artifact")
    bundle = tmp_path / "bundle.json"
    _write_bundle(bundle, hashlib.sha256(artifact.read_bytes()).hexdigest())
    _fake_cosign_success(monkeypatch)

    result = CliRunner().invoke(
        cli_main.app,
        [
            "supply-chain-verify",
            "--artifact",
            str(artifact),
            "--attestation-bundle",
            str(bundle),
            "--certificate-identity",
            "trusted-identity",
            "--certificate-oidc-issuer",
            "https://issuer.example",
            "--predicate-type",
            PREDICATE_TYPE,
        ],
    )

    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["status"] == "ATTESTATION_VERIFIED"
    assert report["scan_reports"]["trivy"]["status"] == "NOT_PROVIDED"
    assert report["scan_reports"]["grype"]["status"] == "NOT_PROVIDED"
