"""Read-only, normalized data access for operator-configured blockchain RPC nodes."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ChainName(StrEnum):
    BITCOIN = "bitcoin"
    ETHEREUM = "ethereum"


class OnChainProviderError(RuntimeError):
    """An RPC provider returned an invalid or unsuccessful response."""


class TransactionOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    index: int = Field(ge=0)
    address: str | None = Field(default=None, min_length=1, max_length=256)
    value_atomic: int = Field(ge=0)
    unit: str = Field(min_length=1, max_length=16)


class TransactionInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    previous_transaction: str | None = Field(default=None, min_length=1, max_length=128)
    previous_output_index: int | None = Field(default=None, ge=0)
    address: str | None = Field(default=None, min_length=1, max_length=256)
    value_atomic: int | None = Field(default=None, ge=0)
    unit: str = Field(min_length=1, max_length=16)

    @model_validator(mode="after")
    def validate_outpoint(self) -> TransactionInput:
        if (self.previous_transaction is None) != (self.previous_output_index is None):
            raise ValueError("previous transaction and output index must be provided together")
        return self


class OnChainTransaction(BaseModel):
    model_config = ConfigDict(frozen=True)

    transaction_hash: str = Field(min_length=1, max_length=128)
    inputs: tuple[TransactionInput, ...]
    outputs: tuple[TransactionOutput, ...]


class OnChainBlock(BaseModel):
    model_config = ConfigDict(frozen=True)

    chain: ChainName
    block_hash: str = Field(min_length=1, max_length=128)
    height: int = Field(ge=0)
    parent_hash: str | None = Field(default=None, min_length=1, max_length=128)
    timestamp: datetime
    transactions: tuple[OnChainTransaction, ...]
    source: str = Field(min_length=1, max_length=64)
    fetched_at: datetime

    @field_validator("timestamp", "fetched_at")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must include a timezone")
        return value


def _validate_height(height: Any) -> None:
        if (
            isinstance(height, bool)
            or not isinstance(height, int)
            or height < 0
            or height > 2**64 - 1
        ):
            raise ValueError("block height must be an integer from 0 to 2^64-1")


class EthereumLog(BaseModel):
    model_config = ConfigDict(frozen=True)

    address: str
    topics: tuple[str, ...]
    data: str
    transaction_hash: str
    block_hash: str
    block_number: int = Field(ge=0)
    log_index: int = Field(ge=0)
    removed: bool


class EthereumTransferObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    token_contract: str
    transaction_hash: str
    block_hash: str
    block_number: int = Field(ge=0)
    log_index: int = Field(ge=0)
    from_address: str
    to_address: str
    value_atomic: int | None = Field(default=None, ge=0)
    token_id: int | None = Field(default=None, ge=0)
    interpretation: str = "standard_transfer_event_shape"
    confidence: str = "provider_observed_log_unverified"


class EthereumCallTrace(BaseModel):
    model_config = ConfigDict(frozen=True)

    call_type: str
    from_address: str
    to_address: str | None
    value_atomic: int
    gas_limit: int | None
    gas_used: int | None
    input_selector: str | None
    input_bytes: int
    error: str | None
    calls: tuple[EthereumCallTrace, ...]


class _JsonRpcClient:
    def __init__(
        self,
        endpoint: str,
        *,
        username: str | None = None,
        password: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        parsed = urlsplit(endpoint)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            raise ValueError("RPC endpoint must be an HTTP(S) URL without embedded credentials or fragment")
        if (username is None) != (password is None):
            raise ValueError("RPC username and password must be configured together")
        if username is not None and (not username or not password):
            raise ValueError("RPC username and password cannot be empty")
        if not 0 < timeout <= 120:
            raise ValueError("RPC timeout must be greater than 0 and at most 120 seconds")
        self._endpoint = endpoint
        self._auth = (username, password) if username is not None and password is not None else None
        self._timeout = timeout

    async def call(self, method: str, params: list[Any]) -> Any:
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        try:
            async with httpx.AsyncClient(
                auth=self._auth,
                timeout=self._timeout,
                verify=True,
                follow_redirects=False,
            ) as client:
                async with client.stream("POST", self._endpoint, json=payload) as response:
                    if response.status_code != 200:
                        raise OnChainProviderError(
                            f"RPC provider returned HTTP status {response.status_code}"
                        )
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > 16 * 1024 * 1024:
                            raise OnChainProviderError("RPC response exceeded the 16 MiB limit")
        except httpx.HTTPError as error:
            raise OnChainProviderError("RPC provider request failed") from error

        try:
            envelope = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise OnChainProviderError("RPC provider returned invalid JSON") from error
        if (
            not isinstance(envelope, dict)
            or isinstance(envelope.get("id"), bool)
            or envelope.get("id") != 1
            or envelope.get("jsonrpc") != "2.0"
        ):
            raise OnChainProviderError("RPC provider returned an invalid response envelope")
        rpc_error = envelope.get("error")
        if rpc_error is not None:
            code = rpc_error.get("code") if isinstance(rpc_error, dict) else None
            if not isinstance(code, int):
                raise OnChainProviderError("RPC provider returned an invalid error object")
            raise OnChainProviderError(f"RPC method failed with provider error code {code}")
        if "result" not in envelope:
            raise OnChainProviderError("RPC provider response is missing its result")
        return envelope["result"]


class BitcoinCoreClient:
    """Fetches a Bitcoin block and its transactions from Bitcoin Core RPC."""

    source = "bitcoin_core_rpc"

    def __init__(
        self,
        endpoint: str,
        *,
        username: str | None = None,
        password: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._rpc = _JsonRpcClient(
            endpoint, username=username, password=password, timeout=timeout
        )

    async def get_block(self, height: int) -> OnChainBlock:
        _validate_height(height)
        block_hash = await self._rpc.call("getblockhash", [height])
        if not isinstance(block_hash, str) or not block_hash:
            raise OnChainProviderError("Bitcoin Core returned an invalid block hash")
        raw = await self._rpc.call("getblock", [block_hash, 2])
        try:
            return _normalize_bitcoin_block(raw)
        except OnChainProviderError:
            raise
        except (ValueError, TypeError, OverflowError, OSError) as error:
            raise OnChainProviderError("Bitcoin Core returned invalid block data") from error


class EthereumJsonRpcClient:
    """Fetches a full Ethereum block by number from an Ethereum JSON-RPC node."""

    source = "ethereum_json_rpc"

    def __init__(self, endpoint: str, *, timeout: float = 10.0) -> None:
        self._rpc = _JsonRpcClient(endpoint, timeout=timeout)

    async def get_block(self, height: int) -> OnChainBlock:
        _validate_height(height)
        raw = await self._rpc.call("eth_getBlockByNumber", [hex(height), True])
        try:
            return _normalize_ethereum_block(raw)
        except OnChainProviderError:
            raise
        except (ValueError, TypeError, OverflowError, OSError) as error:
            raise OnChainProviderError("Ethereum node returned invalid block data") from error

    async def get_block_logs(
        self,
        height: int,
    ) -> tuple[OnChainBlock, tuple[EthereumLog, ...], tuple[EthereumTransferObservation, ...]]:
        block = await self.get_block(height)
        raw_logs = await self._rpc.call("eth_getLogs", [{"blockHash": block.block_hash}])
        logs, transfers = _normalize_ethereum_logs(raw_logs, block)
        return block, logs, transfers

    async def trace_transaction(self, transaction_hash: str) -> dict[str, Any]:
        if not re.fullmatch(r"0x[0-9a-fA-F]{64}", transaction_hash):
            raise ValueError("transaction_hash must be a 32-byte EVM hash")
        normalized_hash = transaction_hash.lower()
        transaction = _require_mapping(
            await self._rpc.call("eth_getTransactionByHash", [normalized_hash]),
            "Ethereum node",
            "transaction",
        )
        if _require_string(transaction.get("hash"), "Ethereum node", "transaction hash").lower() != normalized_hash:
            raise OnChainProviderError("Ethereum node returned a mismatched transaction")
        height = _ethereum_quantity(transaction.get("blockNumber"), "transaction block number")
        try:
            _validate_height(height)
        except ValueError as error:
            raise OnChainProviderError(
                "Ethereum node returned an invalid transaction block number"
            ) from error
        block_hash = _require_string(
            transaction.get("blockHash"),
            "Ethereum node",
            "transaction block hash",
        )
        if not re.fullmatch(r"0x[0-9a-fA-F]{64}", block_hash):
            raise OnChainProviderError("Ethereum node returned an invalid transaction block hash")
        block_header = _require_mapping(
            await self._rpc.call("eth_getBlockByNumber", [hex(height), False]),
            "Ethereum node",
            "block header",
        )
        canonical_hash = _require_string(
            block_header.get("hash"),
            "Ethereum node",
            "block hash",
        )
        canonical_height = _ethereum_quantity(
            block_header.get("number"),
            "block number",
        )
        if (
            canonical_hash.lower() != block_hash.lower()
            or canonical_height != height
        ):
            raise OnChainProviderError("Transaction block changed during trace lookup")
        raw_trace = await self._rpc.call(
            "debug_traceTransaction",
            [
                normalized_hash,
                {
                    "tracer": "callTracer",
                    "tracerConfig": {"onlyTopCall": False},
                },
            ],
        )
        trace_root = _normalize_call_trace(raw_trace)
        final_header = _require_mapping(
            await self._rpc.call("eth_getBlockByNumber", [hex(height), False]),
            "Ethereum node",
            "block header",
        )
        final_hash = _require_string(
            final_header.get("hash"),
            "Ethereum node",
            "block hash",
        )
        final_height = _ethereum_quantity(
            final_header.get("number"),
            "block number",
        )
        if final_hash.lower() != block_hash.lower() or final_height != height:
            raise OnChainProviderError("Transaction block changed during trace lookup")
        return {
            "chain": ChainName.ETHEREUM.value,
            "transaction_hash": normalized_hash,
            "block_hash": block_hash,
            "block_height": height,
            "source": self.source,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "confidence": "provider_observed_trace_unverified",
            "trace": _call_trace_response(trace_root),
            "limitations": [
                "Trace data is provider output from the configured node and is not independently verified.",
                "A call trace is not an entity attribution, AML decision, or proof of legal compliance.",
                "Only the callTracer fields required for bounded review are returned; calldata and return data are withheld.",
            ],
        }


def _require_mapping(value: Any, provider: str, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise OnChainProviderError(f"{provider} block has an invalid {field}")
    return value


def _require_string(value: Any, provider: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise OnChainProviderError(f"{provider} block has an invalid {field}")
    return value


def _bitcoin_atomic_units(value: Any) -> int:
    try:
        amount = Decimal(str(value)) * Decimal(100_000_000)
    except (InvalidOperation, ValueError) as error:
        raise OnChainProviderError("Bitcoin Core returned an invalid output amount") from error
    if not amount.is_finite() or amount < 0 or amount != amount.to_integral_value():
        raise OnChainProviderError("Bitcoin Core returned an invalid output amount")
    return int(amount)


def _bitcoin_timestamp(value: Any) -> datetime:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise OnChainProviderError("Bitcoin Core returned an invalid block timestamp")
    return datetime.fromtimestamp(value, timezone.utc)


def _normalize_bitcoin_block(raw: Any) -> OnChainBlock:
    block = _require_mapping(raw, "Bitcoin Core", "object")
    transactions = block.get("tx")
    if not isinstance(transactions, list):
        raise OnChainProviderError("Bitcoin Core block is missing its transaction list")
    normalized_transactions: list[OnChainTransaction] = []
    for raw_transaction in transactions:
        transaction = _require_mapping(raw_transaction, "Bitcoin Core", "transaction")
        inputs: list[TransactionInput] = []
        raw_inputs = transaction.get("vin")
        if not isinstance(raw_inputs, list):
            raise OnChainProviderError("Bitcoin Core transaction has an invalid input list")
        for index, raw_input in enumerate(raw_inputs):
            tx_input = _require_mapping(raw_input, "Bitcoin Core", "input")
            previous_transaction = tx_input.get("txid")
            previous_output_index = tx_input.get("vout")
            if previous_transaction is None and previous_output_index is None:
                inputs.append(TransactionInput(unit="sat"))
                continue
            if (
                not isinstance(previous_transaction, str)
                or not previous_transaction
                or isinstance(previous_output_index, bool)
                or not isinstance(previous_output_index, int)
                or previous_output_index < 0
            ):
                raise OnChainProviderError("Bitcoin Core transaction has an invalid outpoint")
            inputs.append(
                TransactionInput(
                    previous_transaction=previous_transaction,
                    previous_output_index=previous_output_index,
                    unit="sat",
                )
            )

        outputs: list[TransactionOutput] = []
        raw_outputs = transaction.get("vout")
        if not isinstance(raw_outputs, list):
            raise OnChainProviderError("Bitcoin Core transaction has an invalid output list")
        for index, raw_output in enumerate(raw_outputs):
            output = _require_mapping(raw_output, "Bitcoin Core", "output")
            script = output.get("scriptPubKey")
            addresses: list[str] = []
            if isinstance(script, dict):
                address = script.get("address")
                if isinstance(address, str) and address:
                    addresses.append(address)
            outputs.append(
                TransactionOutput(
                    index=_require_nonnegative_int(output.get("n", index), "output index"),
                    address=addresses[0] if addresses else None,
                    value_atomic=_bitcoin_atomic_units(output.get("value")),
                    unit="sat",
                )
            )
        normalized_transactions.append(
            OnChainTransaction(
                transaction_hash=_require_string(transaction.get("txid"), "Bitcoin Core", "transaction hash"),
                inputs=tuple(inputs),
                outputs=tuple(outputs),
            )
        )

    fetched_at = datetime.now(timezone.utc)
    return OnChainBlock(
        chain=ChainName.BITCOIN,
        block_hash=_require_string(block.get("hash"), "Bitcoin Core", "block hash"),
        height=_require_nonnegative_int(block.get("height"), "block height"),
        parent_hash=block.get("previousblockhash"),
        timestamp=_bitcoin_timestamp(block.get("time")),
        transactions=tuple(normalized_transactions),
        source=BitcoinCoreClient.source,
        fetched_at=fetched_at,
    )


def _ethereum_quantity(value: Any, field: str) -> int:
    if not isinstance(value, str) or not re.fullmatch(r"0x[0-9a-fA-F]+", value):
        raise OnChainProviderError(f"Ethereum node returned an invalid {field}")
    try:
        result = int(value[2:], 16)
    except ValueError as error:
        raise OnChainProviderError(f"Ethereum node returned an invalid {field}") from error
    return result


def _ethereum_timestamp(value: Any) -> datetime:
    timestamp = _ethereum_quantity(value, "block timestamp")
    try:
        return datetime.fromtimestamp(timestamp, timezone.utc)
    except (OverflowError, OSError, ValueError) as error:
        raise OnChainProviderError("Ethereum node returned an invalid block timestamp") from error


def _normalize_ethereum_block(raw: Any) -> OnChainBlock:
    block = _require_mapping(raw, "Ethereum node", "object")
    transactions = block.get("transactions")
    if not isinstance(transactions, list):
        raise OnChainProviderError("Ethereum block is missing its transaction list")
    normalized_transactions: list[OnChainTransaction] = []
    for raw_transaction in transactions:
        transaction = _require_mapping(raw_transaction, "Ethereum node", "transaction")
        sender = _require_string(transaction.get("from"), "Ethereum node", "transaction sender")
        recipient = transaction.get("to")
        if recipient is not None and not isinstance(recipient, str):
            raise OnChainProviderError("Ethereum node returned an invalid transaction recipient")
        outputs = (
            (
                TransactionOutput(
                    index=0,
                    address=recipient,
                    value_atomic=_ethereum_quantity(transaction.get("value"), "transaction value"),
                    unit="wei",
                ),
            )
            if recipient is not None
            else ()
        )
        normalized_transactions.append(
            OnChainTransaction(
                transaction_hash=_require_string(transaction.get("hash"), "Ethereum node", "transaction hash"),
                inputs=(TransactionInput(address=sender, unit="wei"),),
                outputs=outputs,
            )
        )

    return OnChainBlock(
        chain=ChainName.ETHEREUM,
        block_hash=_require_string(block.get("hash"), "Ethereum node", "block hash"),
        height=_ethereum_quantity(block.get("number"), "block number"),
        parent_hash=_require_string(block.get("parentHash"), "Ethereum node", "parent hash"),
        timestamp=_ethereum_timestamp(block.get("timestamp")),
        transactions=tuple(normalized_transactions),
        source=EthereumJsonRpcClient.source,
        fetched_at=datetime.now(timezone.utc),
    )


_TRANSFER_EVENT_TOPIC = (
    "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
)
_MAX_ETHEREUM_LOGS = 5_000
_MAX_ETHEREUM_LOG_BYTES = 8 * 1024 * 1024
_MAX_TRACE_CALLS = 10_000
_MAX_TRACE_DEPTH = 32
_EVM_ADDRESS = re.compile(r"0x[0-9a-fA-F]{40}")
_EVM_TOPIC = re.compile(r"0x[0-9a-fA-F]{64}")


def _normalize_ethereum_logs(
    raw_logs: Any,
    block: OnChainBlock,
) -> tuple[tuple[EthereumLog, ...], tuple[EthereumTransferObservation, ...]]:
    if not isinstance(raw_logs, list):
        raise OnChainProviderError("Ethereum node returned an invalid log list")
    if len(raw_logs) > _MAX_ETHEREUM_LOGS:
        raise OnChainProviderError(
            "Ethereum block exceeds the 5000-log forensics limit; no partial result was returned"
        )
    logs: list[EthereumLog] = []
    transfers: list[EthereumTransferObservation] = []
    seen_log_indexes: set[int] = set()
    normalized_log_bytes = 0
    block_transactions = {
        transaction.transaction_hash.lower() for transaction in block.transactions
    }

    for raw_log in raw_logs:
        item = _require_mapping(raw_log, "Ethereum node", "log")
        address = _require_string(item.get("address"), "Ethereum node", "log address")
        tx_hash = _require_string(
            item.get("transactionHash"),
            "Ethereum node",
            "log transaction hash",
        )
        log_block_hash = _require_string(
            item.get("blockHash"),
            "Ethereum node",
            "log block hash",
        )
        if not _EVM_ADDRESS.fullmatch(address):
            raise OnChainProviderError("Ethereum node returned an invalid log address")
        if not _EVM_TOPIC.fullmatch(tx_hash):
            raise OnChainProviderError("Ethereum node returned an invalid log transaction hash")
        if tx_hash.lower() not in block_transactions:
            raise OnChainProviderError(
                "Ethereum node returned a log for a transaction outside the block"
            )
        if log_block_hash.lower() != block.block_hash.lower():
            raise OnChainProviderError("Ethereum node returned a log from another block")
        block_number = _ethereum_quantity(item.get("blockNumber"), "log block number")
        if block_number != block.height:
            raise OnChainProviderError("Ethereum node returned a log at another block height")
        log_index = _ethereum_quantity(item.get("logIndex"), "log index")
        if log_index in seen_log_indexes:
            raise OnChainProviderError("Ethereum node returned duplicate log indexes")
        seen_log_indexes.add(log_index)
        removed = item.get("removed")
        if not isinstance(removed, bool):
            raise OnChainProviderError("Ethereum node returned an invalid log removal flag")
        topics = item.get("topics")
        if (
            not isinstance(topics, list)
            or len(topics) > 4
            or any(not isinstance(topic, str) or not _EVM_TOPIC.fullmatch(topic) for topic in topics)
        ):
            raise OnChainProviderError("Ethereum node returned invalid log topics")
        data = item.get("data")
        if (
            not isinstance(data, str)
            or len(data) > 131_074
            or re.fullmatch(r"0x(?:[0-9a-fA-F]{2})*", data) is None
        ):
            raise OnChainProviderError("Ethereum node returned invalid or oversized log data")

        normalized_log = EthereumLog(
            address=address.lower(),
            topics=tuple(topic.lower() for topic in topics),
            data=data.lower(),
            transaction_hash=tx_hash.lower(),
            block_hash=log_block_hash.lower(),
            block_number=block_number,
            log_index=log_index,
            removed=removed,
        )
        normalized_log_bytes += len(
            json.dumps(
                normalized_log.model_dump(mode="json"),
                separators=(",", ":"),
            ).encode("utf-8")
        )
        if normalized_log_bytes > _MAX_ETHEREUM_LOG_BYTES:
            raise OnChainProviderError(
                "Ethereum logs exceed the 8 MiB forensics result limit; no partial result was returned"
            )
        logs.append(normalized_log)
        if removed or not topics or topics[0].lower() != _TRANSFER_EVENT_TOPIC:
            continue
        if len(topics) not in {3, 4}:
            continue
        indexed_addresses = topics[1:3]
        if any(
            not topic.startswith("0x" + "0" * 24)
            for topic in indexed_addresses
        ):
            continue
        from_address = "0x" + indexed_addresses[0][-40:]
        to_address = "0x" + indexed_addresses[1][-40:]
        if len(topics) == 3 and len(data) == 66:
            transfers.append(
                EthereumTransferObservation(
                    token_contract=address.lower(),
                    transaction_hash=tx_hash.lower(),
                    block_hash=log_block_hash.lower(),
                    block_number=block_number,
                    log_index=log_index,
                    from_address=from_address,
                    to_address=to_address,
                    value_atomic=int(data[2:], 16),
                )
            )
        elif len(topics) == 4 and data == "0x":
            transfers.append(
                EthereumTransferObservation(
                    token_contract=address.lower(),
                    transaction_hash=tx_hash.lower(),
                    block_hash=log_block_hash.lower(),
                    block_number=block_number,
                    log_index=log_index,
                    from_address=from_address,
                    to_address=to_address,
                    token_id=int(topics[3][2:], 16),
                )
            )
    return tuple(logs), tuple(transfers)


def _normalize_call_trace(raw_trace: Any) -> EthereumCallTrace:
    total_calls = 0

    def normalize(raw_call: Any, depth: int) -> EthereumCallTrace:
        nonlocal total_calls
        if depth > _MAX_TRACE_DEPTH:
            raise OnChainProviderError("Ethereum call trace exceeds the 32-level nesting limit")
        total_calls += 1
        if total_calls > _MAX_TRACE_CALLS:
            raise OnChainProviderError("Ethereum call trace exceeds the 10000-call limit")
        call = _require_mapping(raw_call, "Ethereum node", "call trace")
        call_type = call.get("type", "CALL")
        sender = call.get("from")
        recipient = call.get("to")
        if not isinstance(call_type, str) or not 1 <= len(call_type) <= 32:
            raise OnChainProviderError("Ethereum node returned an invalid trace call type")
        if not isinstance(sender, str) or not _EVM_ADDRESS.fullmatch(sender):
            raise OnChainProviderError("Ethereum node returned an invalid trace sender")
        if recipient is not None and (
            not isinstance(recipient, str) or not _EVM_ADDRESS.fullmatch(recipient)
        ):
            raise OnChainProviderError("Ethereum node returned an invalid trace recipient")
        raw_input = call.get("input", "0x")
        if (
            not isinstance(raw_input, str)
            or len(raw_input) > 2_097_154
            or re.fullmatch(r"0x(?:[0-9a-fA-F]{2})*", raw_input) is None
        ):
            raise OnChainProviderError("Ethereum node returned invalid or oversized trace input")
        raw_error = call.get("error")
        if raw_error is not None and (
            not isinstance(raw_error, str)
            or len(raw_error) > 512
            or any(ord(character) < 32 for character in raw_error)
        ):
            raise OnChainProviderError("Ethereum node returned an invalid trace error")
        raw_calls = call.get("calls", [])
        if not isinstance(raw_calls, list):
            raise OnChainProviderError("Ethereum node returned an invalid nested trace list")
        return EthereumCallTrace(
            call_type=call_type.upper(),
            from_address=sender.lower(),
            to_address=recipient.lower() if recipient is not None else None,
            value_atomic=_ethereum_quantity(call.get("value", "0x0"), "trace value"),
            gas_limit=(
                _ethereum_quantity(call["gas"], "trace gas")
                if call.get("gas") is not None
                else None
            ),
            gas_used=(
                _ethereum_quantity(call["gasUsed"], "trace gas used")
                if call.get("gasUsed") is not None
                else None
            ),
            input_selector=raw_input[:10].lower() if len(raw_input) >= 10 else None,
            input_bytes=(len(raw_input) - 2) // 2,
            error=raw_error,
            calls=tuple(normalize(child, depth + 1) for child in raw_calls),
        )

    return normalize(raw_trace, 0)


def _call_trace_response(trace: EthereumCallTrace) -> dict[str, Any]:
    return {
        "call_type": trace.call_type,
        "from_address": trace.from_address,
        "to_address": trace.to_address,
        "value_atomic": str(trace.value_atomic),
        "gas_limit": str(trace.gas_limit) if trace.gas_limit is not None else None,
        "gas_used": str(trace.gas_used) if trace.gas_used is not None else None,
        "input_selector": trace.input_selector,
        "input_bytes": trace.input_bytes,
        "error": trace.error,
        "calls": [_call_trace_response(child) for child in trace.calls],
    }


def _require_nonnegative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise OnChainProviderError(f"RPC provider returned an invalid {field}")
    return value
