import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from sanctum_suite.api import server
from sanctum_suite.core.incident_cases import IncidentCaseStore
from sanctum_suite.core.onchain import (
    ChainName,
    OnChainBlock,
    OnChainTransaction,
    TransactionInput,
    TransactionOutput,
)
from sanctum_suite.core.onchain_store import (
    OnChainBlockStore,
    OnChainStoreCapacityError,
)


def sample_block(*, block_hash: str = "0x" + "a" * 64) -> OnChainBlock:
    return OnChainBlock(
        chain=ChainName.ETHEREUM,
        block_hash=block_hash,
        height=42,
        parent_hash="0x" + "b" * 64,
        timestamp="2026-10-19T12:00:00Z",
        fetched_at="2026-10-19T12:01:00Z",
        source="ethereum_json_rpc",
        transactions=(
            OnChainTransaction(
                transaction_hash="0x" + "c" * 64,
                inputs=(TransactionInput(address="0x" + "d" * 40, unit="wei"),),
                outputs=(
                    TransactionOutput(
                        index=0,
                        address="0x" + "e" * 40,
                        value_atomic=10**25 + 123,
                        unit="wei",
                    ),
                ),
            ),
        ),
    )


def create_case(store: IncidentCaseStore, title: str = "Snapshot case") -> str:
    case = store.create_case(title=title, summary="Test retained chain evidence.", created_by="analyst")
    return case["case_id"]


def test_store_round_trip_idempotency_and_fork_retention(tmp_path):
    cases = IncidentCaseStore(tmp_path / "cases.sqlite3")
    case_id = create_case(cases)
    snapshots = OnChainBlockStore(cases.db_path, retention_days=30)
    canonical = sample_block()
    fork = sample_block(block_hash="0x" + "f" * 64)

    first = snapshots.store_block(case_id, canonical)
    duplicate = snapshots.store_block(case_id, canonical)
    fork_result = snapshots.store_block(case_id, fork)

    assert first["inserted"] is True
    assert duplicate["inserted"] is False
    assert first["snapshot_id"] == duplicate["snapshot_id"]
    assert fork_result["reorg_fork_preserved"] is True
    assert snapshots.get_block(case_id, canonical.chain, canonical.height, canonical.block_hash) == canonical
    assert snapshots.get_block(case_id, fork.chain, fork.height, fork.block_hash) == fork

    listed = snapshots.list_snapshots(case_id, chain=ChainName.ETHEREUM, limit=1)
    assert len(listed["snapshots"]) == 1
    assert listed["has_more"] is True
    next_page = snapshots.list_snapshots(
        case_id,
        chain=ChainName.ETHEREUM,
        limit=1,
        offset=listed["next_offset"],
    )
    assert len(next_page["snapshots"]) == 1
    assert next_page["snapshots"][0]["block_hash"] != listed["snapshots"][0]["block_hash"]
    assert "payload_json" not in listed["snapshots"][0]


def test_store_retention_and_case_isolation(tmp_path):
    cases = IncidentCaseStore(tmp_path / "cases.sqlite3")
    case_id = create_case(cases, "Retention case")
    other_case_id = create_case(cases, "Separate case")
    snapshots = OnChainBlockStore(cases.db_path, retention_days=1)
    snapshots.store_block(case_id, sample_block())
    snapshots.store_block(other_case_id, sample_block())

    with sqlite3.connect(cases.db_path) as connection:
        connection.execute(
            "UPDATE onchain_block_snapshots SET stored_at = ? WHERE case_id = ?",
            ((datetime.now(timezone.utc) - timedelta(days=2)).isoformat(), case_id),
        )

    assert snapshots.purge_expired() == 1
    assert snapshots.get_block(case_id, ChainName.ETHEREUM, 42, sample_block().block_hash) is None
    assert snapshots.get_block(
        other_case_id,
        ChainName.ETHEREUM,
        42,
        sample_block().block_hash,
    ) == sample_block()
    assert snapshots.list_snapshots(case_id)["snapshots"] == []


def test_retention_cutoff_is_inclusive_and_case_deletion_cascades(tmp_path):
    cases = IncidentCaseStore(tmp_path / "cases.sqlite3")
    case_id = create_case(cases, "Retention cutoff case")
    snapshots = OnChainBlockStore(cases.db_path, retention_days=1)
    snapshots.store_block(case_id, sample_block())
    now = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)
    cutoff = now - timedelta(days=1)

    with sqlite3.connect(cases.db_path) as connection:
        connection.execute(
            "UPDATE onchain_block_snapshots SET stored_at = ? WHERE case_id = ?",
            (cutoff.isoformat(), case_id),
        )

    assert snapshots.purge_expired(now=now) == 0
    with sqlite3.connect(cases.db_path) as connection:
        remaining_at_cutoff = connection.execute(
            "SELECT COUNT(*) FROM onchain_block_snapshots WHERE case_id = ?",
            (case_id,),
        ).fetchone()[0]
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("DELETE FROM incident_cases WHERE case_id = ?", (case_id,))
        remaining = connection.execute(
            "SELECT COUNT(*) FROM onchain_block_snapshots WHERE case_id = ?",
            (case_id,),
        ).fetchone()[0]
    assert remaining_at_cutoff == 1
    assert remaining == 0


def test_store_fails_explicitly_at_snapshot_and_payload_limits(tmp_path, monkeypatch):
    cases = IncidentCaseStore(tmp_path / "cases.sqlite3")
    case_id = create_case(cases, "Bounded storage case")
    snapshots = OnChainBlockStore(cases.db_path, retention_days=30)

    monkeypatch.setattr("sanctum_suite.core.onchain_store.MAX_SNAPSHOTS_PER_CASE", 1)
    snapshots.store_block(case_id, sample_block())
    with pytest.raises(OnChainStoreCapacityError, match="snapshot limit"):
        snapshots.store_block(case_id, sample_block(block_hash="0x" + "f" * 64))

    monkeypatch.setattr("sanctum_suite.core.onchain_store.MAX_BLOCK_BYTES", 1)
    with pytest.raises(OnChainStoreCapacityError, match="32 MiB"):
        snapshots.store_block(
            create_case(cases, "Payload limit case"),
            sample_block(),
        )


def test_onchain_storage_api_persists_and_loads_case_snapshot(monkeypatch, tmp_path):
    api_key = "onchain-storage-test-key-" + "x" * 32
    monkeypatch.setenv("SANCTUM_API_KEY", api_key)
    monkeypatch.setenv("SANCTUM_ONCHAIN_STORAGE_ENABLED", "true")
    monkeypatch.setenv("SANCTUM_ONCHAIN_RETENTION_DAYS", "30")
    monkeypatch.setattr(server, "incident_case_store", IncidentCaseStore(tmp_path / "cases.sqlite3"))
    monkeypatch.setattr(server, "onchain_block_store", None)
    monkeypatch.setattr(server, "_tenant_onchain_block_stores", {})
    monkeypatch.delenv("SANCTUM_TENANT_DATABASE_ROOT", raising=False)
    case_id = create_case(server.get_incident_case_store())

    class FakeClient:
        calls = 0

        async def get_block(self, height):
            self.calls += 1
            assert height == 42
            return sample_block()

    fake_client = FakeClient()
    monkeypatch.setattr(server, "get_onchain_rpc_client", lambda chain: fake_client)
    client = TestClient(server.app)
    headers = {"X-API-Key": api_key}
    graph_url = f"/api/v1/cases/{case_id}/onchain-graph?chain=ethereum&height=42"

    first = client.get(graph_url, headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["storage"]["inserted"] is True
    assert first.json()["storage"]["reorg_fork_preserved"] is False

    duplicate = client.get(graph_url, headers=headers)
    assert duplicate.status_code == 200
    assert duplicate.json()["storage"]["inserted"] is False
    assert fake_client.calls == 2

    listing = client.get(f"/api/v1/cases/{case_id}/onchain-blocks", headers=headers)
    assert listing.status_code == 200, listing.text
    snapshots = listing.json()["snapshots"]
    assert len(snapshots) == 1
    assert "payload_json" not in snapshots[0]

    saved_graph = client.get(
        f"{graph_url}&block_hash={snapshots[0]['block_hash']}",
        headers=headers,
    )
    assert saved_graph.status_code == 200, saved_graph.text
    assert saved_graph.json()["storage"]["loaded_from_snapshot"] is True
    assert fake_client.calls == 2

    unauthorized = client.get(f"/api/v1/cases/{case_id}/onchain-blocks")
    assert unauthorized.status_code == 401

    other_case = create_case(server.get_incident_case_store(), "Other case")
    assert client.get(
        f"/api/v1/cases/{other_case}/onchain-blocks",
        headers=headers,
    ).json()["snapshots"] == []
    cross_case_snapshot = client.get(
        f"/api/v1/cases/{other_case}/onchain-graph?chain=ethereum&height=42&block_hash={snapshots[0]['block_hash']}",
        headers=headers,
    )
    assert cross_case_snapshot.status_code == 404
