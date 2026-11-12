from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote, urlparse

import httpx

from sanctum_suite.core.audit_chain import (
    canonical_json,
    merkle_consistency_proof,
    merkle_tree_root,
    verify_merkle_consistency_proof,
)
from sanctum_suite.core.tee_attestation import TEEAttestation


_ZERO_HASH = "0" * 64
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_LEDGER_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_MAX_RESPONSE_BYTES = 16 * 1024


class PrivateLedgerError(RuntimeError):
    """Raised when a private-ledger anchor cannot be safely stored or confirmed."""


class CheckpointLedger(Protocol):
    def anchor(self, anchor: dict[str, Any]) -> dict[str, Any]: ...


def _validate_anchor(anchor: dict[str, Any]) -> None:
    if not isinstance(anchor, dict) or set(anchor) != {
        "schema_version",
        "checkpoint_sha256",
        "anchored_at",
    }:
        raise PrivateLedgerError("Ledger anchor must contain only digest metadata")
    if (
        isinstance(anchor["schema_version"], bool)
        or anchor["schema_version"] != 1
        or not isinstance(anchor["checkpoint_sha256"], str)
        or not _SHA256.fullmatch(anchor["checkpoint_sha256"])
        or not isinstance(anchor["anchored_at"], str)
    ):
        raise PrivateLedgerError("Ledger anchor fields are invalid")
    try:
        parsed = datetime.fromisoformat(
            anchor["anchored_at"].replace("Z", "+00:00")
        )
    except ValueError as error:
        raise PrivateLedgerError("Ledger anchor timestamp is invalid") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PrivateLedgerError("Ledger anchor timestamp must include a timezone")


class LocalPrivateLedger:
    """Demonstration SQLite ledger with an append-only, hash-linked record table."""

    def __init__(self, database_file: Path) -> None:
        if not database_file.parent.is_dir():
            raise PrivateLedgerError("Local ledger parent directory must exist")
        self._database_file = database_file

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_file, timeout=5.0)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ledger_anchors (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    schema_version INTEGER NOT NULL,
                    checkpoint_sha256 TEXT NOT NULL UNIQUE,
                    anchored_at TEXT NOT NULL,
                    previous_entry_sha256 TEXT NOT NULL,
                    entry_sha256 TEXT NOT NULL UNIQUE
                )
                """
            )
            connection.executescript(
                """
                CREATE TRIGGER IF NOT EXISTS ledger_anchors_no_update
                BEFORE UPDATE ON ledger_anchors
                BEGIN
                    SELECT RAISE(ABORT, 'ledger anchors are append-only');
                END;
                CREATE TRIGGER IF NOT EXISTS ledger_anchors_no_delete
                BEFORE DELETE ON ledger_anchors
                BEGIN
                    SELECT RAISE(ABORT, 'ledger anchors are append-only');
                END;
                """
            )
            if self._database_file.exists():
                self._database_file.chmod(0o600)
        except OSError as error:
            connection.close()
            raise PrivateLedgerError("Could not protect local ledger file") from error
        except sqlite3.Error:
            connection.close()
            raise
        return connection

    @staticmethod
    def _entry_digest(
        *,
        schema_version: int,
        checkpoint_sha256: str,
        anchored_at: str,
        previous_entry_sha256: str,
    ) -> str:
        return hashlib.sha256(
            canonical_json(
                {
                    "schema_version": schema_version,
                    "checkpoint_sha256": checkpoint_sha256,
                    "anchored_at": anchored_at,
                    "previous_entry_sha256": previous_entry_sha256,
                }
            )
        ).hexdigest()

    def _verify(self, connection: sqlite3.Connection) -> str:
        previous = _ZERO_HASH
        rows = connection.execute(
            """
            SELECT sequence, schema_version, checkpoint_sha256, anchored_at,
                   previous_entry_sha256, entry_sha256
            FROM ledger_anchors
            ORDER BY sequence
            """
        )
        for expected_sequence, row in enumerate(rows, start=1):
            anchor = {
                "schema_version": row["schema_version"],
                "checkpoint_sha256": row["checkpoint_sha256"],
                "anchored_at": row["anchored_at"],
            }
            try:
                _validate_anchor(anchor)
            except PrivateLedgerError as error:
                raise PrivateLedgerError("Local ledger integrity verification failed") from error
            expected_hash = self._entry_digest(
                schema_version=row["schema_version"],
                checkpoint_sha256=row["checkpoint_sha256"],
                anchored_at=row["anchored_at"],
                previous_entry_sha256=previous,
            )
            if (
                row["sequence"] != expected_sequence
                or row["previous_entry_sha256"] != previous
                or row["entry_sha256"] != expected_hash
            ):
                raise PrivateLedgerError("Local ledger hash chain is invalid")
            previous = expected_hash
        return previous

    @staticmethod
    def _transparency_leaves(connection: sqlite3.Connection) -> list[bytes]:
        rows = connection.execute(
            """
            SELECT sequence, schema_version, checkpoint_sha256, anchored_at,
                   previous_entry_sha256, entry_sha256
            FROM ledger_anchors
            ORDER BY sequence
            """
        )
        return [
            canonical_json(
                {
                    "sequence": row["sequence"],
                    "schema_version": row["schema_version"],
                    "checkpoint_sha256": row["checkpoint_sha256"],
                    "anchored_at": row["anchored_at"],
                    "previous_entry_sha256": row["previous_entry_sha256"],
                    "entry_sha256": row["entry_sha256"],
                }
            )
            for row in rows
        ]

    def anchor(self, anchor: dict[str, Any]) -> dict[str, Any]:
        _validate_anchor(anchor)
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                head = self._verify(connection)
                existing = connection.execute(
                    """
                    SELECT sequence, entry_sha256, anchored_at
                    FROM ledger_anchors
                    WHERE checkpoint_sha256 = ?
                    """,
                    (anchor["checkpoint_sha256"],),
                ).fetchone()
                if existing is not None:
                    connection.commit()
                    return {
                        "status": "LEDGER_ANCHOR_ALREADY_PRESENT",
                        "backend": "local-private-ledger-demo",
                        "checkpoint_sha256": anchor["checkpoint_sha256"],
                        "anchored_at": existing["anchored_at"],
                        "entry_sha256": existing["entry_sha256"],
                        "sequence": existing["sequence"],
                    }
                entry_hash = self._entry_digest(
                    schema_version=anchor["schema_version"],
                    checkpoint_sha256=anchor["checkpoint_sha256"],
                    anchored_at=anchor["anchored_at"],
                    previous_entry_sha256=head,
                )
                cursor = connection.execute(
                    """
                    INSERT INTO ledger_anchors (
                        schema_version, checkpoint_sha256, anchored_at,
                        previous_entry_sha256, entry_sha256
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        anchor["schema_version"],
                        anchor["checkpoint_sha256"],
                        anchor["anchored_at"],
                        head,
                        entry_hash,
                    ),
                )
                sequence = cursor.lastrowid
                connection.commit()
        except (OSError, sqlite3.Error) as error:
            raise PrivateLedgerError("Local private-ledger write failed") from error
        return {
            "status": "LEDGER_ANCHOR_COMMITTED",
            "backend": "local-private-ledger-demo",
            "checkpoint_sha256": anchor["checkpoint_sha256"],
            "anchored_at": anchor["anchored_at"],
            "entry_sha256": entry_hash,
            "sequence": sequence,
        }

    def verify(self) -> dict[str, Any]:
        try:
            with self._connect() as connection:
                head = self._verify(connection)
                leaves = self._transparency_leaves(connection)
        except (OSError, sqlite3.Error) as error:
            raise PrivateLedgerError("Local private-ledger verification failed") from error
        tree_root = merkle_tree_root(leaves)
        return {
            "status": "LOCAL_LEDGER_VERIFIED",
            "backend": "local-private-ledger-demo",
            "record_count": len(leaves),
            "chain_head_sha256": head,
            "tree_size": len(leaves),
            "tree_root_sha256": tree_root,
        }

    def consistency_proof(
        self,
        *,
        old_tree_size: int,
        old_tree_root_sha256: str,
    ) -> dict[str, Any]:
        if (
            isinstance(old_tree_size, bool)
            or not isinstance(old_tree_size, int)
            or old_tree_size < 0
            or not isinstance(old_tree_root_sha256, str)
            or not _SHA256.fullmatch(old_tree_root_sha256)
        ):
            raise PrivateLedgerError("Previous transparency tree head is invalid")
        try:
            with self._connect() as connection:
                self._verify(connection)
                leaves = self._transparency_leaves(connection)
        except (OSError, sqlite3.Error) as error:
            raise PrivateLedgerError("Local ledger consistency proof failed") from error
        if old_tree_size > len(leaves):
            raise PrivateLedgerError("Previous transparency tree size exceeds current size")
        actual_old_root = merkle_tree_root(leaves[:old_tree_size])
        if actual_old_root != old_tree_root_sha256:
            raise PrivateLedgerError(
                "Previous transparency tree head does not match this ledger history"
            )
        proof = merkle_consistency_proof(leaves, old_tree_size)
        current_root = merkle_tree_root(leaves)
        if not verify_merkle_consistency_proof(
            old_size=old_tree_size,
            new_size=len(leaves),
            old_root=old_tree_root_sha256,
            new_root=current_root,
            proof=proof,
        ):
            raise PrivateLedgerError("Generated transparency consistency proof is invalid")
        return {
            "status": "LOCAL_LEDGER_CONSISTENCY_PROOF",
            "backend": "local-private-ledger-demo",
            "old_tree_size": old_tree_size,
            "old_tree_root_sha256": old_tree_root_sha256,
            "new_tree_size": len(leaves),
            "new_tree_root_sha256": current_root,
            "proof": proof,
        }


class FabricGatewayLedger:
    """Submits digest-only anchors through an operator-managed Fabric HTTP gateway."""

    def __init__(
        self,
        *,
        gateway_url: str,
        channel: str,
        chaincode: str,
        ca_certificate_file: Path,
        client_certificate_file: Path,
        client_key_file: Path,
        client: httpx.Client | None = None,
    ) -> None:
        parsed = urlparse(gateway_url)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise PrivateLedgerError(
                "Fabric gateway URL must be HTTPS without credentials, query, or fragment"
            )
        if not _LEDGER_IDENTIFIER.fullmatch(channel) or not _LEDGER_IDENTIFIER.fullmatch(
            chaincode
        ):
            raise PrivateLedgerError("Fabric channel or chaincode name is invalid")
        for path, label in (
            (ca_certificate_file, "Fabric gateway CA"),
            (client_certificate_file, "Fabric client certificate"),
            (client_key_file, "Fabric client key"),
        ):
            if not path.is_file():
                raise PrivateLedgerError(f"{label} file does not exist")
        self._endpoint = (
            f"{gateway_url.rstrip('/')}/api/v1/channels/{quote(channel, safe='')}"
            f"/chaincodes/{quote(chaincode, safe='')}/anchors"
        )
        self._verify = str(ca_certificate_file)
        self._cert = (str(client_certificate_file), str(client_key_file))
        self._client = client

    def anchor(self, anchor: dict[str, Any]) -> dict[str, Any]:
        _validate_anchor(anchor)
        owned_client = self._client is None
        client = self._client or httpx.Client(
            verify=self._verify,
            cert=self._cert,
            timeout=httpx.Timeout(10.0, connect=2.0),
            follow_redirects=False,
        )
        try:
            with client.stream(
                "POST",
                self._endpoint,
                headers={
                    "Accept": "application/json",
                    "Idempotency-Key": anchor["checkpoint_sha256"],
                },
                json=anchor,
            ) as response:
                if response.status_code not in {200, 201}:
                    raise PrivateLedgerError(
                        "Fabric gateway rejected anchor with HTTP "
                        f"{response.status_code}"
                    )
                body = bytearray()
                for chunk in response.iter_bytes(chunk_size=4_096):
                    body.extend(chunk)
                    if len(body) > _MAX_RESPONSE_BYTES:
                        raise PrivateLedgerError(
                            "Fabric gateway response exceeded its size limit"
                        )
            document = json.loads(body)
        except PrivateLedgerError:
            raise
        except (httpx.HTTPError, json.JSONDecodeError, ValueError) as error:
            raise PrivateLedgerError("Fabric gateway request or response failed") from error
        finally:
            if owned_client:
                client.close()
        if (
            not isinstance(document, dict)
            or document.get("status") != "COMMITTED"
            or document.get("checkpoint_sha256") != anchor["checkpoint_sha256"]
            or not isinstance(document.get("tx_id"), str)
            or not _LEDGER_IDENTIFIER.fullmatch(document["tx_id"])
        ):
            raise PrivateLedgerError(
                "Fabric gateway did not confirm the expected committed anchor"
            )
        return {
            "status": "LEDGER_ANCHOR_COMMITTED",
            "backend": "hyperledger-fabric",
            "checkpoint_sha256": anchor["checkpoint_sha256"],
            "anchored_at": anchor["anchored_at"],
            "transaction_id": document["tx_id"],
        }


def anchor_verified_checkpoint(
    *,
    checkpoint_bytes: bytes,
    attestation: TEEAttestation,
    ledger: CheckpointLedger,
) -> dict[str, Any]:
    if attestation.tee_type not in {"snp", "sgx", "tdx"}:
        raise PrivateLedgerError("A supported fresh TEE attestation is required")
    if not checkpoint_bytes:
        raise PrivateLedgerError("Verified checkpoint must not be empty")
    checkpoint_sha256 = hashlib.sha256(checkpoint_bytes).hexdigest()
    if attestation.operation_digest != checkpoint_sha256:
        raise PrivateLedgerError(
            "TEE attestation is not bound to this checkpoint digest"
        )
    anchor = {
        "schema_version": 1,
        "checkpoint_sha256": checkpoint_sha256,
        "anchored_at": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
    }
    result = ledger.anchor(anchor)
    result["tee_type"] = attestation.tee_type
    result["workload_id"] = attestation.workload_id
    return result
