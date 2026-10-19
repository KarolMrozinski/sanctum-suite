"""Opt-in, case-scoped SQLite snapshots for normalized on-chain blocks."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sanctum_suite.core.onchain import ChainName, OnChainBlock


MAX_BLOCK_BYTES = 32 * 1024 * 1024
MAX_SNAPSHOTS_PER_CASE = 10_000


class OnChainStoreCapacityError(ValueError):
    """The bounded on-chain snapshot store cannot accept more data."""


class OnChainBlockStore:
    def __init__(
        self,
        db_path: str | Path,
        *,
        retention_days: int,
    ) -> None:
        if isinstance(retention_days, bool) or not isinstance(retention_days, int) or not 1 <= retention_days <= 36_500:
            raise ValueError("retention_days must be an integer from 1 to 36500")
        self.db_path = str(Path(db_path).expanduser())
        self.retention_days = retention_days
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS onchain_block_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL REFERENCES incident_cases(case_id) ON DELETE CASCADE,
                    chain TEXT NOT NULL,
                    height INTEGER NOT NULL,
                    block_hash TEXT NOT NULL,
                    parent_hash TEXT,
                    block_timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    fetched_at TEXT NOT NULL,
                    stored_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    payload_bytes INTEGER NOT NULL,
                    UNIQUE(case_id, chain, height, block_hash)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_onchain_snapshots_case_chain_height "
                "ON onchain_block_snapshots(case_id, chain, height DESC, stored_at DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_onchain_snapshots_retention "
                "ON onchain_block_snapshots(stored_at)"
            )

    def purge_expired(self, *, now: datetime | None = None) -> int:
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None or current.utcoffset() is None:
            raise ValueError("now must include a timezone")
        cutoff = (current.astimezone(timezone.utc) - timedelta(days=self.retention_days)).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM onchain_block_snapshots WHERE stored_at < ?",
                (cutoff,),
            )
            return cursor.rowcount

    def store_block(self, case_id: str, block: OnChainBlock) -> dict[str, int | str | bool]:
        payload = json.dumps(
            block.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        payload_bytes = len(payload.encode("utf-8"))
        if payload_bytes > MAX_BLOCK_BYTES:
            raise OnChainStoreCapacityError("Normalized block exceeds the 32 MiB storage limit")
        stored_at = datetime.now(timezone.utc).isoformat()
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        ).isoformat()

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "DELETE FROM onchain_block_snapshots WHERE stored_at < ?",
                (cutoff,),
            )
            existing = connection.execute(
                """
                SELECT snapshot_id FROM onchain_block_snapshots
                WHERE case_id = ? AND chain = ? AND height = ? AND block_hash = ?
                """,
                (case_id, block.chain.value, block.height, block.block_hash),
            ).fetchone()
            if existing is not None:
                return {
                    "enabled": True,
                    "snapshot_id": existing["snapshot_id"],
                    "inserted": False,
                    "reorg_fork_preserved": self._has_fork(
                        connection, case_id, block.chain, block.height
                    ),
                }
            count = connection.execute(
                "SELECT COUNT(*) AS snapshot_count FROM onchain_block_snapshots WHERE case_id = ?",
                (case_id,),
            ).fetchone()["snapshot_count"]
            if count >= MAX_SNAPSHOTS_PER_CASE:
                raise OnChainStoreCapacityError(
                    "Case snapshot limit reached; expire or archive existing snapshots before adding more"
                )
            snapshot_id = str(uuid.uuid4())
            connection.execute(
                """
                INSERT INTO onchain_block_snapshots (
                    snapshot_id, case_id, chain, height, block_hash, parent_hash,
                    block_timestamp, source, fetched_at, stored_at, payload_json, payload_bytes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    case_id,
                    block.chain.value,
                    block.height,
                    block.block_hash,
                    block.parent_hash,
                    block.timestamp.astimezone(timezone.utc).isoformat(),
                    block.source,
                    block.fetched_at.astimezone(timezone.utc).isoformat(),
                    stored_at,
                    payload,
                    payload_bytes,
                ),
            )
            return {
                "enabled": True,
                "snapshot_id": snapshot_id,
                "inserted": True,
                "reorg_fork_preserved": self._has_fork(
                    connection, case_id, block.chain, block.height
                ),
            }

    @staticmethod
    def _has_fork(
        connection: sqlite3.Connection,
        case_id: str,
        chain: ChainName,
        height: int,
    ) -> bool:
        count = connection.execute(
            """
            SELECT COUNT(*) AS block_count FROM onchain_block_snapshots
            WHERE case_id = ? AND chain = ? AND height = ?
            """,
            (case_id, chain.value, height),
        ).fetchone()["block_count"]
        return count > 1

    def get_block(
        self,
        case_id: str,
        chain: ChainName,
        height: int,
        block_hash: str,
    ) -> OnChainBlock | None:
        self.purge_expired()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json FROM onchain_block_snapshots
                WHERE case_id = ? AND chain = ? AND height = ? AND block_hash = ?
                """,
                (case_id, chain.value, height, block_hash),
            ).fetchone()
        if row is None:
            return None
        return OnChainBlock.model_validate_json(row["payload_json"])

    def list_snapshots(
        self,
        case_id: str,
        *,
        chain: ChainName | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, int | list[dict[str, str | int | None]]]:
        if not 1 <= limit <= 500 or not 0 <= offset <= MAX_SNAPSHOTS_PER_CASE:
            raise ValueError("Snapshot pagination is outside the supported bounds")
        self.purge_expired()
        where = "case_id = ?"
        parameters: list[str | int] = [case_id]
        if chain is not None:
            where += " AND chain = ?"
            parameters.append(chain.value)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT snapshot_id, chain, height, block_hash, parent_hash,
                       source, block_timestamp, fetched_at, stored_at, payload_bytes
                FROM onchain_block_snapshots
                WHERE {where}
                ORDER BY height DESC, chain, stored_at DESC, snapshot_id
                LIMIT ? OFFSET ?
                """,
                [*parameters, limit + 1, offset],
            ).fetchall()
        has_more = len(rows) > limit
        snapshots = [
            {
                "snapshot_id": row["snapshot_id"],
                "chain": row["chain"],
                "height": row["height"],
                "block_hash": row["block_hash"],
                "parent_hash": row["parent_hash"],
                "source": row["source"],
                "block_timestamp": row["block_timestamp"],
                "fetched_at": row["fetched_at"],
                "stored_at": row["stored_at"],
                "payload_bytes": row["payload_bytes"],
            }
            for row in rows[:limit]
        ]
        return {
            "snapshots": snapshots,
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
            "next_offset": offset + limit if has_more else None,
        }
