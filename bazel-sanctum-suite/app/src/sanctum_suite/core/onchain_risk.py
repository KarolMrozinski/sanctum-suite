"""Normalized import and case-scoped storage for external on-chain risk reports."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Callable
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from sanctum_suite.core.onchain import ChainName


RiskProvider = Literal["chainalysis", "elliptic", "trm_labs", "arkham", "other"]
ProviderRiskRating = Literal["low", "medium", "high", "severe", "unknown"]
_CATEGORY = re.compile(r"^[A-Za-z][A-Za-z0-9._:-]{0,63}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_MAX_ASSESSMENTS_PER_GRAPH = 5_000


def _normalize_address(chain: ChainName, address: str) -> str:
    if chain is ChainName.ETHEREUM and address.startswith("0x"):
        return address.lower()
    if chain is ChainName.BITCOIN and address.lower().startswith("bc1"):
        return address.lower()
    return address


class OnChainRiskImportRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chain: ChainName
    address: str = Field(min_length=1, max_length=128)
    provider: RiskProvider
    provider_rating: ProviderRiskRating
    category: str = Field(min_length=1, max_length=64)
    report_reference: str = Field(min_length=1, max_length=256)
    assessed_at: AwareDatetime

    @field_validator("address")
    @classmethod
    def validate_address_shape(cls, value: str, info) -> str:
        chain = info.data.get("chain")
        is_valid = False
        if chain is ChainName.ETHEREUM:
            is_valid = re.fullmatch(r"0x[0-9a-fA-F]{40}", value) is not None
        elif chain is ChainName.BITCOIN:
            if value.lower().startswith("bc1"):
                is_valid = re.fullmatch(
                    r"bc1[ac-hj-np-z02-9]{11,71}", value, flags=re.IGNORECASE
                ) is not None
            else:
                is_valid = re.fullmatch(
                    r"[13mn2][1-9A-HJ-NP-Za-km-z]{25,62}", value
                ) is not None
        if not is_valid:
            raise ValueError("address does not match a supported Bitcoin or EVM address shape")
        return _normalize_address(chain, value) if isinstance(chain, ChainName) else value

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        if not _CATEGORY.fullmatch(value):
            raise ValueError("category must be a structured identifier")
        return value

    @field_validator("report_reference")
    @classmethod
    def validate_report_reference(cls, value: str) -> str:
        if not value.strip() or any(ord(character) < 32 for character in value):
            raise ValueError("report_reference must be a non-empty printable identifier")
        return value


class OnChainRiskImportFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"]
    records: list[OnChainRiskImportRecord] = Field(min_length=1, max_length=1_000)

    @classmethod
    def parse_content(cls, content: str) -> tuple[OnChainRiskImportFile, str]:
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Risk report must contain JSON")
        encoded = content.encode("utf-8")
        if len(encoded) > 1_000_000:
            raise ValueError("Risk report cannot exceed 1 MB")
        try:
            value = json.loads(content)
        except json.JSONDecodeError as error:
            raise ValueError("Risk report contains invalid JSON") from error
        report = cls.model_validate(value)
        return report, hashlib.sha256(encoded).hexdigest()


class OnChainRiskResultTooLarge(ValueError):
    """The number of matching assessments exceeds the interactive graph limit."""


class OnChainRiskStore:
    """Stores provider assertions by case while avoiding plaintext address persistence."""

    def __init__(
        self,
        db_path: str | Path,
        *,
        pseudonymize: Callable[[str, str], str] | None = None,
    ) -> None:
        self.db_path = str(Path(db_path).expanduser())
        self._pseudonymize = pseudonymize
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
                CREATE TABLE IF NOT EXISTS onchain_risk_assessments (
                    assessment_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL REFERENCES incident_cases(case_id) ON DELETE CASCADE,
                    chain TEXT NOT NULL,
                    address_token TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    provider_rating TEXT NOT NULL,
                    category TEXT NOT NULL,
                    report_reference TEXT NOT NULL,
                    report_sha256 TEXT NOT NULL,
                    assessed_at TEXT NOT NULL,
                    imported_at TEXT NOT NULL,
                    UNIQUE(case_id, chain, address_token, provider, report_reference, report_sha256)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_onchain_risk_case_chain_address "
                "ON onchain_risk_assessments(case_id, chain, address_token)"
            )

    def _address_token(self, address: str) -> str:
        if self._pseudonymize is not None:
            token = self._pseudonymize("onchain_address", address)
        else:
            token = hashlib.sha256(address.encode("utf-8")).hexdigest()
        if not isinstance(token, str) or not _SHA256.fullmatch(token):
            raise ValueError("address pseudonymizer must return a lowercase SHA-256 digest")
        return token

    def import_report(
        self,
        case_id: str,
        report: OnChainRiskImportFile,
        *,
        report_sha256: str,
    ) -> dict[str, int | str]:
        if not _SHA256.fullmatch(report_sha256):
            raise ValueError("report_sha256 must be a lowercase 64-character digest")
        now = datetime.now(timezone.utc).isoformat()
        records = [
            {
                "assessment_id": str(uuid.uuid4()),
                "case_id": case_id,
                "chain": record.chain.value,
                "address_token": self._address_token(
                    _normalize_address(record.chain, record.address)
                ),
                "provider": record.provider,
                "provider_rating": record.provider_rating,
                "category": record.category,
                "report_reference": record.report_reference,
                "report_sha256": report_sha256,
                "assessed_at": record.assessed_at.astimezone(timezone.utc).isoformat(),
                "imported_at": now,
                "address": record.address,
            }
            for record in report.records
        ]
        if len({(row["chain"], row["address_token"], row["provider"], row["report_reference"]) for row in records}) != len(records):
            raise ValueError("Risk report contains duplicate provider/address references")

        inserted = 0
        with self._connect() as connection:
            if connection.execute(
                "SELECT 1 FROM incident_cases WHERE case_id = ?", (case_id,)
            ).fetchone() is None:
                return {"case_id": case_id, "inserted_count": 0, "duplicate_count": 0}
            for record in records:
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO onchain_risk_assessments (
                        assessment_id, case_id, chain, address_token, provider,
                        provider_rating, category, report_reference, report_sha256,
                        assessed_at, imported_at
                    ) VALUES (
                        :assessment_id, :case_id, :chain, :address_token, :provider,
                        :provider_rating, :category, :report_reference, :report_sha256,
                        :assessed_at, :imported_at
                    )
                    """,
                    record,
                )
                inserted += cursor.rowcount
        return {
            "case_id": case_id,
            "report_sha256": report_sha256,
            "record_count": len(records),
            "inserted_count": inserted,
            "duplicate_count": len(records) - inserted,
        }

    def list_for_addresses(
        self,
        case_id: str,
        chain: ChainName,
        addresses: list[str],
    ) -> list[dict[str, str]]:
        address_by_token = {
            self._address_token(_normalize_address(chain, address)): address
            for address in dict.fromkeys(addresses)
        }
        if not address_by_token:
            return []
        results: list[dict[str, str]] = []
        tokens = list(address_by_token)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TEMP TABLE IF NOT EXISTS requested_address_tokens (
                    address_token TEXT PRIMARY KEY
                )
                """
            )
            for offset in range(0, len(tokens), 500):
                chunk = tokens[offset : offset + 500]
                connection.execute("DELETE FROM requested_address_tokens")
                connection.executemany(
                    "INSERT INTO requested_address_tokens (address_token) VALUES (?)",
                    [(token,) for token in chunk],
                )
                rows = connection.execute(
                    """
                    SELECT assessment.chain, assessment.address_token,
                           assessment.provider, assessment.provider_rating,
                           assessment.category, assessment.report_reference,
                           assessment.report_sha256, assessment.assessed_at,
                           assessment.imported_at
                    FROM onchain_risk_assessments AS assessment
                    JOIN requested_address_tokens AS requested
                        ON requested.address_token = assessment.address_token
                    WHERE assessment.case_id = ? AND assessment.chain = ?
                    ORDER BY assessment.assessed_at DESC, assessment.provider, assessment.category
                    LIMIT ?
                    """,
                    [
                        case_id,
                        chain.value,
                        _MAX_ASSESSMENTS_PER_GRAPH + 1 - len(results),
                    ],
                ).fetchall()
                results.extend(
                    {
                        "chain": row["chain"],
                        "address": address_by_token[row["address_token"]],
                        "provider": row["provider"],
                        "provider_rating": row["provider_rating"],
                        "category": row["category"],
                        "report_reference": row["report_reference"],
                        "report_sha256": row["report_sha256"],
                        "assessed_at": row["assessed_at"],
                        "imported_at": row["imported_at"],
                        "verification_status": "provider_reported_unverified",
                    }
                    for row in rows
                )
                if len(results) > _MAX_ASSESSMENTS_PER_GRAPH:
                    raise OnChainRiskResultTooLarge(
                        "Matching provider assessments exceed the graph limit; no partial result was returned"
                    )
        return results
