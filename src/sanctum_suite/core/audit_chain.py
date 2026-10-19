from __future__ import annotations

import hashlib
import hmac
import json
import re
from pathlib import Path
from typing import Any
from datetime import datetime

from cryptography.hazmat.primitives import serialization

from sanctum_suite.core.signer import SecurityReportSigner


_FORMAT = "sanctum-audit-checkpoint-v1"
_ZERO_HASH = "0" * 64
_MAX_CHECKPOINT_RECORDS = 100_000
_MAX_AUDIT_OBJECT_BYTES = 64_000
_MAX_CHECKPOINT_ARCHIVE_BYTES = 256_000_000
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_AUTHORIZATION_ENGINES = {
    "local_rbac",
    "opa",
    "opa+rbac",
    "keylime",
    "trustee",
    "keylime+local_rbac",
    "keylime+opa+rbac",
    "trustee+local_rbac",
    "trustee+opa+rbac",
    "keylime+trustee+local_rbac",
    "keylime+trustee+opa+rbac",
    "tee_verifier",
    "tee_verifier+local_rbac",
    "tee_verifier+opa+rbac",
    "keylime+tee_verifier+local_rbac",
    "keylime+tee_verifier+opa+rbac",
}
_OBJECT_KEY_PATTERN = re.compile(
    r"^api-access/\d{4}/\d{2}/\d{2}/"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.json$"
)
_MERKLE_HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_CLASSIC_SIGNATURE_FIELDS = {
    "algorithm",
    "signer_sha256",
    "signature_base64",
}
_HYBRID_SIGNATURE_FIELDS = _CLASSIC_SIGNATURE_FIELDS | {
    "pqc_signer_sha256",
    "pqc_signature_base64",
}


def canonical_json(document: dict[str, Any]) -> bytes:
    return json.dumps(
        document,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _entry_hash(entry: dict[str, str]) -> str:
    return hashlib.sha256(canonical_json(entry)).hexdigest()


def _merkle_leaf_hash(leaf: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + leaf).digest()


def _merkle_node_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def _largest_power_of_two_less_than(value: int) -> int:
    return 1 << ((value - 1).bit_length() - 1)


def _merkle_root_hash(hashes: list[bytes]) -> bytes:
    if not hashes:
        return hashlib.sha256(b"").digest()
    if len(hashes) == 1:
        return hashes[0]
    split = _largest_power_of_two_less_than(len(hashes))
    return _merkle_node_hash(
        _merkle_root_hash(hashes[:split]),
        _merkle_root_hash(hashes[split:]),
    )


def merkle_tree_root(leaves: list[bytes]) -> str:
    """Return the RFC 6962 SHA-256 Merkle root for ordered leaf contents."""
    return _merkle_root_hash([_merkle_leaf_hash(leaf) for leaf in leaves]).hex()


def _merkle_subproof(
    old_size: int,
    hashes: list[bytes],
    include_old_root: bool,
) -> list[bytes]:
    new_size = len(hashes)
    if old_size == new_size:
        return [] if include_old_root else [_merkle_root_hash(hashes)]
    split = _largest_power_of_two_less_than(new_size)
    if old_size <= split:
        return _merkle_subproof(old_size, hashes[:split], include_old_root) + [
            _merkle_root_hash(hashes[split:])
        ]
    return _merkle_subproof(
        old_size - split, hashes[split:], False
    ) + [_merkle_root_hash(hashes[:split])]


def merkle_consistency_proof(leaves: list[bytes], old_size: int) -> list[str]:
    """Create an RFC 6962 consistency proof from a prefix to the current tree."""
    if isinstance(old_size, bool) or not isinstance(old_size, int):
        raise ValueError("Merkle tree size must be an integer")
    if not 0 <= old_size <= len(leaves):
        raise ValueError("Previous Merkle tree size is outside the current tree")
    hashes = [_merkle_leaf_hash(leaf) for leaf in leaves]
    if old_size == 0 or old_size == len(leaves):
        return []
    return [
        digest.hex()
        for digest in _merkle_subproof(old_size, hashes, True)
    ]


def verify_merkle_consistency_proof(
    *,
    old_size: int,
    new_size: int,
    old_root: str,
    new_root: str,
    proof: list[str],
) -> bool:
    """Verify an RFC 6962 consistency proof between independently retained tree heads."""
    if (
        isinstance(old_size, bool)
        or not isinstance(old_size, int)
        or isinstance(new_size, bool)
        or not isinstance(new_size, int)
        or old_size < 0
        or new_size < old_size
        or not isinstance(old_root, str)
        or not _MERKLE_HASH_PATTERN.fullmatch(old_root)
        or not isinstance(new_root, str)
        or not _MERKLE_HASH_PATTERN.fullmatch(new_root)
        or not isinstance(proof, list)
        or any(
            not isinstance(node, str) or not _MERKLE_HASH_PATTERN.fullmatch(node)
            for node in proof
        )
    ):
        return False
    old_hash = bytes.fromhex(old_root)
    new_hash = bytes.fromhex(new_root)
    if old_size == 0:
        return not proof and old_hash == hashlib.sha256(b"").digest()
    if old_size == new_size:
        return not proof and old_hash == new_hash
    if old_size == 0 or new_size == 0 or not proof:
        return False

    first = old_size - 1
    second = new_size - 1
    while first & 1:
        first >>= 1
        second >>= 1
    proof_hashes = [bytes.fromhex(node) for node in proof]
    index = 0
    if first == 0:
        old_accumulator = old_hash
        new_accumulator = old_hash
    else:
        old_accumulator = proof_hashes[0]
        new_accumulator = proof_hashes[0]
        index = 1

    for node in proof_hashes[index:]:
        if second == 0:
            return False
        if first & 1 or first == second:
            old_accumulator = _merkle_node_hash(node, old_accumulator)
            new_accumulator = _merkle_node_hash(node, new_accumulator)
            while first and not first & 1:
                first >>= 1
                second >>= 1
        else:
            new_accumulator = _merkle_node_hash(new_accumulator, node)
        first >>= 1
        second >>= 1
    return (
        second == 0
        and old_accumulator == old_hash
        and new_accumulator == new_hash
    )


def create_audit_checkpoint(
    *,
    bucket: str,
    records: list[dict[str, str]],
    signer: SecurityReportSigner,
    created_at: str,
) -> dict[str, Any]:
    if len(records) > _MAX_CHECKPOINT_RECORDS:
        raise ValueError("Audit checkpoint exceeds the 100000-version limit")
    chain_records: list[dict[str, str]] = []
    previous_hash = _ZERO_HASH
    sorted_records = sorted(records, key=lambda record: (record["key"], record["version_id"]))
    for record in sorted_records:
        entry = {
            "key": record["key"],
            "version_id": record["version_id"],
            "record_sha256": record["record_sha256"],
            "previous_hash": previous_hash,
        }
        chain_hash = _entry_hash(entry)
        chain_records.append({**entry, "chain_sha256": chain_hash})
        previous_hash = chain_hash

    checkpoint: dict[str, Any] = {
        "format": _FORMAT,
        "created_at": created_at,
        "bucket": bucket,
        "record_count": len(chain_records),
        "chain_head_sha256": previous_hash,
        "records": chain_records,
    }
    signer_fingerprint = signer.public_key_fingerprint
    if not isinstance(signer_fingerprint, str) or not _SHA256_PATTERN.fullmatch(
        signer_fingerprint
    ):
        raise ValueError("Audit checkpoint signer fingerprint is unavailable")
    checkpoint["signature"] = signer.sign_hybrid_bytes(canonical_json(checkpoint))
    return checkpoint


def verify_audit_checkpoint(
    *,
    checkpoint: dict[str, Any],
    archive_directory: str | Path,
    public_key_pem: bytes,
    pqc_public_key: bytes | None = None,
) -> dict[str, Any]:
    expected_fields = {
        "format",
        "created_at",
        "bucket",
        "record_count",
        "chain_head_sha256",
        "records",
        "signature",
    }
    if set(checkpoint) != expected_fields or checkpoint.get("format") != _FORMAT:
        raise ValueError("Audit checkpoint format or fields are invalid")
    signature = checkpoint.get("signature")
    if not isinstance(signature, dict) or frozenset(signature) not in {
        frozenset(_CLASSIC_SIGNATURE_FIELDS),
        frozenset(_HYBRID_SIGNATURE_FIELDS),
    }:
        raise ValueError("Audit checkpoint signature metadata is invalid")
    is_hybrid = signature["algorithm"] == "RSA-PSS-SHA256+ML-DSA-65"
    if not isinstance(signature["algorithm"], str):
        raise ValueError("Audit checkpoint signature algorithm is invalid")
    if signature["algorithm"] not in {
        "RSA-PSS-SHA256",
        "RSA-PSS-SHA256+ML-DSA-65",
    }:
        raise ValueError("Audit checkpoint signature algorithm is unsupported")
    if not isinstance(signature["signer_sha256"], str) or not isinstance(
        signature["signature_base64"], str
    ):
        raise ValueError("Audit checkpoint signature metadata is invalid")

    unsigned_checkpoint = {
        key: value for key, value in checkpoint.items() if key != "signature"
    }
    public_key = serialization.load_pem_public_key(public_key_pem)
    public_key_der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    signer_fingerprint = hashlib.sha256(public_key_der).hexdigest()
    if not hmac.compare_digest(signature["signer_sha256"], signer_fingerprint):
        raise ValueError("Audit checkpoint signer does not match trusted public key")
    if is_hybrid:
        if (
            set(signature) != _HYBRID_SIGNATURE_FIELDS
            or pqc_public_key is None
            or not isinstance(pqc_public_key, bytes)
            or not isinstance(signature["pqc_signer_sha256"], str)
            or not _SHA256_PATTERN.fullmatch(signature["pqc_signer_sha256"])
            or not isinstance(signature["pqc_signature_base64"], str)
        ):
            raise ValueError(
                "Hybrid audit checkpoint verification requires a trusted ML-DSA-65 public key"
            )
        pqc_fingerprint = hashlib.sha256(pqc_public_key).hexdigest()
        if not hmac.compare_digest(signature["pqc_signer_sha256"], pqc_fingerprint):
            raise ValueError(
                "Audit checkpoint ML-DSA signer does not match trusted public key"
            )
        SecurityReportSigner.verify_hybrid_bytes(
            canonical_json(unsigned_checkpoint),
            signature["signature_base64"],
            public_key_pem,
            signature["pqc_signature_base64"],
            pqc_public_key,
        )
    else:
        if set(signature) != _CLASSIC_SIGNATURE_FIELDS:
            raise ValueError("Classic audit checkpoint signature metadata is invalid")
        SecurityReportSigner.verify_bytes(
            canonical_json(unsigned_checkpoint),
            signature["signature_base64"],
            public_key_pem,
        )

    if (
        not isinstance(checkpoint["bucket"], str)
        or not checkpoint["bucket"]
        or not isinstance(checkpoint["created_at"], str)
        or isinstance(checkpoint["record_count"], bool)
        or not isinstance(checkpoint["record_count"], int)
        or checkpoint["record_count"] < 0
        or checkpoint["record_count"] > _MAX_CHECKPOINT_RECORDS
        or not isinstance(checkpoint["chain_head_sha256"], str)
        or not _SHA256_PATTERN.fullmatch(checkpoint["chain_head_sha256"])
        or not isinstance(checkpoint["records"], list)
        or checkpoint["record_count"] != len(checkpoint["records"])
    ):
        raise ValueError("Audit checkpoint contents are invalid")
    try:
        checkpoint_time = datetime.fromisoformat(checkpoint["created_at"])
    except ValueError as error:
        raise ValueError("Audit checkpoint creation time is invalid") from error
    if checkpoint_time.tzinfo is None or checkpoint_time.utcoffset() is None:
        raise ValueError("Audit checkpoint creation time must include a timezone")

    previous_hash = _ZERO_HASH
    previous_identity: tuple[str, str] | None = None
    total_bytes = 0
    archive_root = Path(archive_directory).resolve()
    for entry in checkpoint["records"]:
        if not isinstance(entry, dict) or set(entry) != {
            "key",
            "version_id",
            "record_sha256",
            "previous_hash",
            "chain_sha256",
        }:
            raise ValueError("Audit checkpoint contains an invalid chain entry")
        key = entry["key"]
        version_id = entry["version_id"]
        record_digest = entry["record_sha256"]
        if (
            not isinstance(key, str)
            or not _OBJECT_KEY_PATTERN.fullmatch(key)
            or not isinstance(version_id, str)
            or not version_id
            or len(version_id) > 1_024
            or not isinstance(record_digest, str)
            or not _SHA256_PATTERN.fullmatch(record_digest)
            or not isinstance(entry["previous_hash"], str)
            or not isinstance(entry["chain_sha256"], str)
            or not _SHA256_PATTERN.fullmatch(entry["chain_sha256"])
            or entry["previous_hash"] != previous_hash
        ):
            raise ValueError("Audit checkpoint chain entry is invalid")
        identity = (key, version_id)
        if previous_identity is not None and identity <= previous_identity:
            raise ValueError("Audit checkpoint entries are not in canonical order")
        previous_identity = identity
        unhashed_entry = {
            "key": key,
            "version_id": version_id,
            "record_sha256": record_digest,
            "previous_hash": previous_hash,
        }
        chain_hash = _entry_hash(unhashed_entry)
        if not hmac.compare_digest(entry["chain_sha256"], chain_hash):
            raise ValueError("Audit checkpoint hash chain verification failed")

        record_path = (archive_root / Path(key)).resolve()
        if not record_path.is_relative_to(archive_root):
            raise ValueError("Audit archive path escapes its root directory")
        if record_path.stat().st_size > _MAX_AUDIT_OBJECT_BYTES:
            raise ValueError(f"Audit archive record exceeds size limit: {key}")
        try:
            record_bytes = record_path.read_bytes()
            record = json.loads(record_bytes)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"Audit archive record is missing or invalid: {key}") from error
        if (
            not isinstance(record, dict)
            or canonical_json(record) != record_bytes
            or hashlib.sha256(record_bytes).hexdigest() != record_digest
            or len(record_bytes) > _MAX_AUDIT_OBJECT_BYTES
            or set(record)
            - {
                "event_id",
                "request_id",
                "event_type",
                "method",
                "route_group",
                "route",
                "credential_fingerprint",
                "subject_pseudonym",
                "tenant_pseudonym",
                "authentication_method",
                "authorization_engine",
                "authorization_decision",
                "authorization_policy_version",
                "outcome_code",
                "source",
                "occurred_at",
            }
            or record.get("event_type")
            not in {
                "request_started",
                "request_completed",
                "storage_preflight",
            }
        ):
            raise ValueError(
                f"Audit archive record digest or schema does not match: {key}"
            )
        authorization_engine = record.get("authorization_engine")
        authorization_decision = record.get("authorization_decision")
        policy_version = record.get("authorization_policy_version")
        outcome_code = record.get("outcome_code")
        if (
            authorization_engine is not None
            and (
                not isinstance(authorization_engine, str)
                or authorization_engine not in _AUTHORIZATION_ENGINES
            )
        ):
            raise ValueError(f"Audit archive authorization engine is invalid: {key}")
        if authorization_decision is not None and (
            not isinstance(authorization_decision, str)
            or authorization_decision not in {"allow", "deny", "error"}
        ):
            raise ValueError(f"Audit archive authorization decision is invalid: {key}")
        if policy_version is not None and (
            not isinstance(policy_version, str)
            or not policy_version
            or len(policy_version) > 128
        ):
            raise ValueError(f"Audit archive policy version is invalid: {key}")
        if outcome_code is not None and (
            isinstance(outcome_code, bool)
            or not isinstance(outcome_code, int)
            or not 100 <= outcome_code <= 599
        ):
            raise ValueError(f"Audit archive outcome code is invalid: {key}")
        try:
            occurred_at = datetime.fromisoformat(record["occurred_at"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Audit archive timestamp is invalid: {key}") from error
        if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise ValueError(f"Audit archive timestamp is invalid: {key}")
        try:
            record_event_id = record.get("event_id")
            if not isinstance(record_event_id, str):
                raise ValueError
            expected_event_id = key.rsplit("/", 1)[1][:-5]
            if record_event_id.lower() != expected_event_id:
                raise ValueError
        except ValueError as error:
            raise ValueError(f"Audit archive record identity does not match: {key}") from error
        total_bytes += len(record_bytes)
        if total_bytes > _MAX_CHECKPOINT_ARCHIVE_BYTES:
            raise ValueError("Audit archive exceeds the 256-megabyte verification limit")
        previous_hash = chain_hash

    if not hmac.compare_digest(checkpoint["chain_head_sha256"], previous_hash):
        raise ValueError("Audit checkpoint chain head does not match")
    return {
        "record_count": len(checkpoint["records"]),
        "chain_head_sha256": previous_hash,
        "signer_sha256": signer_fingerprint,
    }
