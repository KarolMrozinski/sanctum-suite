import hashlib
import json
import uuid
from types import SimpleNamespace

import pytest

from sanctum_suite.core import zk_audit
from sanctum_suite.core.audit_chain import (
    canonical_json,
    create_audit_checkpoint,
)
from sanctum_suite.core.signer import SecurityReportSigner
from sanctum_suite.core.zk_audit import (
    _normalized_event,
    create_zk_audit_proof,
    verify_zk_audit_proof,
)


def test_zk_audit_policy_accepts_allow_and_denied_completions():
    allow = _normalized_event(
        {
            "event_type": "request_completed",
            "authorization_decision": "allow",
            "authorization_engine": "opa+rbac",
            "authorization_policy_version": "policy-v1",
            "outcome_code": 200,
        }
    )
    deny = _normalized_event(
        {
            "event_type": "request_completed",
            "authorization_decision": "deny",
            "authorization_engine": "local_rbac",
            "outcome_code": 403,
        }
    )

    assert allow == {
        "event_type": 1,
        "decision": 0,
        "outcome": 200,
        "engine": 2,
        "has_policy_version": 1,
    }
    assert deny["decision"] == 1
    assert deny["outcome"] == 403


@pytest.mark.parametrize(
    "record",
    [
        {
            "event_type": "request_completed",
            "authorization_decision": "deny",
            "authorization_engine": "local_rbac",
            "outcome_code": 200,
        },
        {
            "event_type": "request_completed",
            "authorization_decision": "deny",
            "authorization_engine": "opa",
            "authorization_policy_version": "policy-v1",
            "outcome_code": 401,
        },
        {
            "event_type": "request_completed",
            "authorization_decision": "allow",
            "authorization_engine": "opa",
            "outcome_code": 200,
        },
        {
            "event_type": "request_completed",
            "authorization_decision": "allow",
            "authorization_engine": "unknown",
            "outcome_code": 200,
        },
        {
            "event_type": "request_completed",
            "authorization_decision": None,
            "authorization_engine": "local_rbac",
            "outcome_code": 500,
        },
    ],
)
def test_zk_audit_policy_rejects_noncompliant_or_unverifiable_completions(record):
    with pytest.raises(ValueError):
        _normalized_event(record)


def test_zk_audit_policy_allows_non_completion_records_without_decision():
    event = _normalized_event(
        {
            "event_type": "storage_preflight",
            "authorization_decision": None,
            "authorization_engine": None,
            "outcome_code": None,
        }
    )

    assert event == {
        "event_type": 2,
        "decision": 3,
        "outcome": 0,
        "engine": 11,
        "has_policy_version": 0,
    }


def test_signed_zk_proof_binds_complete_checkpoint_and_verifies_all_chunks(
    monkeypatch, tmp_path
):
    signer = SecurityReportSigner(key_dir=str(tmp_path / "keys"))
    archive = tmp_path / "archive"
    event_id = str(uuid.uuid4())
    key = f"api-access/2026/10/19/{event_id}.json"
    record = {
        "event_id": event_id,
        "event_type": "request_completed",
        "authorization_engine": "opa+rbac",
        "authorization_decision": "allow",
        "authorization_policy_version": "policy-v1",
        "outcome_code": 200,
        "occurred_at": "2026-10-19T10:00:00+00:00",
    }
    body = canonical_json(record)
    record_path = archive / key
    record_path.parent.mkdir(parents=True)
    record_path.write_bytes(body)
    checkpoint = create_audit_checkpoint(
        bucket="sanctum-audit-worm",
        records=[
            {
                "key": key,
                "version_id": "worm-version-1",
                "record_sha256": hashlib.sha256(body).hexdigest(),
            }
        ],
        signer=signer,
        created_at="2026-10-19T10:00:01+00:00",
    )
    checkpoint_file = tmp_path / "checkpoint.json"
    checkpoint_file.write_bytes(canonical_json(checkpoint) + b"\n")
    wasm_file = tmp_path / "circuit.wasm"
    proving_key_file = tmp_path / "proving.zkey"
    verification_key_file = tmp_path / "verification.json"
    for path, contents in (
        (wasm_file, b"wasm"),
        (proving_key_file, b"proving key"),
        (verification_key_file, b"verification key"),
    ):
        path.write_bytes(contents)

    root = "123456"
    proof = {
        "proof": {"pi_a": ["1"], "pi_b": [["1"]], "pi_c": ["1"], "protocol": "groth16"},
        "public_signals": [
            root,
            "0",
            "1",
            "1",
            zk_audit._POLICY_HASH,
        ],
    }
    generated = {
        "global_root": root,
        "policy_hash": zk_audit._POLICY_HASH,
        "batch_size": 256,
        "tree_depth": 9,
        "proofs": [proof],
    }

    def fake_run(command, **_kwargs):
        if command[1].endswith("prove.mjs"):
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps(generated),
                stderr="",
            )
        return SimpleNamespace(returncode=0, stdout="verified", stderr="")

    monkeypatch.setattr(zk_audit.shutil, "which", lambda _name: "node")
    monkeypatch.setattr(zk_audit.subprocess, "run", fake_run)
    output_file = tmp_path / "proof.json"
    binding = create_zk_audit_proof(
        checkpoint_file=checkpoint_file,
        archive_directory=archive,
        checkpoint_public_key_file=signer.public_key_path,
        checkpoint_pqc_public_key_file=signer.pqc_public_key_path,
        wasm_file=wasm_file,
        proving_key_file=proving_key_file,
        verification_key_file=verification_key_file,
        output_file=output_file,
        signer=signer,
    )

    bundle = json.loads(output_file.read_bytes())
    assert binding["record_count"] == 1
    assert binding["checkpoint_sha256"] == hashlib.sha256(
        checkpoint_file.read_bytes()
    ).hexdigest()
    assert bundle["proofs"] == [proof]
    verified_binding = verify_zk_audit_proof(
        proof_file=output_file,
        checkpoint_file=checkpoint_file,
        archive_directory=archive,
        checkpoint_public_key_file=signer.public_key_path,
        checkpoint_pqc_public_key_file=signer.pqc_public_key_path,
        verification_key_file=verification_key_file,
    )
    assert verified_binding == binding

    bundle["binding"]["poseidon_root"] = "123457"
    output_file.write_bytes(canonical_json(bundle))
    with pytest.raises(ValueError, match="signature verification failed"):
        verify_zk_audit_proof(
            proof_file=output_file,
            checkpoint_file=checkpoint_file,
            archive_directory=archive,
            checkpoint_public_key_file=signer.public_key_path,
            checkpoint_pqc_public_key_file=signer.pqc_public_key_path,
            verification_key_file=verification_key_file,
        )
