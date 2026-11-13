import asyncio
import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone

import httpx
import pytest
from typer.testing import CliRunner

from sanctum_suite import main
from sanctum_suite.core.audit_chain import (
    canonical_json,
    create_audit_checkpoint,
    verify_merkle_consistency_proof,
)
from sanctum_suite.core.private_ledger import (
    FabricGatewayLedger,
    LocalPrivateLedger,
    PrivateLedgerError,
    anchor_verified_checkpoint,
)
from sanctum_suite.core.signer import SecurityReportSigner
from sanctum_suite.core.tee_attestation import TEEAttestation, TrusteeClaimsClient


def _anchor(checkpoint_sha256="a" * 64):
    return {
        "schema_version": 1,
        "checkpoint_sha256": checkpoint_sha256,
        "anchored_at": "2026-10-19T12:00:00Z",
    }


def _attestation(operation_digest=None):
    return TEEAttestation(
        workload_id="sanctum-audit-prod",
        tee_type="sgx",
        measurement="a" * 64,
        workload_digest="b" * 64,
        verified_at=datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc),
        operation_digest=operation_digest,
    )


def _make_checkpoint(tmp_path):
    signer = SecurityReportSigner(key_dir=str(tmp_path / "keys"))
    archive = tmp_path / "archive"
    event_id = str(uuid.uuid4())
    key = f"api-access/2026/10/19/{event_id}.json"
    body = canonical_json(
        {
            "event_id": event_id,
            "event_type": "request_completed",
            "occurred_at": "2026-10-19T12:00:00+00:00",
        }
    )
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
        created_at="2026-10-19T12:00:01+00:00",
    )
    checkpoint_bytes = canonical_json(checkpoint)
    checkpoint_file = tmp_path / "checkpoint.json"
    checkpoint_file.write_bytes(checkpoint_bytes)
    return signer, archive, checkpoint_file, checkpoint_bytes


def test_local_private_ledger_is_idempotent_and_detects_tampering(tmp_path):
    database_file = tmp_path / "private-ledger.sqlite"
    ledger = LocalPrivateLedger(database_file)
    first = ledger.anchor(_anchor())
    repeated = ledger.anchor(_anchor("a" * 64))

    assert first["status"] == "LEDGER_ANCHOR_COMMITTED"
    assert repeated["status"] == "LEDGER_ANCHOR_ALREADY_PRESENT"
    assert first["entry_sha256"] == repeated["entry_sha256"]
    assert ledger.verify()["record_count"] == 1

    with sqlite3.connect(database_file) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE ledger_anchors SET checkpoint_sha256 = ?",
                ("c" * 64,),
            )

    with sqlite3.connect(database_file) as connection:
        connection.execute("DROP TRIGGER ledger_anchors_no_update")
        connection.execute(
            "UPDATE ledger_anchors SET checkpoint_sha256 = ?",
            ("c" * 64,),
        )
    with pytest.raises(PrivateLedgerError, match="hash chain is invalid"):
        ledger.verify()


def test_local_ledger_exposes_verifiable_merkle_consistency_proofs(tmp_path):
    ledger = LocalPrivateLedger(tmp_path / "private-ledger.sqlite")
    ledger.anchor(_anchor("a" * 64))
    old_head = ledger.verify()
    ledger.anchor(_anchor("b" * 64))
    ledger.anchor(_anchor("c" * 64))

    result = ledger.consistency_proof(
        old_tree_size=old_head["tree_size"],
        old_tree_root_sha256=old_head["tree_root_sha256"],
    )
    assert result["old_tree_size"] == 1
    assert result["new_tree_size"] == 3
    assert verify_merkle_consistency_proof(
        old_size=result["old_tree_size"],
        new_size=result["new_tree_size"],
        old_root=result["old_tree_root_sha256"],
        new_root=result["new_tree_root_sha256"],
        proof=result["proof"],
    )
    assert not verify_merkle_consistency_proof(
        old_size=result["old_tree_size"],
        new_size=result["new_tree_size"],
        old_root=result["old_tree_root_sha256"],
        new_root="f" * 64,
        proof=result["proof"],
    )
    cli_result = CliRunner().invoke(
        main.app,
        [
            "ledger-consistency",
            "--database-file",
            str(tmp_path / "private-ledger.sqlite"),
            "--old-tree-size",
            str(old_head["tree_size"]),
            "--old-tree-root-sha256",
            old_head["tree_root_sha256"],
        ],
    )
    assert cli_result.exit_code == 0, cli_result.output
    assert json.loads(cli_result.stdout)["proof"] == result["proof"]
    with pytest.raises(PrivateLedgerError, match="does not match this ledger history"):
        ledger.consistency_proof(
            old_tree_size=old_head["tree_size"],
            old_tree_root_sha256="f" * 64,
        )


def test_anchor_service_persists_only_checkpoint_digest_metadata(tmp_path):
    database_file = tmp_path / "private-ledger.sqlite"
    checkpoint_bytes = b"signed checkpoint bytes"
    ledger = LocalPrivateLedger(database_file)

    result = anchor_verified_checkpoint(
        checkpoint_bytes=checkpoint_bytes,
        attestation=_attestation(hashlib.sha256(checkpoint_bytes).hexdigest()),
        ledger=ledger,
    )

    assert result["checkpoint_sha256"] == hashlib.sha256(checkpoint_bytes).hexdigest()
    assert result["tee_type"] == "sgx"
    with sqlite3.connect(database_file) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(ledger_anchors)")
        }
        rows = connection.execute(
            "SELECT schema_version, checkpoint_sha256, anchored_at FROM ledger_anchors"
        ).fetchall()
    assert columns.isdisjoint({"event_type", "workload_id", "measurement"})
    assert rows[0][0] == 1
    assert rows[0][1] == result["checkpoint_sha256"]

    with pytest.raises(PrivateLedgerError, match="not bound"):
        anchor_verified_checkpoint(
            checkpoint_bytes=checkpoint_bytes,
            attestation=_attestation(),
            ledger=ledger,
        )


def test_fabric_gateway_submits_only_digest_schema_and_timestamp(tmp_path):
    for name in ("ca.pem", "client.pem", "client-key.pem"):
        (tmp_path / name).write_text("test", encoding="utf-8")
    requests = []

    def respond(request):
        requests.append(request)
        payload = json.loads(request.content)
        return httpx.Response(
            201,
            json={
                "status": "COMMITTED",
                "checkpoint_sha256": payload["checkpoint_sha256"],
                "tx_id": "f" * 64,
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(respond))
    ledger = FabricGatewayLedger(
        gateway_url="https://fabric-gateway.internal",
        channel="audit",
        chaincode="checkpoint-anchor",
        ca_certificate_file=tmp_path / "ca.pem",
        client_certificate_file=tmp_path / "client.pem",
        client_key_file=tmp_path / "client-key.pem",
        client=client,
    )
    result = ledger.anchor(_anchor())
    request = requests[0]

    assert result["status"] == "LEDGER_ANCHOR_COMMITTED"
    assert result["backend"] == "hyperledger-fabric"
    assert set(json.loads(request.content)) == {
        "schema_version",
        "checkpoint_sha256",
        "anchored_at",
    }
    assert request.headers["idempotency-key"] == "a" * 64
    client.close()


def test_fabric_gateway_rejects_commit_for_a_different_checkpoint(tmp_path):
    for name in ("ca.pem", "client.pem", "client-key.pem"):
        (tmp_path / name).write_text("test", encoding="utf-8")
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                201,
                json={
                    "status": "COMMITTED",
                    "checkpoint_sha256": "b" * 64,
                    "tx_id": "f" * 64,
                },
            )
        )
    )
    ledger = FabricGatewayLedger(
        gateway_url="https://fabric-gateway.internal",
        channel="audit",
        chaincode="checkpoint-anchor",
        ca_certificate_file=tmp_path / "ca.pem",
        client_certificate_file=tmp_path / "client.pem",
        client_key_file=tmp_path / "client-key.pem",
        client=client,
    )
    with pytest.raises(PrivateLedgerError, match="expected committed anchor"):
        ledger.anchor(_anchor())
    client.close()


def test_ledger_anchor_rejects_non_snp_sgx_platform_from_allowlist(tmp_path):
    from sanctum_suite.core.tee_attestation import TEEAttestationUnavailable

    cert = tmp_path / "client.crt"
    key = tmp_path / "client.key"
    ca = tmp_path / "ca.crt"
    for path in (cert, key, ca):
        path.write_text("test certificate material", encoding="utf-8")
    profile = {
        "snp": {
            "measurement_sha384": ["aa" * 48],
            "workload_digest_sha256": ["bb" * 32],
        },
        "sgx": {
            "measurement_sha256": ["ee" * 32],
            "workload_digest_sha256": ["ff" * 32],
        },
    }

    class AsyncMockTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, _request):
            return httpx.Response(
                200,
                json={
                    "status": "PASS",
                    "tee_type": "tdx",
                    "workload_id": "sanctum-audit-prod",
                    "challenge": "fresh-challenge",
                    "measurement": "cc" * 48,
                    "workload_digest": "dd" * 32,
                    "debug_enabled": False,
                    "verified_at": "2026-10-19T12:00:00Z",
                    "evidence_sig": "valid",
                },
            )

    client = TrusteeClaimsClient(
        endpoint="https://tee-gateway.internal/verify",
        workload_id="sanctum-audit-prod",
        ca_cert_file=str(ca),
        client_cert_file=str(cert),
        client_key_file=str(key),
        max_age_seconds=120,
        expected_claims={
            name: {
                ("measurement_sha256" if name == "sgx" else "measurement_sha384"):
                frozenset(values[
                    "measurement_sha256" if name == "sgx" else "measurement_sha384"
                ]),
                "workload_digest_sha256": frozenset(
                    values["workload_digest_sha256"]
                ),
            }
            for name, values in profile.items()
        },
        transport=AsyncMockTransport(),
        clock=lambda: datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc).timestamp(),
        nonce_factory=lambda: "fresh-challenge",
    )
    with pytest.raises(TEEAttestationUnavailable, match="identity, signature"):
        asyncio.run(client.verify_readiness())


def test_ledger_anchor_cli_verifies_checkpoint_and_requires_tee(
    monkeypatch, tmp_path
):
    signer, archive, checkpoint_file, checkpoint_bytes = _make_checkpoint(tmp_path)

    class VerifiedClient:
        async def verify_readiness(self, *, operation_digest):
            return _attestation(operation_digest)

    monkeypatch.setattr(
        TrusteeClaimsClient,
        "from_environment",
        classmethod(lambda cls, *, required: VerifiedClient()),
    )
    database_file = tmp_path / "private-ledger.sqlite"
    result = CliRunner().invoke(
        main.app,
        [
            "ledger-anchor",
            "--checkpoint-file",
            str(checkpoint_file),
            "--archive-directory",
            str(archive),
            "--checkpoint-public-key-file",
            str(signer.public_key_path),
            "--checkpoint-pqc-public-key-file",
            str(signer.pqc_public_key_path),
            "--backend",
            "local",
            "--database-file",
            str(database_file),
        ],
    )

    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["checkpoint_sha256"] == hashlib.sha256(checkpoint_bytes).hexdigest()
    assert report["tee_type"] == "sgx"
    assert LocalPrivateLedger(database_file).verify()["record_count"] == 1
    assert b"request_completed" not in database_file.read_bytes()


def test_ledger_anchor_cli_rejects_invalid_checkpoint_before_attestation(
    monkeypatch, tmp_path
):
    signer, archive, checkpoint_file, _ = _make_checkpoint(tmp_path)
    document = json.loads(checkpoint_file.read_bytes())
    document["records"][0]["record_sha256"] = "0" * 64
    checkpoint_file.write_text(json.dumps(document), encoding="utf-8")
    called = []
    monkeypatch.setattr(
        TrusteeClaimsClient,
        "from_environment",
        classmethod(
            lambda cls, *, required: called.append(required) or pytest.fail("called")
        ),
    )

    result = CliRunner().invoke(
        main.app,
        [
            "ledger-anchor",
            "--checkpoint-file",
            str(checkpoint_file),
            "--archive-directory",
            str(archive),
            "--checkpoint-public-key-file",
            str(signer.public_key_path),
            "--checkpoint-pqc-public-key-file",
            str(signer.pqc_public_key_path),
            "--backend",
            "local",
            "--database-file",
            str(tmp_path / "private-ledger.sqlite"),
        ],
    )

    assert result.exit_code != 0
    assert called == []
    assert "signature verification failed" in result.output
