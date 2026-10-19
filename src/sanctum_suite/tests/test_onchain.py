import json

import httpx
import pytest

from sanctum_suite.core.onchain import (
    BitcoinCoreClient,
    ChainName,
    EthereumJsonRpcClient,
    OnChainBlock,
    OnChainProviderError,
    OnChainTransaction,
    _normalize_call_trace,
    _normalize_ethereum_logs,
)


def mock_rpc(monkeypatch, handler):
    real_async_client = httpx.AsyncClient
    requests = []

    def record_and_respond(request):
        requests.append(request)
        return handler(request)

    monkeypatch.setattr(
        "sanctum_suite.core.onchain.httpx.AsyncClient",
        lambda **kwargs: real_async_client(
            transport=httpx.MockTransport(record_and_respond),
            **kwargs,
        ),
    )
    return requests


@pytest.mark.asyncio
async def test_bitcoin_core_normalizes_block_and_uses_exact_satoshis(monkeypatch):
    block = {
        "hash": "b" * 64,
        "height": 840_000,
        "previousblockhash": "a" * 64,
        "time": 1_713_571_234,
        "tx": [
            {
                "txid": "c" * 64,
                "vin": [{"coinbase": "coinbase-data"}],
                "vout": [
                    {
                        "n": 0,
                        "value": 1.23456789,
                        "scriptPubKey": {"address": "bc1qexample"},
                    }
                ],
            }
        ],
    }

    def handler(request):
        payload = json.loads(request.content)
        assert request.headers["authorization"].startswith("Basic ")
        if payload["method"] == "getblockhash":
            assert payload["params"] == [840_000]
            result = block["hash"]
        else:
            assert payload["method"] == "getblock"
            assert payload["params"] == [block["hash"], 2]
            result = block
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": result})

    requests = mock_rpc(monkeypatch, handler)
    result = await BitcoinCoreClient(
        "http://127.0.0.1:8332",
        username="rpc-user",
        password="rpc-password",
    ).get_block(840_000)

    assert len(requests) == 2
    assert result.chain is ChainName.BITCOIN
    assert result.height == 840_000
    assert result.parent_hash == "a" * 64
    assert result.source == "bitcoin_core_rpc"
    assert result.transactions[0].inputs[0].previous_transaction is None
    assert result.transactions[0].outputs[0].value_atomic == 123_456_789
    assert result.transactions[0].outputs[0].unit == "sat"
    assert result.transactions[0].outputs[0].address == "bc1qexample"


@pytest.mark.asyncio
async def test_ethereum_rpc_normalizes_values_as_integer_wei(monkeypatch):
    block = {
        "hash": "0x" + "a" * 64,
        "number": "0x10",
        "parentHash": "0x" + "b" * 64,
        "timestamp": "0x6553f100",
        "transactions": [
            {
                "hash": "0x" + "c" * 64,
                "from": "0x" + "d" * 40,
                "to": "0x" + "e" * 40,
                "value": "0xde0b6b3a7640000",
            },
            {
                "hash": "0x" + "f" * 64,
                "from": "0x" + "d" * 40,
                "to": None,
                "value": "0x0",
            },
        ],
    }

    def handler(request):
        payload = json.loads(request.content)
        assert payload["method"] == "eth_getBlockByNumber"
        assert payload["params"] == ["0x10", True]
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": block})

    requests = mock_rpc(monkeypatch, handler)
    result = await EthereumJsonRpcClient("https://node.example.test/rpc").get_block(16)

    assert len(requests) == 1
    assert result.chain is ChainName.ETHEREUM
    assert result.height == 16
    assert result.source == "ethereum_json_rpc"
    assert result.transactions[0].inputs[0].address == "0x" + "d" * 40
    assert result.transactions[0].outputs[0].value_atomic == 10**18
    assert result.transactions[0].outputs[0].unit == "wei"
    assert result.transactions[1].outputs == ()


@pytest.mark.asyncio
async def test_ethereum_forensics_normalizes_transfer_logs_by_block_hash(monkeypatch):
    block = {
        "hash": "0x" + "a" * 64,
        "number": "0x10",
        "parentHash": "0x" + "b" * 64,
        "timestamp": "0x6553f100",
        "transactions": [
            {
                "hash": "0x" + "c" * 64,
                "from": "0x" + "1" * 40,
                "to": "0x" + "2" * 40,
                "value": "0x0",
            },
            {
                "hash": "0x" + "d" * 64,
                "from": "0x" + "1" * 40,
                "to": "0x" + "2" * 40,
                "value": "0x0",
            },
        ],
    }
    transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    from_topic = "0x" + "0" * 24 + "1" * 40
    to_topic = "0x" + "0" * 24 + "2" * 40
    logs = [
        {
            "address": "0x" + "3" * 40,
            "topics": [transfer_topic, from_topic, to_topic],
            "data": hex(15).replace("0x", "0x" + "0" * 63),
            "transactionHash": "0x" + "c" * 64,
            "blockHash": block["hash"],
            "blockNumber": "0x10",
            "logIndex": "0x0",
            "removed": False,
        },
        {
            "address": "0x" + "4" * 40,
            "topics": [transfer_topic, from_topic, to_topic, "0x" + "0" * 63 + "7"],
            "data": "0x",
            "transactionHash": "0x" + "d" * 64,
            "blockHash": block["hash"],
            "blockNumber": "0x10",
            "logIndex": "0x1",
            "removed": False,
        },
    ]

    def handler(request):
        payload = json.loads(request.content)
        if payload["method"] == "eth_getBlockByNumber":
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": block})
        assert payload["method"] == "eth_getLogs"
        assert payload["params"] == [{"blockHash": block["hash"]}]
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": logs})

    requests = mock_rpc(monkeypatch, handler)
    normalized_block, normalized_logs, transfers = await EthereumJsonRpcClient(
        "https://node.example.test/rpc"
    ).get_block_logs(16)

    assert normalized_block.block_hash == block["hash"]
    assert len(requests) == 2
    assert len(normalized_logs) == 2
    assert transfers[0].token_contract == "0x" + "3" * 40
    assert transfers[0].from_address == "0x" + "1" * 40
    assert transfers[0].to_address == "0x" + "2" * 40
    assert transfers[0].value_atomic == 15
    assert transfers[0].token_id is None
    assert transfers[1].token_id == 7
    assert transfers[1].value_atomic is None
    assert transfers[0].confidence == "provider_observed_log_unverified"


@pytest.mark.asyncio
async def test_ethereum_forensics_rejects_log_from_different_block(monkeypatch):
    block = {
        "hash": "0x" + "a" * 64,
        "number": "0x10",
        "parentHash": "0x" + "b" * 64,
        "timestamp": "0x6553f100",
        "transactions": [
            {
                "hash": "0x" + "c" * 64,
                "from": "0x" + "1" * 40,
                "to": "0x" + "2" * 40,
                "value": "0x0",
            }
        ],
    }

    def handler(request):
        payload = json.loads(request.content)
        if payload["method"] == "eth_getBlockByNumber":
            result = block
        else:
            result = [
                {
                    "address": "0x" + "1" * 40,
                    "topics": [],
                    "data": "0x",
                    "transactionHash": "0x" + "c" * 64,
                    "blockHash": "0x" + "d" * 64,
                    "blockNumber": "0x10",
                    "logIndex": "0x0",
                    "removed": False,
                }
            ]
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": result})

    mock_rpc(monkeypatch, handler)
    with pytest.raises(OnChainProviderError, match="another block"):
        await EthereumJsonRpcClient("https://node.example.test/rpc").get_block_logs(16)


def test_trace_normalization_bounds_tree_and_withholds_calldata():
    result = _normalize_call_trace(
        {
            "type": "CALL",
            "from": "0x" + "1" * 40,
            "to": "0x" + "2" * 40,
            "value": "0x10",
            "gas": "0x100",
            "gasUsed": "0x80",
            "input": "0xa9059cbb" + "0" * 64,
            "calls": [
                {
                    "type": "STATICCALL",
                    "from": "0x" + "2" * 40,
                    "to": "0x" + "3" * 40,
                    "value": "0x0",
                    "input": "0x",
                }
            ],
        }
    )

    assert result.call_type == "CALL"
    assert result.value_atomic == 16
    assert result.gas_used == 128
    assert result.input_selector == "0xa9059cbb"
    assert result.input_bytes == 36
    assert result.calls[0].call_type == "STATICCALL"
    assert "input" not in result.model_dump()


def test_forensics_rejects_trace_depth_and_response_size_over_limits(monkeypatch):
    call = {
        "type": "CALL",
        "from": "0x" + "1" * 40,
        "to": "0x" + "2" * 40,
        "value": "0x0",
        "input": "0x",
    }
    monkeypatch.setattr("sanctum_suite.core.onchain._MAX_TRACE_DEPTH", 0)
    with pytest.raises(OnChainProviderError, match="nesting limit"):
        _normalize_call_trace({**call, "calls": [call]})

    block = OnChainBlock(
        chain=ChainName.ETHEREUM,
        block_hash="0x" + "a" * 64,
        height=1,
        parent_hash="0x" + "b" * 64,
        timestamp="2026-10-19T12:00:00Z",
        fetched_at="2026-10-19T12:01:00Z",
        source="ethereum_json_rpc",
        transactions=(
            OnChainTransaction(
                transaction_hash="0x" + "c" * 64,
                inputs=(),
                outputs=(),
            ),
        ),
    )
    monkeypatch.setattr("sanctum_suite.core.onchain._MAX_ETHEREUM_LOG_BYTES", 0)
    with pytest.raises(OnChainProviderError, match="no partial result"):
        _normalize_ethereum_logs(
            [
                {
                    "address": "0x" + "1" * 40,
                    "topics": [],
                    "data": "0x",
                    "transactionHash": "0x" + "c" * 64,
                    "blockHash": block.block_hash,
                    "blockNumber": "0x1",
                    "logIndex": "0x0",
                    "removed": False,
                }
            ],
            block,
        )


@pytest.mark.asyncio
async def test_ethereum_trace_checks_canonical_block_and_uses_fixed_tracer(monkeypatch):
    transaction_hash = "0x" + "c" * 64
    block_hash = "0x" + "a" * 64
    requests = []

    def handler(request):
        payload = json.loads(request.content)
        requests.append(payload)
        if payload["method"] == "eth_getTransactionByHash":
            result = {
                "hash": transaction_hash,
                "blockNumber": "0x10",
                "blockHash": block_hash,
            }
        elif payload["method"] == "eth_getBlockByNumber":
            result = {"hash": block_hash, "number": "0x10"}
        else:
            assert payload["method"] == "debug_traceTransaction"
            result = {
                "type": "CALL",
                "from": "0x" + "1" * 40,
                "to": "0x" + "2" * 40,
                "value": "0x0",
                "input": "0x",
            }
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": result})

    mock_rpc(monkeypatch, handler)
    result = await EthereumJsonRpcClient(
        "https://node.example.test/rpc"
    ).trace_transaction(transaction_hash)

    assert requests[0]["method"] == "eth_getTransactionByHash"
    assert requests[1]["params"] == ["0x10", False]
    assert requests[2]["params"] == [
        transaction_hash,
        {"tracer": "callTracer", "tracerConfig": {"onlyTopCall": False}},
    ]
    assert requests[3]["method"] == "eth_getBlockByNumber"
    assert result["block_hash"] == block_hash
    assert result["trace"]["from_address"] == "0x" + "1" * 40
    assert "calldata" in result["limitations"][2]


@pytest.mark.asyncio
async def test_rpc_error_does_not_expose_provider_message(monkeypatch):
    def handler(_request):
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"code": -32000, "message": "private node detail"},
            },
        )

    mock_rpc(monkeypatch, handler)
    with pytest.raises(OnChainProviderError, match="provider error code -32000") as error:
        await EthereumJsonRpcClient("https://node.example.test/rpc").get_block(1)

    assert "private node detail" not in str(error.value)


@pytest.mark.parametrize(
    "endpoint",
    [
        "file:///tmp/node",
        "https://user:password@node.example.test/rpc",
        "https://node.example.test/rpc#fragment",
    ],
)
def test_rpc_client_rejects_unsafe_endpoint_shapes(endpoint):
    with pytest.raises(ValueError, match="RPC endpoint"):
        EthereumJsonRpcClient(endpoint)


@pytest.mark.parametrize("height", [-1, True])
@pytest.mark.asyncio
async def test_clients_reject_invalid_block_heights_without_rpc(height):
    with pytest.raises(ValueError, match="block height"):
        await EthereumJsonRpcClient("http://127.0.0.1:8545").get_block(height)
