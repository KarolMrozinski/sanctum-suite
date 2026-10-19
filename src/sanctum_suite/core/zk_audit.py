from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from sanctum_suite.core.audit_chain import (
    canonical_json,
    verify_audit_checkpoint,
)
from sanctum_suite.core.signer import SecurityReportSigner


_BUNDLE_FORMAT = "sanctum-zk-audit-proof-v1"
_BINDING_FORMAT = "sanctum-zk-audit-binding-v1"
_POLICY_ID = "sanctum-audit-access-policy-v1.0"
_POLICY_HASH = (
    "1841298221720545410680030688376092580199638229742508812536090285103057017068"
)
_CIRCUIT_ID = "sanctum-audit-policy-batch-v1"
_BATCH_SIZE = 256
_TREE_DEPTH = 9
_MAX_PROOF_BYTES = 50_000_000
_FIELD_MODULUS = (
    21888242871839275222246405745257275088548364400416034343698204186575808495617
)
_DECIMAL_PATTERN = re.compile(r"^(0|[1-9][0-9]*)$")
_EVENT_TYPES = {
    "request_started": 0,
    "request_completed": 1,
    "storage_preflight": 2,
}
_DECISIONS = {"allow": 0, "deny": 1, "error": 2, None: 3}
_ENGINES = {
    "local_rbac": 0,
    "opa": 1,
    "opa+rbac": 2,
    "keylime": 3,
    "trustee": 4,
    "keylime+local_rbac": 5,
    "keylime+opa+rbac": 6,
    "trustee+local_rbac": 7,
    "trustee+opa+rbac": 8,
    "keylime+trustee+local_rbac": 9,
    "keylime+trustee+opa+rbac": 10,
    None: 11,
}
_OPA_ENGINES = {1, 2, 6, 8, 10}
_BINDING_FIELDS = {
    "format",
    "checkpoint_sha256",
    "chain_head_sha256",
    "record_count",
    "policy_id",
    "policy_hash",
    "poseidon_root",
    "batch_size",
    "batch_count",
    "tree_depth",
    "circuit_id",
    "verification_key_sha256",
}
_SIGNATURE_FIELDS = {"algorithm", "signer_sha256", "signature_base64"}
_BUNDLE_FIELDS = {"format", "binding", "signature", "proofs"}


def _normalized_event(record: dict[str, Any]) -> dict[str, int]:
    event_type = record["event_type"]
    decision = record.get("authorization_decision")
    engine = record.get("authorization_engine")
    outcome = record.get("outcome_code")
    policy_version = record.get("authorization_policy_version")

    if not isinstance(event_type, str) or event_type not in _EVENT_TYPES:
        raise ValueError("Audit snapshot contains an unsupported event type")
    if decision is not None and (
        not isinstance(decision, str) or decision not in _DECISIONS
    ):
        raise ValueError("Audit snapshot contains an unsupported authorization decision")
    if engine is not None and (not isinstance(engine, str) or engine not in _ENGINES):
        raise ValueError("Audit snapshot contains an unsupported authorization engine")
    if outcome is not None and (
        isinstance(outcome, bool) or not isinstance(outcome, int) or not 100 <= outcome <= 599
    ):
        raise ValueError("Audit snapshot contains an invalid HTTP outcome code")
    if policy_version is not None and (
        not isinstance(policy_version, str) or not policy_version or len(policy_version) > 128
    ):
        raise ValueError("Audit snapshot contains an invalid authorization policy version")

    event_type_code = _EVENT_TYPES[event_type]
    decision_code = _DECISIONS[decision]
    engine_code = _ENGINES[engine]
    outcome_code = outcome or 0
    has_policy_version = int(policy_version is not None)

    if event_type == "request_completed":
        if decision_code == 3 or engine_code == 11 or outcome_code == 0:
            raise ValueError(
                "Every completed request needs a decision, engine, and HTTP outcome "
                "before a ZK audit proof can be generated"
            )
        if 200 <= outcome_code < 300 and decision_code != _DECISIONS["allow"]:
            raise ValueError("A completed 2xx request must have an allow decision")
        if decision_code == _DECISIONS["deny"] and outcome_code != 403:
            raise ValueError("A denied request must have an HTTP 403 outcome")
        if engine_code in _OPA_ENGINES and not has_policy_version:
            raise ValueError("OPA-authorized requests must record a policy version")

    return {
        "event_type": event_type_code,
        "decision": decision_code,
        "outcome": outcome_code,
        "engine": engine_code,
        "has_policy_version": has_policy_version,
    }


def _load_verified_snapshot(
    checkpoint_file: Path,
    archive_directory: Path,
    public_key_file: Path,
) -> tuple[dict[str, Any], bytes, list[dict[str, int]]]:
    if checkpoint_file.stat().st_size > 256_000_000:
        raise ValueError("Audit checkpoint exceeds the 256-megabyte size limit")
    checkpoint_bytes = checkpoint_file.read_bytes()
    checkpoint = json.loads(checkpoint_bytes)
    if not isinstance(checkpoint, dict):
        raise ValueError("Audit checkpoint must be a JSON object")
    public_key_pem = public_key_file.read_bytes()
    verified = verify_audit_checkpoint(
        checkpoint=checkpoint,
        archive_directory=archive_directory,
        public_key_pem=public_key_pem,
    )

    archive_root = archive_directory.resolve()
    events: list[dict[str, int]] = []
    for entry in checkpoint["records"]:
        record_path = (archive_root / Path(entry["key"])).resolve()
        if not record_path.is_relative_to(archive_root):
            raise ValueError("Audit archive path escapes its root directory")
        record_bytes = record_path.read_bytes()
        record = json.loads(record_bytes)
        if (
            not isinstance(record, dict)
            or canonical_json(record) != record_bytes
            or hashlib.sha256(record_bytes).hexdigest() != entry["record_sha256"]
        ):
            raise ValueError("Audit archive changed after checkpoint verification")
        events.append(_normalized_event(record))
    if not events:
        raise ValueError("Empty WORM snapshots cannot produce an audit policy proof")
    return {
        **verified,
        "checkpoint_sha256": hashlib.sha256(checkpoint_bytes).hexdigest(),
    }, public_key_pem, events


def _zk_tool_directory() -> Path:
    return Path(__file__).resolve().parents[3] / "tools" / "zk-audit"


def create_zk_audit_proof(
    *,
    checkpoint_file: Path,
    archive_directory: Path,
    checkpoint_public_key_file: Path,
    wasm_file: Path,
    proving_key_file: Path,
    verification_key_file: Path,
    output_file: Path,
    signer: SecurityReportSigner,
) -> dict[str, Any]:
    if output_file.exists():
        raise ValueError("ZK audit proof output file must not already exist")
    verified, _public_key_pem, events = _load_verified_snapshot(
        checkpoint_file,
        archive_directory,
        checkpoint_public_key_file,
    )
    if not hmac.compare_digest(verified["signer_sha256"], signer.public_key_fingerprint or ""):
        raise ValueError(
            "ZK binding signer must match the trusted WORM checkpoint signer"
        )
    for path in (wasm_file, proving_key_file, verification_key_file):
        if not path.is_file():
            raise ValueError(f"Configured ZK proving artifact does not exist: {path}")

    node = shutil.which("node")
    if node is None:
        raise ValueError("Node.js is required to generate the Groth16 audit proof")
    tool_directory = _zk_tool_directory()
    script = tool_directory / "scripts" / "prove.mjs"
    command = [
        node,
        str(script),
        str(wasm_file.resolve()),
        str(proving_key_file.resolve()),
        str(verification_key_file.resolve()),
    ]
    try:
        node_environment = {
            key: value
            for key, value in os.environ.items()
            if key not in {"SANCTUM_ZK_BATCH_SIZE", "SANCTUM_ZK_TREE_DEPTH"}
        }
        result = subprocess.run(
            command,
            input=json.dumps({"events": events}, separators=(",", ":")),
            text=True,
            capture_output=True,
            check=False,
            env=node_environment,
        )
    except OSError as error:
        raise ValueError("Could not start the Groth16 proof generator") from error
    if result.returncode != 0:
        detail = result.stderr.strip() or "ZK proof generation returned an error"
        raise ValueError(detail[:2_000])
    try:
        generated = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ValueError("Groth16 proof generator returned invalid JSON") from error
    if not isinstance(generated, dict) or set(generated) != {
        "global_root",
        "policy_hash",
        "batch_size",
        "tree_depth",
        "proofs",
    }:
        raise ValueError("Groth16 proof generator returned an invalid result")
    if (
        generated["policy_hash"] != _POLICY_HASH
        or generated["batch_size"] != _BATCH_SIZE
        or generated["tree_depth"] != _TREE_DEPTH
        or not isinstance(generated["proofs"], list)
    ):
        raise ValueError("Groth16 proof generator result does not match the configured circuit")
    root = generated["global_root"]
    if (
        not isinstance(root, str)
        or not _DECIMAL_PATTERN.fullmatch(root)
        or int(root) >= _FIELD_MODULUS
    ):
        raise ValueError("Groth16 proof generator returned an invalid snapshot commitment")
    expected_batch_count = (len(events) + _BATCH_SIZE - 1) // _BATCH_SIZE
    if len(generated["proofs"]) != expected_batch_count:
        raise ValueError("Groth16 proof generator did not prove every audit batch")
    for index, proof in enumerate(generated["proofs"]):
        expected_signals = [
            root,
            str(index),
            str(min(_BATCH_SIZE, len(events) - index * _BATCH_SIZE)),
            str(len(events)),
            _POLICY_HASH,
        ]
        if (
            not isinstance(proof, dict)
            or set(proof) != {"proof", "public_signals"}
            or not isinstance(proof["public_signals"], list)
            or proof["public_signals"] != expected_signals
        ):
            raise ValueError(f"Groth16 proof generator returned an invalid batch: {index}")

    binding = {
        "format": _BINDING_FORMAT,
        "checkpoint_sha256": verified["checkpoint_sha256"],
        "chain_head_sha256": verified["chain_head_sha256"],
        "record_count": verified["record_count"],
        "policy_id": _POLICY_ID,
        "policy_hash": _POLICY_HASH,
        "poseidon_root": root,
        "batch_size": _BATCH_SIZE,
        "batch_count": len(generated["proofs"]),
        "tree_depth": _TREE_DEPTH,
        "circuit_id": _CIRCUIT_ID,
        "verification_key_sha256": hashlib.sha256(
            verification_key_file.read_bytes()
        ).hexdigest(),
    }
    bundle = {
        "format": _BUNDLE_FORMAT,
        "binding": binding,
        "signature": {
            "algorithm": "RSA-PSS-SHA256",
            "signer_sha256": signer.public_key_fingerprint,
            "signature_base64": signer.sign_bytes(canonical_json(binding)),
        },
        "proofs": generated["proofs"],
    }
    output_file.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(output_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(canonical_json(bundle) + b"\n")
            output.flush()
    except OSError:
        output_file.unlink(missing_ok=True)
        raise
    if output_file.stat().st_size > _MAX_PROOF_BYTES:
        output_file.unlink()
        raise ValueError("Generated ZK audit proof exceeds the 50-megabyte size limit")
    return binding


def verify_zk_audit_proof(
    *,
    proof_file: Path,
    checkpoint_file: Path,
    archive_directory: Path,
    checkpoint_public_key_file: Path,
    verification_key_file: Path,
) -> dict[str, Any]:
    if proof_file.stat().st_size > _MAX_PROOF_BYTES:
        raise ValueError("ZK audit proof exceeds the 50-megabyte size limit")
    verified, public_key_pem, _events = _load_verified_snapshot(
        checkpoint_file,
        archive_directory,
        checkpoint_public_key_file,
    )
    try:
        bundle = json.loads(proof_file.read_bytes())
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("ZK audit proof is not valid JSON") from error
    if not isinstance(bundle, dict) or set(bundle) != _BUNDLE_FIELDS:
        raise ValueError("ZK audit proof format or fields are invalid")
    binding = bundle["binding"]
    signature = bundle["signature"]
    if (
        bundle["format"] != _BUNDLE_FORMAT
        or not isinstance(binding, dict)
        or set(binding) != _BINDING_FIELDS
        or not isinstance(signature, dict)
        or set(signature) != _SIGNATURE_FIELDS
        or signature.get("algorithm") != "RSA-PSS-SHA256"
        or signature.get("signer_sha256") != verified["signer_sha256"]
        or not isinstance(signature.get("signature_base64"), str)
    ):
        raise ValueError("ZK audit proof signature metadata is invalid")
    expected_binding = {
        "format": _BINDING_FORMAT,
        "checkpoint_sha256": verified["checkpoint_sha256"],
        "chain_head_sha256": verified["chain_head_sha256"],
        "record_count": verified["record_count"],
        "policy_id": _POLICY_ID,
        "policy_hash": _POLICY_HASH,
        "batch_size": _BATCH_SIZE,
        "tree_depth": _TREE_DEPTH,
        "circuit_id": _CIRCUIT_ID,
        "verification_key_sha256": hashlib.sha256(
            verification_key_file.read_bytes()
        ).hexdigest(),
    }
    if any(binding.get(key) != value for key, value in expected_binding.items()):
        raise ValueError("ZK audit proof is not bound to this checkpoint and policy")
    root = binding.get("poseidon_root")
    if (
        not isinstance(root, str)
        or not _DECIMAL_PATTERN.fullmatch(root)
        or int(root) >= _FIELD_MODULUS
    ):
        raise ValueError("ZK audit proof contains an invalid snapshot commitment")
    batch_count = (verified["record_count"] + _BATCH_SIZE - 1) // _BATCH_SIZE
    if (
        isinstance(binding.get("batch_count"), bool)
        or not isinstance(binding.get("batch_count"), int)
        or binding["batch_count"] != batch_count
        or not isinstance(bundle["proofs"], list)
        or len(bundle["proofs"]) != batch_count
    ):
        raise ValueError("ZK audit proof does not cover every checkpoint record")
    SecurityReportSigner.verify_bytes(
        canonical_json(binding),
        signature["signature_base64"],
        public_key_pem,
    )
    if not verification_key_file.is_file():
        raise ValueError("Configured Groth16 verification key does not exist")

    node = shutil.which("node")
    if node is None:
        raise ValueError("Node.js is required to verify the Groth16 audit proof")
    script = _zk_tool_directory() / "scripts" / "verify.mjs"
    result = subprocess.run(
        [
            node,
            str(script),
            str(proof_file.resolve()),
            str(verification_key_file.resolve()),
            root,
            str(verified["record_count"]),
        ],
        capture_output=True,
        text=True,
        check=False,
        env={
            key: value
            for key, value in os.environ.items()
            if key not in {"SANCTUM_ZK_BATCH_SIZE", "SANCTUM_ZK_TREE_DEPTH"}
        },
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "Groth16 proof verification failed"
        raise ValueError(detail[:2_000])
    return binding
