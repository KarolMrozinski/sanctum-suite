from fastapi import FastAPI, Request, WebSocket, Security, HTTPException, status, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import AwareDatetime, BaseModel, Field, ValidationError, field_validator
from typing import Dict, Any, List, Literal
from fastapi import Response
import hashlib
import hmac
import json
import os
import re
from pathlib import Path
from datetime import timezone
from pydantic import ConfigDict
from starlette.concurrency import run_in_threadpool

from sanctum_suite.orchestrator.engine import SanctumUnifiedOrchestrator
from sanctum_suite.core.analytics import AnalyticsStoreEngine
from sanctum_suite.core.sigma_yara import DetectionRuleGenerator
from sanctum_suite.core.anomaly import MLAnomalyDetector
from sanctum_suite.core.control_catalog import (
    AssessmentState,
    ControlCatalog,
    EvidenceInput,
)
from sanctum_suite.core.incident_cases import IncidentCaseStore
from sanctum_suite.core.incident_governance import IncidentGovernanceStore
from sanctum_suite.core.incident_playbooks import IncidentPlaybookStore
from sanctum_suite.core.synthetic_incident_lab import SyntheticIncidentLab
from sanctum_suite.core.telemetry_adapters import TelemetryAdapterRegistry
from sanctum_suite.core.telemetry_store import (
    TelemetryEventStore,
    validate_source_id,
)
from sanctum_suite.core.xdr_correlator import RealtimeXdrMeshCorrelator
from sanctum_suite.core.methodology_catalog import list_methodology_references
from sanctum_suite.core.target_authorization import TargetAuthorizationError, require_authorized_target
from sanctum_suite.core.billing import CommercialLicenseManager

app = FastAPI(
    title="SANCTUM-SUITE API",
    description="API for audit workflows, analytics, prompt inspection, and detection rules.",
    version="6.0.0",
)


@app.exception_handler(RequestValidationError)
async def sanitized_request_validation_error(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    if not request.url.path.startswith("/api/v1/telemetry"):
        return await request_validation_exception_handler(request, error)
    return JSONResponse(
        status_code=422,
        content={
            "detail": [
                {
                    "loc": item["loc"],
                    "msg": item["msg"],
                    "type": item["type"],
                }
                for item in error.errors()
            ]
        },
    )


cors_origins = [
    origin.strip()
    for origin in os.environ.get("SANCTUM_CORS_ORIGINS", "").split(",")
    if origin.strip()
]
if "*" in cors_origins:
    raise ValueError("SANCTUM_CORS_ORIGINS must contain explicit origins, not wildcards")
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["X-API-Key", "Content-Type"],
    )

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_CORRELATION_TOKEN_PATTERN = r"^[0-9a-f]{64}$"


def get_telemetry_event_store() -> TelemetryEventStore:
    global telemetry_event_store
    if telemetry_event_store is None:
        telemetry_event_store = TelemetryEventStore(
            get_incident_case_store().db_path
        )
    return telemetry_event_store


def configured_event_source_keys() -> Dict[str, str]:
    serialized = os.environ.get("SANCTUM_EVENT_SOURCE_KEYS", "").strip()
    if not serialized:
        return {}
    try:
        configured = json.loads(serialized)
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SANCTUM_EVENT_SOURCE_KEYS must contain a JSON object",
        ) from error
    if not isinstance(configured, dict) or not configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SANCTUM_EVENT_SOURCE_KEYS must be a non-empty JSON object",
        )
    normalized: Dict[str, str] = {}
    try:
        for source_id, source_key in configured.items():
            validate_source_id(source_id)
            if not isinstance(source_key, str) or len(source_key.encode("utf-8")) < 32:
                raise ValueError("each source key must contain at least 32 bytes")
            normalized[source_id] = source_key
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SANCTUM_EVENT_SOURCE_KEYS contains an invalid source or key",
        ) from error
    return normalized


def require_event_retention(source_keys: Dict[str, str]) -> int:
    if not source_keys:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No event source is configured",
        )
    retention_days = configured_retention_days("SANCTUM_EVENT_RETENTION_DAYS")
    if retention_days is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Configure SANCTUM_EVENT_RETENTION_DAYS before enabling telemetry ingestion",
        )
    return retention_days


def get_incident_governance_store() -> IncidentGovernanceStore:
    global incident_governance_store
    if incident_governance_store is None:
        incident_governance_store = IncidentGovernanceStore(
            get_incident_case_store().db_path
        )
    return incident_governance_store


def configured_retention_days(environment_name: str) -> int | None:
    configured_value = os.environ.get(environment_name)
    if configured_value is None or not configured_value.strip():
        return None
    try:
        days = int(configured_value)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{environment_name} must be an integer between 1 and 36500",
        ) from error
    if not 1 <= days <= 36_500:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{environment_name} must be between 1 and 36500 days",
        )
    return days


def apply_configured_incident_retention() -> Dict[str, int]:
    try:
        deleted = get_incident_governance_store().apply_retention(
            case_retention_days=configured_retention_days(
                "SANCTUM_CASE_RETENTION_DAYS"
            ),
            audit_retention_days=configured_retention_days(
                "SANCTUM_ACCESS_AUDIT_RETENTION_DAYS"
            ),
        )
        telemetry_retention_days = configured_retention_days(
            "SANCTUM_EVENT_RETENTION_DAYS"
        )
        deleted["telemetry_events_deleted"] = (
            get_telemetry_event_store().delete_expired_events(
                retention_days=telemetry_retention_days
            )
            if telemetry_retention_days is not None
            else 0
        )
        return deleted
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Incident retention configuration is invalid",
        ) from error


async def verify_api_key(
    request: Request,
    api_key: str = Security(api_key_header),
):
    expected_key = os.environ.get("SANCTUM_API_KEY", "")
    if len(expected_key.encode("utf-8")) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is not configured",
        )
    if not api_key or not hmac.compare_digest(
        api_key.encode("utf-8"), expected_key.encode("utf-8")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header",
        )
    request.state.credential_fingerprint = hashlib.sha256(
        api_key.encode("utf-8")
    ).hexdigest()[:16]
    if request.url.path.startswith(
        (
            "/api/v1/cases",
            "/api/v1/playbooks",
            "/api/v1/governance",
            "/api/v1/events/correlate",
            "/api/v1/telemetry",
        )
    ) and request.url.path != "/api/v1/governance/retention/purge":
        apply_configured_incident_retention()
    return api_key


async def verify_event_source(
    request: Request,
    source_id: str = Header(alias="X-Sanctum-Source-ID"),
    source_key: str = Header(alias="X-Sanctum-Source-Key"),
) -> str:
    source_keys = configured_event_source_keys()
    retention_days = require_event_retention(source_keys)
    try:
        validate_source_id(source_id)
    except ValueError as error:
        raise HTTPException(status_code=401, detail="Invalid event source credentials") from error
    expected_key = source_keys.get(source_id)
    if expected_key is None or not hmac.compare_digest(
        source_key.encode("utf-8"), expected_key.encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Invalid event source credentials")
    request.state.credential_fingerprint = hashlib.sha256(
        source_key.encode("utf-8")
    ).hexdigest()[:16]
    request.state.telemetry_source_id = source_id
    try:
        get_telemetry_event_store().delete_expired_events(
            retention_days=retention_days
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Event retention configuration is invalid",
        ) from error
    return source_id


@app.middleware("http")
async def audit_incident_api_access(request: Request, call_next):
    response = await call_next(request)
    credential_fingerprint = getattr(
        request.state, "credential_fingerprint", None
    )
    route = request.scope.get("route")
    action = getattr(route, "path", request.url.path)
    is_audited_route = action.startswith(
        (
            "/api/v1/cases",
            "/api/v1/playbooks",
            "/api/v1/governance",
            "/api/v1/events/correlate",
            "/api/v1/lab",
            "/api/v1/telemetry",
        )
    )
    if is_audited_route:
        source_id = getattr(request.state, "telemetry_source_id", None)
        if source_id is not None:
            action = f"{action} source={source_id}"
        get_incident_governance_store().record_access(
            credential_fingerprint=credential_fingerprint,
            action=f"{request.method} {action}",
            outcome_code=response.status_code,
        )
    return response


orchestrator = SanctumUnifiedOrchestrator()
analytics = AnalyticsStoreEngine()
rules_gen = DetectionRuleGenerator()
anomaly_detector = MLAnomalyDetector()
control_catalog: ControlCatalog | None = None
incident_case_store: IncidentCaseStore | None = None
incident_governance_store: IncidentGovernanceStore | None = None
incident_playbook_store: IncidentPlaybookStore | None = None
telemetry_event_store: TelemetryEventStore | None = None
xdr_correlator = RealtimeXdrMeshCorrelator()
synthetic_incident_lab = SyntheticIncidentLab(xdr_correlator)
telemetry_adapter_registry = TelemetryAdapterRegistry()
license_manager = CommercialLicenseManager()
audits_total = 0


def get_control_catalog() -> ControlCatalog:
    global control_catalog
    if control_catalog is None:
        default_controls_db = Path.home() / ".sanctum-suite" / "controls.sqlite3"
        control_catalog = ControlCatalog(
            os.environ.get("SANCTUM_CONTROLS_DB", str(default_controls_db))
        )
    return control_catalog


def get_incident_case_store() -> IncidentCaseStore:
    global incident_case_store
    if incident_case_store is None:
        default_cases_db = Path.home() / ".sanctum-suite" / "cases.sqlite3"
        incident_case_store = IncidentCaseStore(
            os.environ.get("SANCTUM_CASES_DB", str(default_cases_db))
        )
    return incident_case_store


def get_incident_playbook_store() -> IncidentPlaybookStore:
    global incident_playbook_store
    if incident_playbook_store is None:
        case_store = get_incident_case_store()
        incident_playbook_store = IncidentPlaybookStore(case_store.db_path)
    return incident_playbook_store


def consume_entitlement_usage(metric: str) -> None:
    entitlement = license_manager.validate_license_key(
        os.environ.get("SANCTUM_LICENSE_KEY")
    )
    license_manager.check_and_increment_usage(
        entitlement["tenant_id"],
        entitlement,
        metric,
    )


class AuditRequest(BaseModel):
    target_domain: str = Field(min_length=1, max_length=253)
    authorization_reference: str = Field(min_length=1, max_length=500)

class PromptInspectRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=32_768)

class EvidenceRequest(BaseModel):
    source: str = Field(min_length=1, max_length=100)
    reference: str = Field(min_length=1, max_length=2_048)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

class ControlAssessmentRequest(BaseModel):
    state: AssessmentState
    summary: str = Field(min_length=1, max_length=4_000)
    assessed_by: str = Field(min_length=1, max_length=200)
    evidence: List[EvidenceRequest] = Field(default_factory=list, max_length=20)

class SecurityEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1, max_length=128)
    event_type: str = Field(min_length=1, max_length=128)
    correlation_key: str = Field(min_length=1, max_length=256)
    source: str | None = Field(default=None, min_length=1, max_length=128)
    observed_at: AwareDatetime | None = None
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"] | None = None

class EventCorrelationRequest(BaseModel):
    events: List[SecurityEvent] = Field(min_length=1, max_length=1_000)

class NormalizedTelemetryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_event_id: str = Field(min_length=1, max_length=256)
    event_type: str = Field(min_length=1, max_length=128)
    observed_at: AwareDatetime
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"] | None = None
    correlation_token: str | None = Field(
        default=None, pattern=_CORRELATION_TOKEN_PATTERN
    )

    @field_validator("source_event_id", "event_type")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value cannot be blank")
        return value

class TelemetryIngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: List[NormalizedTelemetryEvent] = Field(min_length=1, max_length=1_000)

class TelemetryImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1, max_length=64)
    format: Literal["json", "jsonl", "cef"]
    content: str = Field(min_length=1, max_length=4_000_000)

    @field_validator("source_id")
    @classmethod
    def validate_source_name(cls, value: str) -> str:
        return validate_source_id(value)

class CaseTimelineEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1, max_length=128)
    event_type: str = Field(min_length=1, max_length=128)
    source: str | None = Field(default=None, min_length=1, max_length=128)
    observed_at: AwareDatetime | None = None
    reported_severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"] | None = None

class IncidentCaseCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=4_000)
    created_by: str = Field(min_length=1, max_length=200)
    priority: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO", "NOT_ASSESSED"] = "NOT_ASSESSED"
    correlation_id: str | None = Field(default=None, min_length=1, max_length=128)
    priority_reasons: List[str] = Field(default_factory=list, max_length=20)
    timeline: List[CaseTimelineEvent] = Field(default_factory=list, max_length=1_000)
    assigned_to: str | None = Field(default=None, min_length=1, max_length=200)

class IncidentCaseUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["open", "in_progress", "resolved", "closed"] | None = None
    assigned_to: str | None = Field(default=None, min_length=1, max_length=200)

class IncidentCaseNoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    author: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=4_000)

class IncidentCaseEvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1, max_length=100)
    reference: str = Field(min_length=1, max_length=2_048)
    added_by: str = Field(min_length=1, max_length=200)
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

class IncidentPlaybookSimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    simulated_by: str = Field(min_length=1, max_length=200)

class IncidentPlaybookDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "reject"]
    reviewer: str = Field(min_length=1, max_length=200)
    rationale: str = Field(min_length=1, max_length=2_000)

@app.get("/")
async def root() -> Dict[str, str]:
    return {"status": "ONLINE", "system": "SANCTUM-SUITE Enterprise Core"}


@app.post("/api/v1/audit", dependencies=[Security(verify_api_key)])
async def trigger_audit(payload: AuditRequest) -> Dict[str, Any]:
    """Wyzwala pełen audyt odporności cyfrowej (Wymaga nagłówka X-API-Key)."""
    global audits_total
    try:
        target = require_authorized_target(
            payload.target_domain,
            payload.authorization_reference,
        )
    except (TargetAuthorizationError, ValueError) as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    try:
        result = await run_in_threadpool(
            orchestrator.execute_full_resilience_audit,
            target,
            authorization_reference=payload.authorization_reference,
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    audits_total += 1
    return {
        "status": "COMPLETED",
        "audit_id": result["audit_id"],
        "target": result["target"],
        "overall_score": result["overall_score"],
        "risk_level": result["risk_level"],
        "report_html": result["report_path_html"],
        "report_pdf": result["report_path_pdf"],
    }


@app.get("/api/v1/analytics", dependencies=[Security(verify_api_key)])
async def get_analytics(target: str = Query(..., description="Domena docelowa")) -> Dict[str, Any]:
    """Pobiera zbiorcze wskaźniki analityczne z bazy DuckDB (Wymaga nagłówka X-API-Key)."""
    return analytics.get_target_threat_metrics(target)


@app.get("/api/v1/controls", dependencies=[Security(verify_api_key)])
async def list_controls(framework: str | None = Query(default=None, max_length=100)) -> Dict[str, Any]:
    """Lists versioned control definitions without claiming compliance."""
    return {"controls": get_control_catalog().list_controls(framework)}


@app.get("/api/v1/frameworks", dependencies=[Security(verify_api_key)])
async def list_framework_references(
    category: str | None = Query(default=None, max_length=100),
) -> Dict[str, Any]:
    """Lists version-labeled references and their implementation boundaries."""
    return {"frameworks": list_methodology_references(category)}


@app.post("/api/v1/controls/{control_id}/assessments", dependencies=[Security(verify_api_key)])
async def create_control_assessment(
    control_id: str,
    payload: ControlAssessmentRequest,
) -> Dict[str, Any]:
    """Stores an assessment and integrity references, never raw evidence."""
    try:
        return get_control_catalog().create_assessment(
            control_id=control_id,
            state=payload.state,
            summary=payload.summary,
            assessed_by=payload.assessed_by,
            evidence=[
                EvidenceInput(source=item.source, reference=item.reference, sha256=item.sha256)
                for item in payload.evidence
            ],
        )
    except ValueError as error:
        if str(error).startswith("Unknown control:"):
            raise HTTPException(status_code=404, detail=str(error)) from error
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/api/v1/controls/{control_id}/assessments", dependencies=[Security(verify_api_key)])
async def list_control_assessments(
    control_id: str,
    limit: int = Query(default=50, ge=1, le=100),
) -> Dict[str, Any]:
    """Returns the latest evidence-backed assessment records for a control."""
    try:
        return {"assessments": get_control_catalog().list_assessments(control_id, limit)}
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/api/v1/events/correlate", dependencies=[Security(verify_api_key)])
async def correlate_security_events(payload: EventCorrelationRequest) -> Dict[str, Any]:
    """Groups events by exact key and returns a source-qualified, non-diagnostic timeline."""
    return xdr_correlator.ingest_telemetry_stream(
        [event.model_dump() for event in payload.events]
    )


@app.get(
    "/api/v1/telemetry/connectors",
    dependencies=[Security(verify_api_key)],
)
async def list_telemetry_connectors() -> Dict[str, Any]:
    configured_sources = configured_event_source_keys()
    retention_days = configured_retention_days("SANCTUM_EVENT_RETENTION_DAYS")
    return {
        "sources": [
            {
                "source_id": source_id,
                "modes": ["push_api", "file_import"],
                "credentials_configured": True,
            }
            for source_id in sorted(configured_sources)
        ],
        "file_formats": telemetry_adapter_registry.list_file_formats(),
        "pull_adapters": telemetry_adapter_registry.list_pull_sources(),
        "pull_connector_contract_available": True,
        "push_ingestion_enabled": bool(configured_sources) and retention_days is not None,
        "event_retention_days": retention_days,
        "limitations": (
            "No vendor connector or polling scheduler is included. Pull integrations "
            "must implement the adapter contract, be deployed explicitly, and run under "
            "an operator-approved network and credential policy."
        ),
    }


@app.post(
    "/api/v1/telemetry/ingest",
)
async def ingest_source_telemetry(
    payload: TelemetryIngestRequest,
    source_id: str = Security(verify_event_source),
) -> Dict[str, Any]:
    return _telemetry_store_events(
        source_id,
        payload.events,
        ingestion_mode="push_api",
    )


@app.post(
    "/api/v1/telemetry/import",
    dependencies=[Security(verify_api_key)],
)
async def import_telemetry_file(
    payload: TelemetryImportRequest,
) -> Dict[str, Any]:
    source_keys = configured_event_source_keys()
    require_event_retention(source_keys)
    if payload.source_id not in source_keys:
        raise HTTPException(
            status_code=403,
            detail="The import source is not configured",
        )
    events = _parse_import_events(payload)
    return _telemetry_store_events(
        payload.source_id,
        events,
        ingestion_mode=f"file_import:{payload.format}",
    )


@app.get(
    "/api/v1/telemetry/events",
    dependencies=[Security(verify_api_key)],
)
async def list_ingested_telemetry(
    source_id: str | None = Query(default=None, min_length=1, max_length=64),
    limit: int = Query(default=100, ge=1, le=1_000),
) -> Dict[str, Any]:
    if source_id is not None:
        try:
            validate_source_id(source_id)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
    events = get_telemetry_event_store().list_events(source_id=source_id, limit=limit)
    for event in events:
        event.pop("correlation_token_sha256", None)
    return {
        "events": events,
        "retained_event_count": len(events),
        "limitations": (
            "Only normalized allow-listed fields are returned. Raw source event IDs, "
            "raw payloads, and correlation tokens are not exposed."
        ),
    }


@app.post(
    "/api/v1/telemetry/correlate",
    dependencies=[Security(verify_api_key)],
)
async def correlate_ingested_telemetry(
    window_hours: int = Query(default=24, ge=1, le=720),
    limit: int = Query(default=10_000, ge=2, le=10_000),
) -> Dict[str, Any]:
    events = get_telemetry_event_store().find_correlated_events(
        window_hours=window_hours,
        limit=limit,
    )
    correlations = xdr_correlator.ingest_telemetry_stream(
        [
            {
                "event_id": event["event_id"],
                "event_type": event["event_type"],
                "correlation_key": event["correlation_token_sha256"],
                "source": event["source_id"],
                "observed_at": event["observed_at"],
                "severity": event["reported_severity"],
            }
            for event in events
        ]
    )
    return {
        **correlations,
        "window_hours": window_hours,
        "limitations": (
            "Correlation uses exact matches of source-supplied, pseudonymous "
            "correlation tokens. It is not behavioral detection and does not establish "
            "malicious activity."
        ),
    }


def _telemetry_store_events(
    source_id: str,
    events: List[NormalizedTelemetryEvent],
    *,
    ingestion_mode: str,
) -> Dict[str, Any]:
    correlation_window_hours = telemetry_correlation_window_hours()
    serialized_events = [
        {
            "source_event_id": event.source_event_id,
            "event_type": event.event_type,
            "observed_at": (
                event.observed_at.astimezone(timezone.utc)
                .isoformat(timespec="microseconds")
                .replace("+00:00", "Z")
            ),
            "severity": event.severity,
            "correlation_token": event.correlation_token,
        }
        for event in events
    ]
    store = get_telemetry_event_store()
    batch = store.ingest(source_id, serialized_events)
    related_events = store.find_correlated_events(
        window_hours=correlation_window_hours
    )
    correlation_input = [
        {
            "event_id": event["event_id"],
            "event_type": event["event_type"],
            "correlation_key": event["correlation_token_sha256"],
            "source": event["source_id"],
            "observed_at": event["observed_at"],
            "severity": event["reported_severity"],
        }
        for event in related_events
    ]
    correlation_result = xdr_correlator.ingest_telemetry_stream(correlation_input)
    return {
        **batch,
        "ingestion_mode": ingestion_mode,
        "data_classification": "SOURCE_PROVIDED",
        "correlation_window_hours": correlation_window_hours,
        "correlations": correlation_result["correlations"],
        "raw_payload_persisted": False,
        "external_actions_executed": False,
        "limitations": (
            "Only allow-listed normalized metadata is stored. Raw source identifiers "
            "and correlation tokens are hashed, not retained. Correlation is exact "
            "pseudonymous-token grouping within the configured ingestion window and "
            "does not establish malicious activity."
        ),
    }


def telemetry_correlation_window_hours() -> int:
    configured_value = os.environ.get("SANCTUM_EVENT_CORRELATION_WINDOW_HOURS", "24")
    try:
        window_hours = int(configured_value)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SANCTUM_EVENT_CORRELATION_WINDOW_HOURS must be an integer from 1 to 720",
        ) from error
    if not 1 <= window_hours <= 720:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SANCTUM_EVENT_CORRELATION_WINDOW_HOURS must be from 1 to 720",
        )
    return window_hours


def _parse_import_events(payload: TelemetryImportRequest) -> List[NormalizedTelemetryEvent]:
    if len(payload.content.encode("utf-8")) > 4_000_000:
        raise HTTPException(status_code=413, detail="Import content exceeds 4 MB")
    parser = telemetry_adapter_registry.get_file_parser(payload.format)
    if parser is None:
        raise HTTPException(status_code=422, detail="Unsupported telemetry import format")
    try:
        raw_events = parser.parse(payload.content, max_events=1_000)
        return [
            NormalizedTelemetryEvent.model_validate(event)
            for event in raw_events
        ]
    except ValidationError as error:
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "loc": item["loc"],
                    "msg": item["msg"],
                    "type": item["type"],
                }
                for item in error.errors()
            ],
        ) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/v1/cases", status_code=status.HTTP_201_CREATED, dependencies=[Security(verify_api_key)])
async def create_incident_case(payload: IncidentCaseCreateRequest) -> Dict[str, Any]:
    try:
        return get_incident_case_store().create_case(
            title=payload.title,
            summary=payload.summary,
            created_by=payload.created_by,
            priority=payload.priority,
            correlation_id=payload.correlation_id,
            priority_reasons=payload.priority_reasons,
            timeline=[
                {
                    **event.model_dump(exclude={"observed_at"}),
                    "observed_at": (
                        event.observed_at.astimezone(timezone.utc)
                        .isoformat(timespec="microseconds")
                        .replace("+00:00", "Z")
                        if event.observed_at is not None
                        else None
                    ),
                }
                for event in payload.timeline
            ],
            assigned_to=payload.assigned_to,
        )
    except ValueError as error:
        if "already exists" in str(error):
            raise HTTPException(status_code=409, detail=str(error)) from error
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/api/v1/cases", dependencies=[Security(verify_api_key)])
async def list_incident_cases(
    case_status: Literal["open", "in_progress", "resolved", "closed"] | None = Query(
        default=None, alias="status"
    ),
    limit: int = Query(default=50, ge=1, le=100),
) -> Dict[str, Any]:
    return {
        "cases": get_incident_case_store().list_cases(status=case_status, limit=limit)
    }


@app.get("/api/v1/cases/{case_id}", dependencies=[Security(verify_api_key)])
async def get_incident_case(case_id: str) -> Dict[str, Any]:
    case = get_incident_case_store().get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Incident case not found")
    return case


@app.patch("/api/v1/cases/{case_id}", dependencies=[Security(verify_api_key)])
async def update_incident_case(
    case_id: str,
    payload: IncidentCaseUpdateRequest,
) -> Dict[str, Any]:
    if not payload.model_fields_set:
        raise HTTPException(status_code=422, detail="At least one case field must be updated")
    try:
        case = get_incident_case_store().update_case(
            case_id,
            status=payload.status,
            assigned_to=payload.assigned_to,
            update_assignee="assigned_to" in payload.model_fields_set,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if case is None:
        raise HTTPException(status_code=404, detail="Incident case not found")
    return case


@app.post("/api/v1/cases/{case_id}/notes", status_code=status.HTTP_201_CREATED, dependencies=[Security(verify_api_key)])
async def add_incident_case_note(
    case_id: str,
    payload: IncidentCaseNoteRequest,
) -> Dict[str, Any]:
    try:
        case = get_incident_case_store().add_note(
            case_id, author=payload.author, body=payload.body
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if case is None:
        raise HTTPException(status_code=404, detail="Incident case not found")
    return case


@app.post("/api/v1/cases/{case_id}/evidence", status_code=status.HTTP_201_CREATED, dependencies=[Security(verify_api_key)])
async def add_incident_case_evidence(
    case_id: str,
    payload: IncidentCaseEvidenceRequest,
) -> Dict[str, Any]:
    try:
        case = get_incident_case_store().add_evidence(
            case_id,
            source=payload.source,
            reference=payload.reference,
            added_by=payload.added_by,
            sha256=payload.sha256,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if case is None:
        raise HTTPException(status_code=404, detail="Incident case not found")
    return case


@app.post(
    "/api/v1/cases/{case_id}/playbooks/simulate",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Security(verify_api_key)],
)
async def simulate_incident_playbook(
    case_id: str,
    payload: IncidentPlaybookSimulationRequest,
) -> Dict[str, Any]:
    try:
        plan = get_incident_playbook_store().simulate(
            case_id, simulated_by=payload.simulated_by
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if plan is None:
        raise HTTPException(status_code=404, detail="Incident case not found")
    return plan


@app.get(
    "/api/v1/cases/{case_id}/playbooks",
    dependencies=[Security(verify_api_key)],
)
async def list_incident_playbooks(case_id: str) -> Dict[str, Any]:
    plans = get_incident_playbook_store().list_plans(case_id)
    if plans is None:
        raise HTTPException(status_code=404, detail="Incident case not found")
    return {"playbooks": plans}


@app.get(
    "/api/v1/playbooks/{plan_id}",
    dependencies=[Security(verify_api_key)],
)
async def get_incident_playbook(plan_id: str) -> Dict[str, Any]:
    plan = get_incident_playbook_store().get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return plan


@app.post(
    "/api/v1/playbooks/{plan_id}/decisions",
    dependencies=[Security(verify_api_key)],
)
async def decide_incident_playbook(
    plan_id: str,
    payload: IncidentPlaybookDecisionRequest,
) -> Dict[str, Any]:
    try:
        plan = get_incident_playbook_store().record_decision(
            plan_id,
            decision=payload.decision,
            reviewer=payload.reviewer,
            rationale=payload.rationale,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if plan is None:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return plan


@app.get(
    "/api/v1/governance/access-log",
    dependencies=[Security(verify_api_key)],
)
async def list_incident_access_log(
    limit: int = Query(default=100, ge=1, le=500),
) -> Dict[str, Any]:
    return {
        "records": get_incident_governance_store().list_access(limit=limit),
        "limitations": (
            "The fingerprint identifies the shared API credential, not an individual "
            "operator. Request bodies, API keys, client IP addresses, and query strings "
            "are not stored."
        ),
    }


@app.post(
    "/api/v1/governance/retention/purge",
    dependencies=[Security(verify_api_key)],
)
async def apply_incident_retention_policy() -> Dict[str, Any]:
    return {
        "policy": {
            "case_retention_days": configured_retention_days(
                "SANCTUM_CASE_RETENTION_DAYS"
            ),
            "access_audit_retention_days": configured_retention_days(
                "SANCTUM_ACCESS_AUDIT_RETENTION_DAYS"
            ),
            "event_retention_days": configured_retention_days(
                "SANCTUM_EVENT_RETENTION_DAYS"
            ),
        },
        "deleted": apply_configured_incident_retention(),
    }


@app.get(
    "/api/v1/lab/scenarios",
    dependencies=[Security(verify_api_key)],
)
async def list_synthetic_scenarios() -> Dict[str, Any]:
    return {
        "scenarios": synthetic_incident_lab.list_scenarios(),
        "status": "SYNTHETIC_DEMO_ONLY",
    }


@app.post(
    "/api/v1/lab/scenarios/{scenario_id}/run",
    dependencies=[Security(verify_api_key)],
)
async def run_synthetic_scenario(scenario_id: str) -> Dict[str, Any]:
    result = synthetic_incident_lab.run(scenario_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Synthetic scenario not found")
    return result


@app.websocket("/ws/incidents")
async def websocket_incident_stream(websocket: WebSocket) -> None:
    """Rejects the endpoint until a real, authenticated event source is configured."""
    await websocket.accept()
    await websocket.close(code=1013, reason="Incident telemetry is not configured")

@app.post("/api/v1/inspect-prompt", dependencies=[Security(verify_api_key)])
async def inspect_prompt_endpoint(payload: PromptInspectRequest) -> Dict[str, Any]:
    """Skanuje prompt przez Guardrail Proxy oraz Anomaly Detector."""
    await run_in_threadpool(consume_entitlement_usage, "prompts")
    is_blocked, msg, details = orchestrator.guardrail.inspect_prompt(payload.prompt)
    anomaly_res = anomaly_detector.score_prompt_anomaly(payload.prompt)
    
    return {
        "is_blocked": is_blocked,
        "status_message": msg,
        "guardrail_details": details,
        "ml_anomaly_analysis": anomaly_res,
    }


@app.get("/api/v1/detection-rules", dependencies=[Security(verify_api_key)])
async def get_detection_rules(audit_id: str = Query("SNC-0001", description="ID Audytu")) -> Dict[str, str]:
    """Generuje natywne reguły Sigma i YARA dla wskazanego audytu."""
    yara_rule = rules_gen.generate_yara_rule(audit_id)
    sigma_rule = rules_gen.generate_sigma_rule(audit_id, "enterprise-core.com", [{"issue": "PROMPT_INJECTION_RISK"}])
    
    return {
        "audit_id": audit_id,
        "sigma_rule": sigma_rule,
        "yara_rule": yara_rule,
    }

@app.get("/healthz", status_code=200)
async def healthz():
    """Liveness probe dla Kubernetes / Docker Healthcheck."""
    return {"status": "HEALTHY", "service": "sanctum-suite-core"}

@app.get("/readyz", status_code=200)
async def readyz():
    """Readiness probe checks that API authentication is configured."""
    if len(os.environ.get("SANCTUM_API_KEY", "").encode("utf-8")) < 32:
        return Response(
            content='{"status":"NOT_READY","reason":"API authentication is not configured"}',
            status_code=503,
            media_type="application/json",
        )
    return {"status": "READY", "api_auth_configured": True}

@app.get("/metrics")
async def metrics():
    """Endpoint eksportu metryk w formacie Prometheus."""
    metrics_data = (
        "# HELP sanctum_audits_total Audits completed by this API process.\n"
        "# TYPE sanctum_audits_total counter\n"
        f"sanctum_audits_total {audits_total}\n"
    )
    return Response(content=metrics_data, media_type="text/plain")
