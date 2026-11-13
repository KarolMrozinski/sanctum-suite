"""Versioned security-control catalog and evidence-backed assessments."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable


class AssessmentState(str, Enum):
    VERIFIED = "verified"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"
    NOT_ASSESSED = "not_assessed"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class FrameworkReference:
    framework: str
    version: str
    reference: str
    mapping_type: str


@dataclass(frozen=True)
class Control:
    control_id: str
    title: str
    description: str
    assessment_guidance: str
    references: tuple[FrameworkReference, ...]


@dataclass(frozen=True)
class EvidenceInput:
    source: str
    reference: str
    sha256: str


_CONTROLS: tuple[Control, ...] = (
    Control(
        "APP-VULN-001",
        "Application vulnerability handling",
        "Track, prioritize, remediate, and retest application security findings.",
        "Review a scoped vulnerability register and verify remediation evidence.",
        (
            FrameworkReference("OWASP ASVS", "5.0.0", "Application security verification", "related"),
            FrameworkReference("CWE Top 25", "2025", "Weakness prioritization", "related"),
            FrameworkReference("CIS Controls", "8.1", "Control 7: Continuous Vulnerability Management", "related"),
            FrameworkReference("NIST CSF", "2.0", "ID.RA; PR.PS", "related"),
            FrameworkReference("NIST SP 800-53", "Rev. 5", "RA-5 Vulnerability Monitoring and Scanning", "related"),
            FrameworkReference("NIST SP 800-53", "Rev. 5", "SA-11 Developer Testing and Evaluation", "related"),
            FrameworkReference("NIST SP 800-53", "Rev. 5", "SI-2 Flaw Remediation", "related"),
            FrameworkReference("NIS2", "Directive (EU) 2022/2555", "Article 21(2)(e): security in acquisition, development, and maintenance", "related"),
            FrameworkReference("DORA", "Regulation (EU) 2022/2554", "Article 24: digital operational resilience testing", "related"),
        ),
    ),
    Control(
        "APP-ACCESS-001",
        "Identity and access management",
        "Use managed identities, least privilege, and reviewable access decisions.",
        "Inspect access policy, representative role assignments, and access review evidence.",
        (
            FrameworkReference("OWASP ASVS", "5.0.0", "Authentication and access control", "related"),
            FrameworkReference("CIS Controls", "8.1", "Control 6: Access Control Management", "related"),
            FrameworkReference("NIST CSF", "2.0", "PR.AA", "related"),
            FrameworkReference("NIST SP 800-53", "Rev. 5", "AC-2 Account Management; AC-3 Access Enforcement; IA-2 Identification and Authentication", "related"),
            FrameworkReference("NIS2", "Directive (EU) 2022/2555", "Article 21(2)(i)-(j): human-resources, access-control, and authentication policies", "related"),
            FrameworkReference("DORA", "Regulation (EU) 2022/2554", "Article 9: protection and prevention", "related"),
        ),
    ),
    Control(
        "APP-CONFIG-001",
        "Secure configuration management",
        "Define and maintain secure configurations for application and infrastructure assets.",
        "Compare sampled deployed settings against an approved baseline and record deviations.",
        (
            FrameworkReference("OWASP ASVS", "5.0.0", "Configuration and secure architecture", "related"),
            FrameworkReference("CIS Controls", "8.1", "Control 4: Secure Configuration of Enterprise Assets and Software", "related"),
            FrameworkReference("NIST CSF", "2.0", "PR.PS", "related"),
            FrameworkReference("NIST SP 800-53", "Rev. 5", "CM-2 Baseline Configuration; CM-6 Configuration Settings", "related"),
            FrameworkReference("NIS2", "Directive (EU) 2022/2555", "Article 21(2)(e)-(f): secure maintenance and effectiveness assessment", "related"),
            FrameworkReference("DORA", "Regulation (EU) 2022/2554", "Article 9: protection and prevention", "related"),
        ),
    ),
    Control(
        "APP-LOG-001",
        "Security event logging and monitoring",
        "Record security-relevant events and review whether configured monitoring detects them.",
        "Use authorized, non-destructive test events and retain the matching source and alert evidence.",
        (
            FrameworkReference("OWASP ASVS", "5.0.0", "Logging and error handling", "related"),
            FrameworkReference("CIS Controls", "8.1", "Control 8: Audit Log Management", "related"),
            FrameworkReference("NIST CSF", "2.0", "DE.CM", "related"),
            FrameworkReference("NIST SP 800-53", "Rev. 5", "AU-2 Event Logging; AU-9 Protection of Audit Information; AU-11 Audit Record Retention", "related"),
            FrameworkReference("NIS2", "Directive (EU) 2022/2555", "Article 21(2)(b): incident handling", "related"),
            FrameworkReference("DORA", "Regulation (EU) 2022/2554", "Article 10: detection", "related"),
        ),
    ),
    Control(
        "APP-INCIDENT-001",
        "Incident response readiness",
        "Maintain assigned response roles, escalation paths, and tested response procedures.",
        "Review the approved response procedure and a dated exercise record.",
        (
            FrameworkReference("CIS Controls", "8.1", "Control 17: Incident Response Management", "related"),
            FrameworkReference("NIST CSF", "2.0", "RS.MA; RS.CO", "related"),
            FrameworkReference("NIST SP 800-53", "Rev. 5", "IR-4 Incident Handling; IR-6 Incident Reporting", "related"),
            FrameworkReference("NIS2", "Directive (EU) 2022/2555", "Articles 21(2)(b) and 23: incident handling and reporting", "related"),
            FrameworkReference("DORA", "Regulation (EU) 2022/2554", "Articles 17 and 19: incident management and reporting", "related"),
        ),
    ),
    Control(
        "AI-GOV-001",
        "AI system risk governance",
        "Maintain an inventory, documented risk ownership, and lifecycle review for AI systems.",
        "Review system inventory, assigned owners, risk assessments, and lifecycle review evidence.",
        (
            FrameworkReference("ISO/IEC 42001", "2023", "Clauses 4-10: AI management system requirements", "related"),
            FrameworkReference("ISO/IEC 42001", "2023", "Annex A: AI management system control objectives", "related"),
            FrameworkReference("NIST AI RMF", "1.0", "Govern; Map; Measure; Manage", "related"),
            FrameworkReference("NIST CSF", "2.0", "GV.RM; GV.OV", "related"),
        ),
    ),
    Control(
        "APP-SDLC-001",
        "Secure software development and verification",
        "Apply documented secure development, code review, automated security testing, and remediation before release.",
        "Review approved development standards and representative, reproducible SAST, DAST, fuzz, review, and remediation evidence.",
        (
            FrameworkReference("NIST SP 800-53", "Rev. 5", "SA-3 System Development Life Cycle; SA-11 Developer Testing and Evaluation", "related"),
            FrameworkReference("NIS2", "Directive (EU) 2022/2555", "Article 21(2)(e): security in acquisition, development, and maintenance", "related"),
            FrameworkReference("DORA", "Regulation (EU) 2022/2554", "Article 24: digital operational resilience testing", "related"),
        ),
    ),
    Control(
        "APP-SUPPLY-001",
        "ICT supply-chain risk management",
        "Identify, assess, and monitor security risks from software, service providers, and technology dependencies.",
        "Review the scoped dependency and supplier inventory, risk decisions, SBOMs, and remediation or exception records.",
        (
            FrameworkReference("NIST SP 800-53", "Rev. 5", "SR-3 Supply Chain Controls and Processes; SR-5 Acquisition Strategies, Tools, and Methods", "related"),
            FrameworkReference("NIS2", "Directive (EU) 2022/2555", "Article 21(2)(d): supply-chain security", "related"),
            FrameworkReference("DORA", "Regulation (EU) 2022/2554", "Articles 28 and 29: ICT third-party risk and critical ICT third-party providers", "related"),
        ),
    ),
    Control(
        "APP-RESILIENCE-001",
        "Continuity, backup, and recovery",
        "Maintain tested recovery capabilities, protected backups, and assigned continuity responsibilities.",
        "Review approved recovery objectives, backup protection, and dated restoration exercise evidence.",
        (
            FrameworkReference("NIST SP 800-53", "Rev. 5", "CP-2 Contingency Plan; CP-9 System Backup; CP-10 System Recovery and Reconstitution", "related"),
            FrameworkReference("NIS2", "Directive (EU) 2022/2555", "Article 21(2)(c): business continuity, backup management, and disaster recovery", "related"),
            FrameworkReference("DORA", "Regulation (EU) 2022/2554", "Articles 11 and 12: response, recovery, backup, and restoration", "related"),
        ),
    ),
    Control(
        "APP-CRYPTO-001",
        "Cryptographic protection and key management",
        "Use approved cryptographic mechanisms and controlled lifecycle management for cryptographic keys.",
        "Review cryptographic policies, key ownership and rotation, and evidence of approved implementation and recovery.",
        (
            FrameworkReference("NIST SP 800-53", "Rev. 5", "SC-12 Cryptographic Key Establishment and Management; SC-13 Cryptographic Protection", "related"),
            FrameworkReference("NIS2", "Directive (EU) 2022/2555", "Article 21(2)(h): policies and procedures regarding cryptography and encryption", "related"),
            FrameworkReference("DORA", "Regulation (EU) 2022/2554", "Article 9: protection and prevention", "related"),
        ),
    ),
)

_CONTROL_BY_ID = {control.control_id: control for control in _CONTROLS}
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
CATALOG_VERSION = "1.1.0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def control_to_dict(control: Control) -> dict[str, Any]:
    return {
        "control_id": control.control_id,
        "title": control.title,
        "description": control.description,
        "assessment_guidance": control.assessment_guidance,
        "references": [asdict(reference) for reference in control.references],
    }


class ControlCatalog:
    """SQLite-backed assessment store; evidence content is never stored."""

    def __init__(self, db_path: str | Path = "sanctum_controls.db") -> None:
        self.db_path = str(db_path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        Path(self.db_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS control_assessments (
                    assessment_id TEXT PRIMARY KEY,
                    control_id TEXT NOT NULL,
                    catalog_version TEXT NOT NULL DEFAULT '1.1.0',
                    state TEXT NOT NULL CHECK (
                        state IN ('verified', 'failed', 'needs_review', 'not_assessed', 'not_applicable')
                    ),
                    summary TEXT NOT NULL,
                    assessed_by TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            assessment_columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(control_assessments)"
                ).fetchall()
            }
            if "catalog_version" not in assessment_columns:
                connection.execute(
                    "ALTER TABLE control_assessments ADD COLUMN "
                    "catalog_version TEXT NOT NULL DEFAULT '1.0.0'"
                )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS control_evidence (
                    evidence_id TEXT PRIMARY KEY,
                    assessment_id TEXT NOT NULL REFERENCES control_assessments(assessment_id) ON DELETE CASCADE,
                    source TEXT NOT NULL,
                    reference TEXT NOT NULL,
                    sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_assessments_control_created "
                "ON control_assessments(control_id, created_at DESC)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS control_catalog_mappings (
                    mapping_id TEXT PRIMARY KEY,
                    catalog_version TEXT NOT NULL,
                    control_id TEXT NOT NULL,
                    framework TEXT NOT NULL,
                    framework_version TEXT NOT NULL,
                    source_reference TEXT NOT NULL,
                    mapping_type TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    UNIQUE (
                        catalog_version, control_id, framework,
                        framework_version, source_reference, mapping_type
                    )
                )
                """
            )
            self._record_catalog_mappings(connection)

    @staticmethod
    def _record_catalog_mappings(connection: sqlite3.Connection) -> None:
        recorded_at = _utc_now()
        for control in _CONTROLS:
            for reference in control.references:
                stable_identity = "\x1f".join(
                    (
                        CATALOG_VERSION,
                        control.control_id,
                        reference.framework,
                        reference.version,
                        reference.reference,
                        reference.mapping_type,
                    )
                )
                mapping_id = hashlib.sha256(
                    stable_identity.encode("utf-8")
                ).hexdigest()
                connection.execute(
                    """
                    INSERT OR IGNORE INTO control_catalog_mappings (
                        mapping_id, catalog_version, control_id, framework,
                        framework_version, source_reference, mapping_type, recorded_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        mapping_id,
                        CATALOG_VERSION,
                        control.control_id,
                        reference.framework,
                        reference.version,
                        reference.reference,
                        reference.mapping_type,
                        recorded_at,
                    ),
                )

    @staticmethod
    def list_controls(framework: str | None = None) -> list[dict[str, Any]]:
        controls: Iterable[Control] = _CONTROLS
        if framework:
            normalized = framework.casefold()
            controls = (
                control
                for control in _CONTROLS
                if any(ref.framework.casefold() == normalized for ref in control.references)
            )
        return [control_to_dict(control) for control in controls]

    @staticmethod
    def get_control(control_id: str) -> Control | None:
        return _CONTROL_BY_ID.get(control_id)

    def create_assessment(
        self,
        control_id: str,
        state: AssessmentState,
        summary: str,
        assessed_by: str,
        evidence: list[EvidenceInput],
    ) -> dict[str, Any]:
        if control_id not in _CONTROL_BY_ID:
            raise ValueError(f"Unknown control: {control_id}")
        if not summary.strip() or len(summary) > 4_000:
            raise ValueError("summary must contain between 1 and 4000 characters")
        if not assessed_by.strip() or len(assessed_by) > 200:
            raise ValueError("assessed_by must contain between 1 and 200 characters")
        if state == AssessmentState.VERIFIED and not evidence:
            raise ValueError("A verified assessment requires at least one evidence reference")
        if state == AssessmentState.NOT_ASSESSED and evidence:
            raise ValueError("An unassessed control cannot include assessment evidence")
        for item in evidence:
            if not item.source.strip() or len(item.source) > 100:
                raise ValueError("Evidence source must contain between 1 and 100 characters")
            if not item.reference.strip() or len(item.reference) > 2_048:
                raise ValueError("Evidence reference must contain between 1 and 2048 characters")
            if not _SHA256_PATTERN.fullmatch(item.sha256):
                raise ValueError("Evidence sha256 must be a lowercase 64-character hex digest")

        assessment_id = str(uuid.uuid4())
        created_at = _utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO control_assessments
                    (assessment_id, control_id, catalog_version, state, summary, assessed_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    assessment_id,
                    control_id,
                    CATALOG_VERSION,
                    state.value,
                    summary,
                    assessed_by,
                    created_at,
                ),
            )
            for item in evidence:
                connection.execute(
                    """
                    INSERT INTO control_evidence
                        (evidence_id, assessment_id, source, reference, sha256, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        assessment_id,
                        item.source,
                        item.reference,
                        item.sha256,
                        created_at,
                    ),
                )
        assessment = self.get_assessment(assessment_id)
        if assessment is None:
            raise RuntimeError("Assessment was saved but could not be read back")
        return assessment

    def list_mapping_history(
        self,
        *,
        framework: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        if not 1 <= limit <= 2_000:
            raise ValueError("limit must be between 1 and 2000")
        with self._connect() as connection:
            if framework:
                rows = connection.execute(
                    """
                    SELECT * FROM control_catalog_mappings
                    WHERE framework = ? COLLATE NOCASE
                    ORDER BY catalog_version DESC, framework_version, control_id,
                        mapping_id
                    LIMIT ?
                    """,
                    (framework.strip(), limit),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM control_catalog_mappings
                    ORDER BY catalog_version DESC, framework, framework_version,
                        control_id, mapping_id
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        return [dict(row) for row in rows]

    def get_coverage_report(
        self,
        *,
        framework: str | None = None,
    ) -> dict[str, Any]:
        mappings = self.list_mapping_history(framework=framework, limit=2_000)
        mappings = [
            mapping
            for mapping in mappings
            if mapping["catalog_version"] == CATALOG_VERSION
        ]
        if framework and not mappings:
            raise ValueError(f"Unknown framework mapping: {framework}")

        latest_assessments: dict[str, dict[str, Any] | None] = {}
        rows: list[dict[str, Any]] = []
        for mapping in mappings:
            control_id = mapping["control_id"]
            if control_id not in latest_assessments:
                assessments = self.list_assessments(control_id, limit=1)
                latest_assessments[control_id] = assessments[0] if assessments else None
            assessment = latest_assessments[control_id]
            rows.append(
                {
                    **mapping,
                    "control_title": _CONTROL_BY_ID[control_id].title,
                    "assessment_state": (
                        assessment["state"] if assessment else "not_assessed"
                    ),
                    "assessment_id": (
                        assessment["assessment_id"] if assessment else None
                    ),
                    "assessed_at": assessment["created_at"] if assessment else None,
                    "assessed_by": assessment["assessed_by"] if assessment else None,
                    "evidence_reference_count": (
                        len(assessment["evidence"]) if assessment else 0
                    ),
                    "assessment_catalog_version": (
                        assessment["catalog_version"] if assessment else None
                    ),
                    "mapping_interpretation": "RELATED_NOT_EQUIVALENT",
                }
            )
        state_counts = {
            state.value: sum(row["assessment_state"] == state.value for row in rows)
            for state in AssessmentState
        }
        state_counts["not_assessed"] = sum(
            row["assessment_state"] == "not_assessed" for row in rows
        )
        return {
            "catalog_version": CATALOG_VERSION,
            "framework_filter": framework,
            "mapping_count": len(rows),
            "state_counts": state_counts,
            "mappings": rows,
            "certification_status": "NOT_ASSESSED",
            "limitations": [
                "Mappings are scoped discovery relationships, not equivalence to official requirements.",
                "Control assessments are operator-entered and apply at control level, not independently to each mapped publication clause.",
                "An assessment state of verified records an operator assertion with evidence references; it is not proof of compliance or certification.",
                "The report does not determine legal applicability or independently inspect systems or evidence.",
            ],
        }

    def get_assessment(self, assessment_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM control_assessments WHERE assessment_id = ?",
                (assessment_id,),
            ).fetchone()
            if row is None:
                return None
            evidence = connection.execute(
                """
                SELECT evidence_id, source, reference, sha256, created_at
                FROM control_evidence WHERE assessment_id = ? ORDER BY created_at, evidence_id
                """,
                (assessment_id,),
            ).fetchall()
        result = dict(row)
        result["evidence"] = [dict(item) for item in evidence]
        return result

    def list_assessments(self, control_id: str, limit: int = 50) -> list[dict[str, Any]]:
        if control_id not in _CONTROL_BY_ID:
            raise ValueError(f"Unknown control: {control_id}")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT assessment_id FROM control_assessments
                WHERE control_id = ? ORDER BY created_at DESC LIMIT ?
                """,
                (control_id, limit),
            ).fetchall()
        return [
            assessment
            for row in rows
            if (assessment := self.get_assessment(row["assessment_id"])) is not None
        ]

    @staticmethod
    def evidence_digest(content: bytes) -> str:
        """Return a SHA-256 digest for caller-side evidence integrity checks."""
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def export_assessment(assessment: dict[str, Any]) -> str:
        """Serialize a stable, content-only-free JSON assessment record."""
        return json.dumps(assessment, sort_keys=True, separators=(",", ":"))
