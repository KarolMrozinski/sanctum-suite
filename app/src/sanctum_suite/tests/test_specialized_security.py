import hashlib
import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from typer.testing import CliRunner

from sanctum_suite import main as cli_main
from sanctum_suite.core.airgap_diode import AirGapDataDiodeBroker
from sanctum_suite.core.ebpf_enforcement import EbpfInKernelEnforcementEngine
from sanctum_suite.core.post_quantum_pqc import (
    PostQuantumCryptographicAssuranceEngine,
)
from sanctum_suite.core.security_readiness import SecurityReadinessAudit
from sanctum_suite.core.tempest_auditor import TempestSdip27EmissionsAuditor


def test_pqc_inventory_prioritizes_only_explicit_hndl_context():
    report = PostQuantumCryptographicAssuranceEngine().audit_cryptographic_primitives(
        [
            {
                "algorithm": "ECDH-P256",
                "location": "archive-transfer-service",
                "use_case": "key_establishment",
                "requires_long_term_confidentiality": True,
            },
            {
                "algorithm": "ML-KEM-768",
                "location": "new-service",
                "use_case": "key_establishment",
            },
            {"algorithm": "vendor-cipher", "location": "legacy-device"},
        ]
    )

    assert report["review_counts"] == {
        "total": 3,
        "classical_public_key": 1,
        "standardized_pqc_reported": 1,
        "manual_review": 1,
        "hndl_review_prioritized": 1,
    }
    classical, pqc, unknown = report["algorithms"]
    assert classical["migration_review"] == "PRIORITIZE_HARVEST_NOW_DECRYPT_LATER_REVIEW"
    assert pqc["standard"] == "NIST FIPS 203"
    assert pqc["migration_review"] == "VERIFY_PARAMETERS_IMPLEMENTATION_AND_INTEROPERABILITY"
    assert unknown["migration_review"] == "MANUAL_ALGORITHM_REVIEW_REQUIRED"
    assert "does not discover" in report["limitations"]


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        ({"algorithm": "RSA"}, "requires an algorithm and location"),
        (
            {
                "algorithm": "ECDH",
                "location": "svc",
                "use_case": "key_exchange",
            },
            "use_case must be",
        ),
        (
            {
                "algorithm": "ECDH",
                "location": "svc",
                "requires_long_term_confidentiality": "yes",
            },
            "must be a boolean",
        ),
    ],
)
def test_pqc_inventory_rejects_invalid_entries(entry, message):
    with pytest.raises(ValueError, match=message):
        PostQuantumCryptographicAssuranceEngine().audit_cryptographic_primitives(
            [entry]
        )


def test_pqc_inventory_marks_unrecognized_parameter_set_for_manual_review():
    report = PostQuantumCryptographicAssuranceEngine().audit_cryptographic_primitives(
        [{"algorithm": "ML-KEM-44", "location": "svc"}]
    )

    assert report["algorithms"][0]["migration_review"] == "MANUAL_ALGORITHM_REVIEW_REQUIRED"


def test_pqc_inventory_reports_pqxdh_as_a_protocol_not_a_standardized_algorithm():
    report = PostQuantumCryptographicAssuranceEngine().audit_cryptographic_primitives(
        [
            {
                "algorithm": "PQXDH",
                "location": "messaging-service",
                "use_case": "key_establishment",
            }
        ]
    )

    assert (
        report["algorithms"][0]["classification"]
        == "POST_QUANTUM_KEY_ESTABLISHMENT_PROTOCOL_REPORTED"
    )
    assert report["algorithms"][0]["standard"] == ""
    assert (
        report["algorithms"][0]["migration_review"]
        == "VERIFY_PROTOCOL_SPEC_IMPLEMENTATION_AND_INTEROPERABILITY"
    )


def test_security_readiness_reports_declared_gaps_and_missing_sections():
    declaration = {
        "ebpf": {
            "kernel_compatibility_checked": True,
            "verifier_tests_passed": True,
            "hook_coverage_reviewed": True,
            "fail_mode_documented": True,
            "performance_tested": True,
            "detach_rollback_tested": False,
        },
        "rust": {
            "cargo_lock_reviewed": True,
        },
        "cryptography": {
            "inventory": [
                {
                    "algorithm": "PQXDH",
                    "location": "messaging-service",
                    "use_case": "key_establishment",
                }
            ]
        },
    }

    report = SecurityReadinessAudit().audit(declaration)

    assert report["status"] == "REVIEW_REQUIRED"
    assert report["domains"]["ebpf"]["status"] == "GAPS_REPORTED"
    assert report["domains"]["rust"]["status"] == "INCOMPLETE"
    assert report["domains"]["spiffe"]["status"] == "NOT_ASSESSED"
    assert (
        report["domains"]["cryptography"]["algorithms"][0]["classification"]
        == "POST_QUANTUM_KEY_ESTABLISHMENT_PROTOCOL_REPORTED"
    )
    assert report["summary"] == {
        "domains_assessed": 3,
        "domains_not_assessed": 1,
        "operator_reported_ready": 0,
        "operator_reported_gaps": 1,
        "incomplete_assessments": 1,
    }


def test_security_readiness_requires_boolean_checks_and_rejects_unknown_fields():
    with pytest.raises(ValueError, match="must be a boolean"):
        SecurityReadinessAudit().audit({"spiffe": {"mtls_enforced": "yes"}})

    with pytest.raises(ValueError, match="Unknown readiness section"):
        SecurityReadinessAudit().audit({"kernel": {}})


def test_security_readiness_keeps_reported_passes_distinct_from_verification():
    report = SecurityReadinessAudit().audit(
        {
            "spiffe": {
                "trust_domain_configured": True,
                "svid_rotation_tested": True,
                "workload_api_access_controlled": True,
                "mtls_enforced": True,
                "authorization_policy_reviewed": True,
            }
        }
    )

    assert report["domains"]["spiffe"]["status"] == "OPERATOR_REPORTED_READY"
    assert report["summary"]["operator_reported_ready"] == 1
    assert report["assessment_scope"] == "OPERATOR_SUPPLIED_DECLARATIONS"


def test_security_readiness_cli_emits_json_report(tmp_path):
    input_path = tmp_path / "readiness.json"
    input_path.write_text(
        json.dumps({"spiffe": {"trust_domain_configured": True}}),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli_main.app, ["security-readiness", "--input", str(input_path)]
    )

    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["assessment_scope"] == "OPERATOR_SUPPLIED_DECLARATIONS"
    assert report["domains"]["spiffe"]["status"] == "INCOMPLETE"


def test_security_readiness_cli_rejects_invalid_json_input(tmp_path):
    input_path = tmp_path / "readiness.json"
    input_path.write_text('{"spiffe": {"mtls_enforced": "yes"}}', encoding="utf-8")

    result = CliRunner().invoke(
        cli_main.app, ["security-readiness", "--input", str(input_path)]
    )

    assert result.exit_code != 0
    assert "must be a boolean" in result.output


def test_offline_transfer_manifest_has_canonical_digest_and_signer_fingerprint():
    payload = b"approved synthetic offline test payload"
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    result = AirGapDataDiodeBroker().prepare_offline_package(
        payload,
        "test-enclave",
        private_key.sign(payload),
        public_key_pem,
    )
    canonical_manifest = json.dumps(
        result["manifest"], sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    public_key_der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    assert result["signature_valid"] is True
    assert result["manifest"]["payload_sha256"] == hashlib.sha256(payload).hexdigest()
    assert result["manifest_sha256"] == hashlib.sha256(canonical_manifest).hexdigest()
    assert result["signer_public_key_sha256"] == hashlib.sha256(public_key_der).hexdigest()
    assert result["transmitted"] is False
    assert result["physical_diode_verified"] is False


def test_ebpf_and_tempest_report_unimplemented_or_unassessed_states():
    ebpf = EbpfInKernelEnforcementEngine().enforce_kernel_shield("reviewed-profile")
    tempest = TempestSdip27EmissionsAuditor().audit_enclave_emissions("Zone-1")

    assert ebpf["status"] == "NOT_IMPLEMENTED"
    assert ebpf["enforcement_active"] is False
    assert ebpf["validation_evidence"]["kernel_compatibility_checked"] is False
    assert tempest["status"] == "NOT_ASSESSED"
    assert tempest["evidence_readiness"] == "REQUIRED_QUALIFIED_EVIDENCE_MISSING"
    assert len(tempest["missing_evidence_types"]) == 2


def test_pqc_inventory_cli_emits_json_report(tmp_path):
    inventory_path = tmp_path / "crypto-inventory.json"
    inventory_path.write_text(
        json.dumps(
            [
                {
                    "algorithm": "ECDH-P256",
                    "location": "archive-service",
                    "use_case": "key_establishment",
                    "requires_long_term_confidentiality": True,
                }
            ]
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli_main.app, ["pqc-inventory", "--inventory", str(inventory_path)]
    )

    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["status"] == "INVENTORY_REVIEW_REQUIRED"
    assert (
        report["algorithms"][0]["migration_review"]
        == "PRIORITIZE_HARVEST_NOW_DECRYPT_LATER_REVIEW"
    )
