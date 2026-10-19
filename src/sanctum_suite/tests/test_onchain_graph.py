import pytest
from fastapi.testclient import TestClient

from sanctum_suite.api import server
from sanctum_suite.core.incident_cases import IncidentCaseStore
from sanctum_suite.core.onchain import (
    ChainName,
    EthereumTransferObservation,
    OnChainBlock,
    OnChainTransaction,
    TransactionInput,
    TransactionOutput,
)
from sanctum_suite.core.onchain_graph import OnChainGraphBuilder, OnChainGraphTooLarge


def sample_ethereum_block():
    return OnChainBlock(
        chain=ChainName.ETHEREUM,
        block_hash="0x" + "a" * 64,
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
                        value_atomic=10**18 + 1,
                        unit="wei",
                    ),
                ),
            ),
        ),
    )


def test_graph_records_provenance_and_preserves_atomic_amount_precision():
    result = OnChainGraphBuilder().build(sample_ethereum_block(), case_id="case-1")

    assert result["case_id"] == "case-1"
    assert result["source"] == "ethereum_json_rpc"
    assert result["nodes"][0]["provider"] == "ethereum_json_rpc"
    transfer = next(edge for edge in result["edges"] if edge["relation"] == "SUBMITS_TO")
    assert transfer["source"].startswith("transaction:ethereum:")
    assert transfer["provider"] == "ethereum_json_rpc"
    assert transfer["value_atomic"] == str(10**18 + 1)
    assert transfer["unit"] == "wei"
    assert transfer["confidence"] == "directly_observed"
    assert transfer["block_hash"] == "0x" + "a" * 64
    assert any(edge["relation"] == "INITIATES" for edge in result["edges"])
    assert any(edge["relation"] == "CONTAINS" for edge in result["edges"])
    assert any("No wallet ownership" in limitation for limitation in result["limitations"])
    assert any("optional normalized block snapshot" in limitation for limitation in result["limitations"])


def test_bitcoin_graph_keeps_spent_outpoints_without_claiming_input_owner():
    block = OnChainBlock(
        chain=ChainName.BITCOIN,
        block_hash="a" * 64,
        height=100,
        parent_hash="b" * 64,
        timestamp="2026-10-19T12:00:00Z",
        fetched_at="2026-10-19T12:01:00Z",
        source="bitcoin_core_rpc",
        transactions=(
            OnChainTransaction(
                transaction_hash="c" * 64,
                inputs=(
                    TransactionInput(
                        previous_transaction="d" * 64,
                        previous_output_index=2,
                        unit="sat",
                    ),
                ),
                outputs=(
                    TransactionOutput(
                        index=0,
                        address="bc1qexample",
                        value_atomic=123_456_789,
                        unit="sat",
                    ),
                ),
            ),
        ),
    )

    result = OnChainGraphBuilder().build(block, case_id="case-1")

    spent = next(edge for edge in result["edges"] if edge["relation"] == "SPENDS")
    assert spent["target"] == f"outpoint:bitcoin:{'d' * 64}:2"
    assert not any(
        node.get("kind") == "address" and node.get("label") == "d" * 64
        for node in result["nodes"]
    )
    created = next(edge for edge in result["edges"] if edge["relation"] == "CREATES")
    assert created["value_atomic"] == "123456789"


def test_graph_fails_instead_of_returning_a_partial_result(monkeypatch):
    monkeypatch.setattr("sanctum_suite.core.onchain_graph._MAX_GRAPH_NODES", 1)

    with pytest.raises(OnChainGraphTooLarge, match="no partial graph"):
        OnChainGraphBuilder().build(sample_ethereum_block(), case_id="case-1")


def test_case_onchain_graph_endpoint_requires_case_and_reads_configured_client(
    monkeypatch, tmp_path
):
    api_key = "onchain-graph-test-key-" + "x" * 32
    monkeypatch.setenv("SANCTUM_API_KEY", api_key)
    monkeypatch.setattr(
        server,
        "incident_case_store",
        IncidentCaseStore(tmp_path / "cases.sqlite3"),
    )
    created_case = server.get_incident_case_store().create_case(
        title="On-chain investigation",
        summary="Review a block related to the incident.",
        created_by="analyst",
    )

    class FakeClient:
        async def get_block(self, height):
            assert height == 42
            return sample_ethereum_block()

    def fake_client(chain):
        assert chain is ChainName.ETHEREUM
        return FakeClient()

    monkeypatch.setattr(server, "get_onchain_rpc_client", fake_client)
    client = TestClient(server.app)
    headers = {"X-API-Key": api_key}

    unauthorized = client.get(
        f"/api/v1/cases/{created_case['case_id']}/onchain-graph?chain=ethereum&height=42"
    )
    assert unauthorized.status_code == 401

    response = client.get(
        f"/api/v1/cases/{created_case['case_id']}/onchain-graph?chain=ethereum&height=42",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["case_id"] == created_case["case_id"]
    assert response.json()["block_height"] == 42

    missing = client.get(
        "/api/v1/cases/not-a-case/onchain-graph?chain=ethereum&height=42",
        headers=headers,
    )
    assert missing.status_code == 404


def test_case_onchain_graph_endpoint_fails_closed_when_provider_is_unconfigured(
    monkeypatch, tmp_path
):
    api_key = "onchain-unconfigured-test-key-" + "x" * 32
    monkeypatch.setenv("SANCTUM_API_KEY", api_key)
    monkeypatch.delenv("SANCTUM_ETHEREUM_RPC_URL", raising=False)
    monkeypatch.setattr(
        server,
        "incident_case_store",
        IncidentCaseStore(tmp_path / "cases.sqlite3"),
    )
    created_case = server.get_incident_case_store().create_case(
        title="Unconfigured on-chain source",
        summary="A missing RPC source must not return a success-shaped response.",
        created_by="analyst",
    )
    client = TestClient(server.app)

    response = client.get(
        f"/api/v1/cases/{created_case['case_id']}/onchain-graph?chain=ethereum&height=42",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Ethereum JSON-RPC is not configured"


def test_case_onchain_forensics_and_trace_endpoints_are_authenticated_and_case_scoped(
    monkeypatch,
    tmp_path,
):
    api_key = "onchain-forensics-test-key-" + "x" * 32
    monkeypatch.setenv("SANCTUM_API_KEY", api_key)
    monkeypatch.setattr(
        server,
        "incident_case_store",
        IncidentCaseStore(tmp_path / "cases.sqlite3"),
    )
    monkeypatch.setattr(server, "get_onchain_block_store", lambda: None)
    queried_addresses = []

    class EmptyRiskStore:
        def list_for_addresses(self, case_id, chain, addresses):
            queried_addresses.extend(addresses)
            return [
                {
                    "address": addresses[0],
                    "provider": "chainalysis",
                    "provider_rating": "high",
                    "verification_status": "provider_reported_unverified",
                }
            ]

    monkeypatch.setattr(server, "get_onchain_risk_store", lambda: EmptyRiskStore())
    created_case = server.get_incident_case_store().create_case(
        title="Ethereum forensics",
        summary="Review block events and transaction call trace.",
        created_by="analyst",
    )
    sender = "0x" + "1" * 40
    recipient = "0x" + "2" * 40
    block_hash = "0x" + "a" * 64
    transaction_hash = "0x" + "c" * 64

    class FakeClient:
        async def get_block_logs(self, height):
            assert height == 42
            transfer = EthereumTransferObservation(
                token_contract="0x" + "3" * 40,
                transaction_hash=transaction_hash,
                block_hash=block_hash,
                block_number=42,
                log_index=0,
                from_address=sender,
                to_address=recipient,
                value_atomic=15,
            )
            return sample_ethereum_block(), (), (transfer,)

        async def trace_transaction(self, tx_hash):
            assert tx_hash == transaction_hash
            return {
                "chain": "ethereum",
                "transaction_hash": tx_hash,
                "block_hash": block_hash,
                "block_height": 42,
                "source": "ethereum_json_rpc",
                "observed_at": "2026-10-19T12:00:00Z",
                "confidence": "provider_observed_trace_unverified",
                "trace": {
                    "call_type": "CALL",
                    "from_address": sender,
                    "to_address": recipient,
                    "value_atomic": "1",
                    "gas_limit": 21_000,
                    "gas_used": "21000",
                    "input_selector": "0xa9059cbb",
                    "input_bytes": 36,
                    "error": None,
                    "calls": [],
                },
                "limitations": ["provider output only"],
            }

    monkeypatch.setattr(server, "get_onchain_rpc_client", lambda chain: FakeClient())
    client = TestClient(server.app)
    forensics_path = f"/api/v1/cases/{created_case['case_id']}/onchain-forensics?height=42"
    trace_path = (
        f"/api/v1/cases/{created_case['case_id']}/onchain-traces/{transaction_hash}"
    )
    assert client.get(forensics_path).status_code == 401
    assert client.get(trace_path).status_code == 401

    headers = {"X-API-Key": api_key}
    forensics = client.get(forensics_path, headers=headers)
    assert forensics.status_code == 200, forensics.text
    assert forensics.json()["case_id"] == created_case["case_id"]
    assert forensics.json()["block"]["height"] == 42
    assert forensics.json()["limitations"]
    assert forensics.json()["logs"] == []
    assert forensics.json()["provider_assessments"][0]["provider"] == "chainalysis"
    assert forensics.json()["regulatory_assessment"]["status"] == "NOT_ASSESSED"
    assert set(queried_addresses) == {sender, recipient}

    trace = client.get(trace_path, headers=headers)
    assert trace.status_code == 200, trace.text
    assert trace.json()["case_id"] == created_case["case_id"]
    assert trace.json()["confidence"] == "provider_observed_trace_unverified"
    assert trace.json()["trace"]["input_selector"] == "0xa9059cbb"
    assert trace.json()["regulatory_assessment"]["status"] == "NOT_ASSESSED"

    invalid_hash = client.get(
        f"/api/v1/cases/{created_case['case_id']}/onchain-traces/not-a-hash",
        headers=headers,
    )
    assert invalid_hash.status_code == 422
    missing_case = client.get(
        "/api/v1/cases/not-a-case/onchain-forensics?height=42",
        headers=headers,
    )
    assert missing_case.status_code == 404


@pytest.mark.parametrize(
    ("query", "status_code"),
    [
        ("chain=ethereum&height=-1", 422),
        ("chain=unknown&height=1", 422),
    ],
)
def test_case_onchain_graph_endpoint_validates_query(monkeypatch, tmp_path, query, status_code):
    api_key = "onchain-query-test-key-" + "x" * 32
    monkeypatch.setenv("SANCTUM_API_KEY", api_key)
    monkeypatch.setattr(
        server,
        "incident_case_store",
        IncidentCaseStore(tmp_path / "cases.sqlite3"),
    )
    created_case = server.get_incident_case_store().create_case(
        title="On-chain query",
        summary="Validate the query contract.",
        created_by="analyst",
    )
    client = TestClient(server.app)
    response = client.get(
        f"/api/v1/cases/{created_case['case_id']}/onchain-graph?{query}",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == status_code
