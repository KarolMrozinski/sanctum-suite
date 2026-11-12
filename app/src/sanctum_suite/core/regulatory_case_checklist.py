"""Case-scoped AML/MiCA review tracking without automated compliance claims."""

from __future__ import annotations

import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


Applicability = Literal[
    "not_assessed",
    "in_scope",
    "out_of_scope",
    "needs_legal_review",
]
ReviewState = Literal["not_assessed", "evidence_recorded", "needs_review"]
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
MAX_EVIDENCE_PER_CONTROL = 100


class RegulatoryControl(BaseModel):
    model_config = ConfigDict(frozen=True)

    control_id: str
    framework: str
    title: str
    review_prompt: str
    official_reference: str
    source_url: str


CONTROLS: tuple[RegulatoryControl, ...] = (
    RegulatoryControl(
        control_id="EU-MICA-PERIMETER",
        framework="MiCA",
        title="CASP authorization and service perimeter",
        review_prompt=(
            "Record the services, entities, jurisdictions, authorization status, "
            "and qualified legal review used to determine the MiCA perimeter."
        ),
        official_reference="Regulation (EU) 2023/1114",
        source_url="https://eur-lex.europa.eu/eli/reg/2023/1114/oj",
    ),
    RegulatoryControl(
        control_id="EU-MICA-SERVICE-CONTROLS",
        framework="MiCA",
        title="Service-specific governance and client safeguards",
        review_prompt=(
            "Map controls and evidence to each authorized crypto-asset service; "
            "record the applicability rationale and gaps for human review."
        ),
        official_reference="Regulation (EU) 2023/1114",
        source_url="https://eur-lex.europa.eu/eli/reg/2023/1114/oj",
    ),
    RegulatoryControl(
        control_id="EU-TFR-TRANSFER-INFO",
        framework="EU Transfer of Funds Regulation",
        title="Transfer information and exception handling",
        review_prompt=(
            "Review the CASP's procedures for required transfer-party information, "
            "missing or incomplete information, and relevant self-hosted address cases."
        ),
        official_reference="Regulation (EU) 2023/1113",
        source_url="https://eur-lex.europa.eu/eli/reg/2023/1113/oj",
    ),
    RegulatoryControl(
        control_id="EU-AMLR-APPLICABILITY",
        framework="EU AMLR",
        title="AMLR applicability and transition planning",
        review_prompt=(
            "Have qualified reviewers determine the entity's scope, applicable "
            "obligations, transition dates, and implementation owners."
        ),
        official_reference="Regulation (EU) 2024/1624",
        source_url="https://eur-lex.europa.eu/eli/reg/2024/1624/oj",
    ),
    RegulatoryControl(
        control_id="PL-AML-SCOPE",
        framework="Polish AML Act",
        title="Polish AML/CFT scope and current national requirements",
        review_prompt=(
            "Record qualified review of the current consolidated Polish AML Act, "
            "entity scope, competent authority, and relevant national guidance."
        ),
        official_reference="Polish Act of 1 March 2018 on counteracting money laundering and terrorist financing, as amended",
        source_url="https://isap.sejm.gov.pl/isap.nsf/DocDetails.xsp?id=WDU20180000723",
    ),
    RegulatoryControl(
        control_id="EU-AML-CASE-REVIEW",
        framework="AML/CFT case review",
        title="Human review of transaction-monitoring evidence",
        review_prompt=(
            "Record the analyst's review of source provenance, customer context, "
            "applicable internal escalation criteria, and any required independent decision."
        ),
        official_reference=(
            "Review against the entity's approved AML/CFT program and applicable EU/national law"
        ),
        source_url="https://eur-lex.europa.eu/eli/reg/2024/1624/oj",
    ),
)
CONTROL_BY_ID = {control.control_id: control for control in CONTROLS}


class RegulatoryCaseChecklistStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(Path(db_path).expanduser())
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
                CREATE TABLE IF NOT EXISTS regulatory_case_controls (
                    case_id TEXT NOT NULL REFERENCES incident_cases(case_id) ON DELETE CASCADE,
                    control_id TEXT NOT NULL,
                    applicability TEXT NOT NULL CHECK (
                        applicability IN (
                            'not_assessed', 'in_scope', 'out_of_scope', 'needs_legal_review'
                        )
                    ),
                    review_state TEXT NOT NULL CHECK (
                        review_state IN ('not_assessed', 'evidence_recorded', 'needs_review')
                    ),
                    summary TEXT NOT NULL,
                    updated_by TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (case_id, control_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS regulatory_case_evidence (
                    evidence_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    control_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    reference TEXT NOT NULL,
                    sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
                    recorded_by TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    FOREIGN KEY (case_id, control_id)
                        REFERENCES regulatory_case_controls(case_id, control_id)
                        ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_regulatory_case_evidence "
                "ON regulatory_case_evidence(case_id, control_id, recorded_at, evidence_id)"
            )

    @staticmethod
    def _ensure_controls(connection: sqlite3.Connection, case_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        connection.executemany(
            """
            INSERT OR IGNORE INTO regulatory_case_controls (
                case_id, control_id, applicability, review_state, summary, updated_by, updated_at
            ) VALUES (?, ?, 'not_assessed', 'not_assessed', '', '', ?)
            """,
            [(case_id, control.control_id, now) for control in CONTROLS],
        )

    def get_checklist(self, case_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            self._ensure_controls(connection, case_id)
            controls = connection.execute(
                """
                SELECT * FROM regulatory_case_controls
                WHERE case_id = ?
                ORDER BY control_id
                """,
                (case_id,),
            ).fetchall()
            evidence = connection.execute(
                """
                SELECT evidence_id, control_id, source, reference, sha256,
                       recorded_by, recorded_at
                FROM regulatory_case_evidence
                WHERE case_id = ?
                ORDER BY recorded_at, evidence_id
                """,
                (case_id,),
            ).fetchall()

        evidence_by_control: dict[str, list[dict[str, Any]]] = {}
        for row in evidence:
            evidence_by_control.setdefault(row["control_id"], []).append(dict(row))
        checklist = []
        for row in controls:
            definition = CONTROL_BY_ID[row["control_id"]]
            checklist.append(
                {
                    **definition.model_dump(),
                    "applicability": row["applicability"],
                    "review_state": row["review_state"],
                    "summary": row["summary"],
                    "updated_by": row["updated_by"] or None,
                    "updated_at": row["updated_at"],
                    "evidence": evidence_by_control.get(row["control_id"], []),
                }
            )
        return {
            "case_id": case_id,
            "profile": "EU_CASP",
            "profile_version": "1.0.0",
            "overall_status": "NOT_ASSESSED",
            "controls": checklist,
            "limitations": [
                "This is an evidence and review tracker, not legal advice or an automated compliance assessment.",
                "Every control starts not assessed; in-scope/out-of-scope and evidence states are operator-entered review metadata.",
                "Evidence files are not uploaded; references and caller-supplied SHA-256 digests do not prove authenticity or sufficiency.",
                "Applicability, current law, deadlines, control effectiveness, reporting duties, and any SAR/STR decision require qualified human review.",
                "The checklist is a starter profile, not a complete transcription of MiCA, EU AMLR, TFR, or Polish law.",
            ],
        }

    def update_control(
        self,
        case_id: str,
        control_id: str,
        *,
        updated_by: str,
        applicability: Applicability | None = None,
        review_state: ReviewState | None = None,
        summary: str | None = None,
    ) -> dict[str, Any]:
        if control_id not in CONTROL_BY_ID:
            raise ValueError(f"Unknown regulatory control: {control_id}")
        if applicability is None and review_state is None and summary is None:
            raise ValueError("At least one control review field must be provided")
        if not updated_by.strip() or len(updated_by) > 200:
            raise ValueError("updated_by must contain between 1 and 200 characters")
        if summary is not None and (not summary.strip() or len(summary) > 4_000):
            raise ValueError("summary must contain between 1 and 4000 characters")
        if applicability == "out_of_scope" and summary is None:
            raise ValueError("Out-of-scope controls require a recorded rationale")

        with self._connect() as connection:
            self._ensure_controls(connection, case_id)
            current = connection.execute(
                """
                SELECT applicability, review_state, summary FROM regulatory_case_controls
                WHERE case_id = ? AND control_id = ?
                """,
                (case_id, control_id),
            ).fetchone()
            evidence_count = connection.execute(
                """
                SELECT COUNT(*) AS evidence_count FROM regulatory_case_evidence
                WHERE case_id = ? AND control_id = ?
                """,
                (case_id, control_id),
            ).fetchone()["evidence_count"]
            next_state = review_state or current["review_state"]
            if next_state == "evidence_recorded" and evidence_count == 0:
                raise ValueError("evidence_recorded requires at least one evidence reference")
            if next_state == "not_assessed" and evidence_count > 0:
                raise ValueError("A control with retained evidence cannot be reset to not_assessed")
            connection.execute(
                """
                UPDATE regulatory_case_controls
                SET applicability = ?, review_state = ?, summary = ?,
                    updated_by = ?, updated_at = ?
                WHERE case_id = ? AND control_id = ?
                """,
                (
                    applicability or current["applicability"],
                    next_state,
                    summary if summary is not None else current["summary"],
                    updated_by,
                    datetime.now(timezone.utc).isoformat(),
                    case_id,
                    control_id,
                ),
            )
        return self.get_checklist(case_id)

    def add_evidence(
        self,
        case_id: str,
        control_id: str,
        *,
        source: str,
        reference: str,
        sha256: str,
        recorded_by: str,
    ) -> dict[str, Any]:
        if control_id not in CONTROL_BY_ID:
            raise ValueError(f"Unknown regulatory control: {control_id}")
        if not source.strip() or len(source) > 100:
            raise ValueError("Evidence source must contain between 1 and 100 characters")
        if not reference.strip() or len(reference) > 2_048:
            raise ValueError("Evidence reference must contain between 1 and 2048 characters")
        if not _SHA256.fullmatch(sha256):
            raise ValueError("Evidence sha256 must be a lowercase 64-character hex digest")
        if not recorded_by.strip() or len(recorded_by) > 200:
            raise ValueError("recorded_by must contain between 1 and 200 characters")

        with self._connect() as connection:
            self._ensure_controls(connection, case_id)
            count = connection.execute(
                """
                SELECT COUNT(*) AS evidence_count FROM regulatory_case_evidence
                WHERE case_id = ? AND control_id = ?
                """,
                (case_id, control_id),
            ).fetchone()["evidence_count"]
            if count >= MAX_EVIDENCE_PER_CONTROL:
                raise ValueError("The evidence reference limit for this control has been reached")
            connection.execute(
                """
                INSERT INTO regulatory_case_evidence (
                    evidence_id, case_id, control_id, source, reference, sha256,
                    recorded_by, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    case_id,
                    control_id,
                    source.strip(),
                    reference.strip(),
                    sha256,
                    recorded_by,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            connection.execute(
                """
                UPDATE regulatory_case_controls
                SET review_state = CASE
                        WHEN review_state = 'needs_review' THEN review_state
                        ELSE 'evidence_recorded'
                    END,
                    updated_by = ?,
                    updated_at = ?
                WHERE case_id = ? AND control_id = ?
                """,
                (
                    recorded_by,
                    datetime.now(timezone.utc).isoformat(),
                    case_id,
                    control_id,
                ),
            )
        return self.get_checklist(case_id)
