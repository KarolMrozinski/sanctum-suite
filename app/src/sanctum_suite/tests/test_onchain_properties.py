from datetime import datetime, timezone
from decimal import Decimal

from hypothesis import given, settings, strategies as st
import pytest

from sanctum_suite.core.onchain import (
    ChainName,
    OnChainBlock,
    OnChainTransaction,
    TransactionInput,
    TransactionOutput,
    OnChainProviderError,
    _bitcoin_atomic_units,
    _normalize_ethereum_block,
)
from sanctum_suite.core.onchain_graph import OnChainGraphBuilder


_MAX_BITCOIN_SUPPLY_SAT = 21_000_000 * 100_000_000
_MAX_EVM_QUANTITY = 2**256 - 1


@settings(max_examples=200, deadline=None)
@given(st.integers(min_value=0, max_value=_MAX_BITCOIN_SUPPLY_SAT))
def test_bitcoin_amount_normalization_round_trips_every_satoshi_value(satoshis):
    btc_amount = Decimal(satoshis) / Decimal(100_000_000)

    assert _bitcoin_atomic_units(btc_amount) == satoshis


@settings(max_examples=100, deadline=None)
@given(st.integers(min_value=0, max_value=_MAX_BITCOIN_SUPPLY_SAT))
def test_bitcoin_amount_normalization_rejects_sub_satoshi_values(satoshis):
    fractional_satoshi = (Decimal(satoshis) + Decimal("0.1")) / Decimal(100_000_000)

    with pytest.raises(OnChainProviderError, match="invalid output amount"):
        _bitcoin_atomic_units(fractional_satoshi)


@settings(max_examples=100, deadline=None)
@given(st.integers(min_value=0, max_value=_MAX_EVM_QUANTITY))
def test_ethereum_block_normalization_preserves_full_wei_quantity(value_wei):
    sender = "0x" + "1" * 40
    recipient = "0x" + "2" * 40
    raw_block = {
        "hash": "0x" + "a" * 64,
        "number": "0x2a",
        "parentHash": "0x" + "b" * 64,
        "timestamp": "0x6553f100",
        "transactions": [
            {
                "hash": "0x" + "c" * 64,
                "from": sender,
                "to": recipient,
                "value": hex(value_wei),
            }
        ],
    }

    block = _normalize_ethereum_block(raw_block)

    assert block.transactions[0].inputs[0].address == sender
    assert block.transactions[0].outputs[0].address == recipient
    assert block.transactions[0].outputs[0].value_atomic == value_wei
    assert block.transactions[0].outputs[0].unit == "wei"


@settings(max_examples=100, deadline=None)
@given(st.lists(st.integers(min_value=0, max_value=_MAX_EVM_QUANTITY), min_size=0, max_size=20))
def test_graph_keeps_generated_transaction_edges_and_values_consistent(values):
    transactions = tuple(
        OnChainTransaction(
            transaction_hash=f"0x{index + 1:064x}",
            inputs=(
                TransactionInput(
                    address=f"0x{index + 1:040x}",
                    unit="wei",
                ),
            ),
            outputs=(
                TransactionOutput(
                    index=0,
                    address=f"0x{index + 101:040x}",
                    value_atomic=value,
                    unit="wei",
                ),
            ),
        )
        for index, value in enumerate(values)
    )
    block = OnChainBlock(
        chain=ChainName.ETHEREUM,
        block_hash="0x" + "a" * 64,
        height=42,
        parent_hash="0x" + "b" * 64,
        timestamp=datetime(2026, 10, 19, tzinfo=timezone.utc),
        fetched_at=datetime(2026, 10, 19, 0, 1, tzinfo=timezone.utc),
        source="ethereum_json_rpc",
        transactions=transactions,
    )

    graph = OnChainGraphBuilder().build(block, case_id="property-case")
    node_ids = {node["id"] for node in graph["nodes"]}

    assert len(node_ids) == len(graph["nodes"])
    assert all(edge["source"] in node_ids and edge["target"] in node_ids for edge in graph["edges"])
    assert sum(edge["relation"] == "CONTAINS" for edge in graph["edges"]) == len(values)
    transfer_edges = [edge for edge in graph["edges"] if edge["relation"] == "SUBMITS_TO"]
    assert [int(edge["value_atomic"]) for edge in transfer_edges] == values
    assert all(edge["confidence"] == "directly_observed" for edge in graph["edges"])
