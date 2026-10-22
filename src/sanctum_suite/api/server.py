from fastapi import FastAPI, Request, WebSocket, Security, HTTPException, status, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from pydantic import AwareDatetime, BaseModel, Field, ValidationError, field_validator
from typing import Dict, Any, List, Literal
from fastapi import Response
import asyncio
import hashlib
import hmac
import json
import logging
import os
import re
import sqlite3
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from datetime import datetime, timezone
from pydantic import ConfigDict, model_validator
from starlette.concurrency import run_in_threadpool

from sanctum_suite.orchestrator.engine import SanctumUnifiedOrchestrator
from sanctum_suite.core.analytics import AnalyticsStoreEngine
from sanctum_suite.core.sigma_yara import DetectionRuleGenerator
from sanctum_suite.core.anomaly import MLAnomalyDetector
from sanctum_suite.core.control_catalog import (
    AssessmentState,
    CATALOG_VERSION,
    ControlCatalog,
    EvidenceInput,
)
from sanctum_suite.core.incident_cases import IncidentCaseStore
from sanctum_suite.core.onchain import (
    BitcoinCoreClient,
    ChainName,
    EthereumJsonRpcClient,
    OnChainProviderError,
)
from sanctum_suite.core.onchain_graph import OnChainGraphBuilder, OnChainGraphTooLarge
from sanctum_suite.core.onchain_risk import (
    OnChainRiskImportFile,
    OnChainRiskResultTooLarge,
    OnChainRiskStore,
)
from sanctum_suite.core.onchain_store import (
    MAX_SNAPSHOTS_PER_CASE,
    OnChainBlockStore,
    OnChainStoreCapacityError,
)
from sanctum_suite.core.regulatory_case_checklist import (
    Applicability,
    RegulatoryCaseChecklistStore,
    ReviewState,
)
from sanctum_suite.core.incident_governance import IncidentGovernanceStore
from sanctum_suite.core.audit_pseudonymizer import (
    AuditPseudonymizationConfigurationError,
    AuditPseudonymizer,
)
from sanctum_suite.core.immutable_audit import (
    ImmutableAuditConfigurationError,
    ImmutableAuditError,
    MinioImmutableAuditStore,
)
from sanctum_suite.core.kms_vault import KMSConfigurationError, ZeroTrustKMSVault
from sanctum_suite.core.signer import SecurityReportSigner
from sanctum_suite.core.incident_playbooks import IncidentPlaybookStore
from sanctum_suite.core.synthetic_incident_lab import SyntheticIncidentLab
from sanctum_suite.core.telemetry_adapters import TelemetryAdapterRegistry
from sanctum_suite.core.telemetry_store import (
    TelemetryEventStore,
    validate_event_label,
    validate_source_id,
)
from sanctum_suite.core.xdr_correlator import RealtimeXdrMeshCorrelator
from sanctum_suite.core.purple_team import PurpleTeamEmulationCoordinator
from sanctum_suite.core.oidc import (
    AuthenticatedIdentity,
    OIDCAuthenticationError,
    current_identity,
    oidc_configuration,
    oidc_token_verifier,
    tenant_database_path,
)
from sanctum_suite.core.opa_policy import (
    OPAPolicyClient,
    OPAPolicyConfigurationError,
    OPAPolicyUnavailable,
)
from sanctum_suite.core.tpm_attestation import (
    KeylimeVerifierClient,
    TPMAttestationConfigurationError,
    TPMAttestationUnavailable,
)
from sanctum_suite.core.tee_attestation import (
    TEEAttestationConfigurationError,
    TEEAttestationUnavailable,
    TEEClaimsClient,
)
from sanctum_suite.core.methodology_catalog import list_methodology_references
from sanctum_suite.core.target_authorization import TargetAuthorizationError, require_authorized_target
from sanctum_suite.core.technology_stack_catalog import PlatformTechnologyCatalog
from sanctum_suite.core.security_capability_adapters import (
    COMMON_CAPABILITY_EVENT_SCHEMA,
    SecurityCapabilityAdapterRegistry,
    build_capability_event,
)
from sanctum_suite.core.billing import CommercialLicenseManager
from sanctum_suite.core.privacy_credentials import (
    DifferentialPrivacyCredentialIssuer,
    PrivacyBudgetExceeded,
    ed25519_private_key_from_base64,
)

app = FastAPI(
    title="SANCTUM-SUITE API",
    description="API for audit workflows, analytics, prompt inspection, detection rules, and security-capability evidence for controlled environments.",
    version="6.0.0",
    openapi_tags=[
        {
            "name": "security-capabilities",
            "description": "Operator-managed security capability and evidence records for GCP, ELK, Terraform, SELinux, and similar sources.",
        }
    ],
)
_LOGGER = logging.getLogger(__name__)
security_capability_adapter_registry = SecurityCapabilityAdapterRegistry()
onchain_graph_builder = OnChainGraphBuilder()


@app.exception_handler(RequestValidationError)
async def sanitized_request_validation_error(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    if not (
        request.url.path.startswith("/api/v1/telemetry")
        or request.url.path.startswith("/api/v1/privacy/")
        or request.url.path.endswith("/onchain-risk/import")
        or "/aml-mica-checklist" in request.url.path
    ):
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
        allow_headers=["X-API-Key", "Authorization", "Content-Type"],
    )

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)
_CORRELATION_TOKEN_PATTERN = r"^[0-9a-f]{64}$"


def get_telemetry_event_store() -> TelemetryEventStore:
    global telemetry_event_store
    pseudonymize = (
        get_audit_pseudonymizer().pseudonymize
        if production_environment()
        else None
    )
    tenant_path = tenant_database_path("cases")
    if tenant_path is not None:
        if tenant_path not in _tenant_telemetry_stores:
            _tenant_telemetry_stores[tenant_path] = TelemetryEventStore(
                tenant_path,
                pseudonymize=pseudonymize,
            )
        return _tenant_telemetry_stores[tenant_path]
    if telemetry_event_store is None:
        telemetry_event_store = TelemetryEventStore(
            get_incident_case_store().db_path,
            pseudonymize=pseudonymize,
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
    tenant_path = tenant_database_path("cases")
    if tenant_path is not None:
        if tenant_path not in _tenant_governance_stores:
            _tenant_governance_stores[tenant_path] = IncidentGovernanceStore(
                tenant_path
            )
        return _tenant_governance_stores[tenant_path]
    if incident_governance_store is None:
        incident_governance_store = IncidentGovernanceStore(
            get_incident_case_store().db_path
        )
    return incident_governance_store


def immutable_audit_required() -> bool:
    return (
        os.environ.get("SANCTUM_IMMUTABLE_AUDIT_ENABLED", "").strip().lower()
        == "true"
        or production_environment()
    )


def production_environment() -> bool:
    environment = os.environ.get("SANCTUM_ENVIRONMENT", "").strip().lower()
    return (
        environment in {"production", "prod", "air-gapped", "air_gapped"}
    )


def get_immutable_audit_store() -> MinioImmutableAuditStore:
    global immutable_audit_store
    if immutable_audit_store is None:
        immutable_audit_store = MinioImmutableAuditStore()
    return immutable_audit_store


def get_report_signer() -> SecurityReportSigner:
    global security_report_signer
    if security_report_signer is None:
        security_report_signer = SecurityReportSigner()
    return security_report_signer


def get_opa_policy_client(*, required: bool) -> OPAPolicyClient | None:
    return OPAPolicyClient.from_environment(required=required)


def get_tpm_attestation_client(
    *, required: bool
) -> KeylimeVerifierClient | None:
    return KeylimeVerifierClient.from_environment(required=required)


def get_tee_attestation_client(
    *, required: bool
) -> TEEClaimsClient | None:
    return TEEClaimsClient.from_environment(required=required)


def get_audit_pseudonymizer() -> AuditPseudonymizer:
    global audit_pseudonymizer
    if audit_pseudonymizer is None:
        audit_pseudonymizer = AuditPseudonymizer()
    return audit_pseudonymizer


async def record_immutable_audit_start(
    request: Request,
    credential: str | None,
    identity: AuthenticatedIdentity,
) -> None:
    if not immutable_audit_required() or not request.url.path.startswith("/api/v1/"):
        return
    request_id = str(uuid.uuid4())
    credential_fingerprint = (
        hashlib.sha256(credential.encode("utf-8")).hexdigest() if credential else None
    )
    subject_pseudonym = None
    tenant_pseudonym = None
    if production_environment():
        try:
            pseudonymizer = get_audit_pseudonymizer()
            subject_pseudonym = pseudonymizer.pseudonymize(
                "subject", identity.subject
            )
            tenant_pseudonym = pseudonymizer.pseudonymize(
                "tenant", identity.tenant_id
            )
        except AuditPseudonymizationConfigurationError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Audit pseudonymization is unavailable",
                headers={"Retry-After": "5"},
            ) from error
    route = request.scope.get("route")
    try:
        await run_in_threadpool(
            get_immutable_audit_store().write_event,
            {
                "event_id": str(uuid.uuid4()),
                "request_id": request_id,
                "event_type": "request_started",
                "method": request.method,
                "route_group": "/api/v1",
                "route": getattr(route, "path", "/api/v1"),
                "credential_fingerprint": credential_fingerprint,
                "subject_pseudonym": subject_pseudonym,
                "tenant_pseudonym": tenant_pseudonym,
            },
        )
    except (ImmutableAuditConfigurationError, ImmutableAuditError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Immutable audit storage is unavailable",
            headers={"Retry-After": "5"},
        ) from error
    request.state.immutable_audit_request_id = request_id
    request.state.immutable_audit_credential_fingerprint = credential_fingerprint
    request.state.audit_subject_pseudonym = subject_pseudonym
    request.state.audit_tenant_pseudonym = tenant_pseudonym


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
    bearer: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
):
    try:
        configured_oidc = oidc_configuration()
    except OIDCAuthenticationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if production_environment():
        if configured_oidc is None:
            raise HTTPException(
                status_code=503,
                detail="Production requires Keycloak/OIDC issuer and audience configuration",
            )
        legacy_enabled = os.environ.get(
            "SANCTUM_ALLOW_LEGACY_API_KEY", ""
        ).casefold() in {"1", "true", "yes"}
        if legacy_enabled:
            raise HTTPException(
                status_code=503,
                detail="Legacy shared API-key authentication is disabled in production",
            )
    identity: AuthenticatedIdentity
    if bearer is not None and bearer.scheme.casefold() == "bearer":
        if configured_oidc is None:
            raise HTTPException(
                status_code=503,
                detail="Configure OIDC issuer and audience before using bearer tokens",
            )
        try:
            identity = await oidc_token_verifier.authenticate(bearer.credentials)
        except OIDCAuthenticationError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error
    elif configured_oidc is not None:
        legacy_enabled = os.environ.get(
            "SANCTUM_ALLOW_LEGACY_API_KEY", ""
        ).casefold() in {"1", "true", "yes"}
        if not legacy_enabled:
            raise HTTPException(
                status_code=401,
                detail="A valid OIDC bearer token is required",
            )
        identity = _authenticate_legacy_api_key(api_key)
    else:
        identity = _authenticate_legacy_api_key(api_key)

    context_token = current_identity.set(identity)
    request.state.credential_fingerprint = identity.credential_fingerprint
    request.state.identity_subject = identity.subject
    request.state.identity_tenant = identity.tenant_id
    request.state.authentication_method = identity.authentication_method
    request.state.authenticated_identity = identity
    request.state.authorization_engine = "local_rbac"
    request.state.authorization_decision = "error"
    request.state.authorization_policy_version = None
    try:
        await record_immutable_audit_start(
            request,
            bearer.credentials
            if bearer is not None and bearer.scheme.casefold() == "bearer"
            else api_key,
            identity,
        )
        tpm_attested = await _verify_tpm_attestation(request)
        tee_attested = await _verify_tee_attestation(request)
        policy_enabled = await _apply_opa_policy(request, identity)
        request.state.authorization_engine = _authorization_engine(
            tpm_attested=tpm_attested,
            tee_attested=tee_attested,
            policy_enabled=policy_enabled,
        )
        try:
            _authorize_identity(request, identity)
        except HTTPException:
            request.state.authorization_decision = "deny"
            raise
        if policy_enabled:
            request.state.authorization_engine = "opa+rbac"
        request.state.authorization_decision = "allow"
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
        yield identity
    finally:
        current_identity.reset(context_token)


def _authorization_engine(
    *,
    tpm_attested: bool,
    tee_attested: bool,
    policy_enabled: bool,
) -> str:
    factors = []
    if tpm_attested:
        factors.append("keylime")
    if tee_attested:
        factors.append("tee_verifier")
    factors.append("opa+rbac" if policy_enabled else "local_rbac")
    return "+".join(factors)


async def _verify_tpm_attestation(request: Request) -> bool:
    tpm_required = production_environment()
    try:
        client = get_tpm_attestation_client(required=tpm_required)
    except TPMAttestationConfigurationError as error:
        request.state.authorization_engine = "keylime"
        request.state.authorization_decision = "error"
        _LOGGER.warning(
            "TPM measured-boot configuration is invalid (%s)",
            type(error).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TPM measured-boot attestation is not configured",
            headers={"Retry-After": "5"},
        ) from error
    if client is None:
        return False

    request.state.authorization_engine = "keylime"
    try:
        await client.verify_readiness()
    except TPMAttestationUnavailable as error:
        request.state.authorization_decision = "error"
        _LOGGER.warning(
            "TPM measured-boot verification failed (%s)",
            type(error).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TPM measured-boot attestation is unavailable or stale",
            headers={"Retry-After": "5"},
        ) from error
    return True


async def _verify_tee_attestation(request: Request) -> bool:
    tee_required = production_environment()
    try:
        client = get_tee_attestation_client(required=tee_required)
    except TEEAttestationConfigurationError as error:
        request.state.authorization_engine = "tee_verifier"
        request.state.authorization_decision = "error"
        _LOGGER.warning(
            "Confidential-computing configuration is invalid (%s)",
            type(error).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Confidential-computing attestation is not configured",
            headers={"Retry-After": "5"},
        ) from error
    if client is None:
        return False

    request.state.authorization_engine = "tee_verifier"
    try:
        await client.verify_readiness()
    except TEEAttestationUnavailable as error:
        request.state.authorization_decision = "error"
        _LOGGER.warning(
            "Confidential-computing verification failed (%s)",
            type(error).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Confidential-computing attestation is unavailable or stale",
            headers={"Retry-After": "5"},
        ) from error
    return True


def _authenticate_legacy_api_key(api_key: str | None) -> AuthenticatedIdentity:
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
    fingerprint = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]
    return AuthenticatedIdentity(
        subject=f"api-key:{fingerprint}",
        tenant_id="legacy",
        roles=frozenset({"ADMIN"}),
        credential_fingerprint=fingerprint,
        authentication_method="api_key",
    )


def _authorize_identity(request: Request, identity: AuthenticatedIdentity) -> None:
    if identity.authentication_method != "oidc":
        return
    if request.url.path in {"/api/v1/audit", "/api/v1/analytics"}:
        raise HTTPException(
            status_code=403,
            detail=(
                "This legacy audit/analytics surface is not tenant-scoped; "
                "use the isolated case, telemetry, and control workflows"
            ),
        )
    if "ADMIN" in identity.roles or request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    is_auditor_workflow = request.url.path.startswith(
        (
            "/api/v1/controls/",
            "/api/v1/cases",
            "/api/v1/playbooks",
            "/api/v1/governance/retention/purge",
        )
    )
    if "AUDITOR" in identity.roles and is_auditor_workflow:
        return
    raise HTTPException(
        status_code=403,
        detail="The authenticated OIDC role is not authorized for this operation",
    )


async def _apply_opa_policy(
    request: Request,
    identity: AuthenticatedIdentity,
) -> bool:
    policy_required = production_environment()
    try:
        policy_client = get_opa_policy_client(required=policy_required)
    except OPAPolicyConfigurationError as error:
        policy_settings = (
            os.environ.get("SANCTUM_OPA_URL", ""),
            os.environ.get("SANCTUM_OPA_BEARER_TOKEN_FILE", ""),
            os.environ.get("SANCTUM_OPA_CA_CERT", ""),
        )
        policy_configured = policy_required or any(
            value.strip() for value in policy_settings
        )
        request.state.authorization_engine = (
            "opa" if policy_configured else "local_rbac"
        )
        request.state.authorization_decision = "error"
        _LOGGER.warning(
            "OPA policy configuration is invalid (%s)",
            type(error).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authorization policy service is not configured",
            headers={"Retry-After": "5"},
        ) from error
    if policy_client is None:
        request.state.authorization_engine = "local_rbac"
        return False

    request.state.authorization_engine = "opa"
    route = request.scope.get("route")
    route_template = getattr(route, "path", None)
    if not isinstance(route_template, str) or not route_template.startswith(
        "/api/v1/"
    ):
        request.state.authorization_decision = "error"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authorization policy route context is unavailable",
            headers={"Retry-After": "5"},
        )
    try:
        decision = await policy_client.evaluate(
            {
                "identity": {
                    "authentication_method": identity.authentication_method,
                    "tenant_id": identity.tenant_id,
                    "roles": sorted(identity.roles),
                },
                "request": {
                    "method": request.method,
                    "route": route_template,
                },
            }
        )
    except OPAPolicyUnavailable as error:
        request.state.authorization_decision = "error"
        _LOGGER.warning(
            "OPA policy evaluation failed (%s)",
            type(error).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authorization policy service is unavailable",
            headers={"Retry-After": "5"},
        ) from error
    request.state.authorization_policy_version = decision.policy_version
    if not decision.allow:
        request.state.authorization_decision = "deny"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The authorization policy denied this operation",
        )
    return True


def _authenticated_actor_label(requested_label: str) -> str:
    identity = current_identity.get()
    if identity is not None and identity.authentication_method == "oidc":
        return identity.subject
    return requested_label


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
        configured_oidc = oidc_configuration()
    except OIDCAuthenticationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if production_environment() and configured_oidc is None:
        raise HTTPException(
            status_code=503,
            detail="Production requires Keycloak/OIDC issuer and audience configuration",
        )
    tenant_id = "legacy"
    if configured_oidc is not None:
        serialized_tenants = os.environ.get("SANCTUM_EVENT_SOURCE_TENANTS", "").strip()
        try:
            source_tenants = json.loads(serialized_tenants) if serialized_tenants else {}
        except json.JSONDecodeError as error:
            raise HTTPException(
                status_code=503,
                detail="SANCTUM_EVENT_SOURCE_TENANTS must contain a JSON object",
            ) from error
        tenant_id = source_tenants.get(source_id) if isinstance(source_tenants, dict) else None
        if not isinstance(tenant_id, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", tenant_id
        ):
            raise HTTPException(
                status_code=503,
                detail="Map every configured event source to a tenant in SANCTUM_EVENT_SOURCE_TENANTS",
            )
    source_identity = AuthenticatedIdentity(
        subject=f"event-source:{source_id}",
        tenant_id=tenant_id,
        roles=frozenset({"ADMIN"}),
        credential_fingerprint=request.state.credential_fingerprint,
        authentication_method="event_source",
    )
    context_token = current_identity.set(source_identity)
    request.state.identity_subject = source_identity.subject
    request.state.identity_tenant = source_identity.tenant_id
    request.state.authentication_method = source_identity.authentication_method
    request.state.authenticated_identity = source_identity
    request.state.authorization_engine = "local_rbac"
    request.state.authorization_decision = "error"
    request.state.authorization_policy_version = None
    try:
        await record_immutable_audit_start(request, source_key, source_identity)
        tpm_attested = await _verify_tpm_attestation(request)
        tee_attested = await _verify_tee_attestation(request)
        policy_enabled = await _apply_opa_policy(request, source_identity)
        request.state.authorization_engine = _authorization_engine(
            tpm_attested=tpm_attested,
            tee_attested=tee_attested,
            policy_enabled=policy_enabled,
        )
        request.state.authorization_decision = "allow"
        try:
            get_telemetry_event_store().delete_expired_events(
                retention_days=retention_days
            )
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Event retention configuration is invalid",
            ) from error
        yield source_id
    finally:
        current_identity.reset(context_token)


@app.middleware("http")
async def audit_incident_api_access(request: Request, call_next):
    if not request.url.path.startswith("/api/v1/"):
        return await call_next(request)
    route_group = "/api/v1"

    response = await call_next(request)
    route = request.scope.get("route")
    action = getattr(route, "path", route_group)
    source_id = getattr(request.state, "telemetry_source_id", None)
    if source_id is not None:
        action = f"{action} source={source_id}"
    identity = getattr(request.state, "authenticated_identity", None)
    request_id = getattr(request.state, "immutable_audit_request_id", None)
    credential_fingerprint = getattr(
        request.state, "immutable_audit_credential_fingerprint", None
    )
    context_token = current_identity.set(identity) if identity is not None else None
    try:
        if request_id is not None:
            try:
                await run_in_threadpool(
                    get_immutable_audit_store().write_event,
                    {
                        "event_id": str(uuid.uuid4()),
                        "request_id": request_id,
                        "event_type": "request_completed",
                        "method": request.method,
                        "route": getattr(route, "path", route_group),
                        "credential_fingerprint": credential_fingerprint,
                        "subject_pseudonym": getattr(
                            request.state, "audit_subject_pseudonym", None
                        ),
                        "tenant_pseudonym": getattr(
                            request.state, "audit_tenant_pseudonym", None
                        ),
                        "authentication_method": getattr(
                            request.state, "authentication_method", None
                        ),
                        "outcome_code": response.status_code,
                        "authorization_engine": getattr(
                            request.state, "authorization_engine", None
                        ),
                        "authorization_decision": getattr(
                            request.state, "authorization_decision", None
                        ),
                        "authorization_policy_version": getattr(
                            request.state,
                            "authorization_policy_version",
                            None,
                        ),
                    },
                )
            except (ImmutableAuditConfigurationError, ImmutableAuditError) as error:
                _LOGGER.error(
                    "Immutable audit completion write failed (%s)",
                    type(error).__name__,
                )
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "detail": (
                            "Immutable audit completion could not be stored; "
                            "the request outcome may be uncertain"
                        ),
                        "request_id": request_id,
                    },
                    headers={"Retry-After": "5"},
                )
        get_incident_governance_store().record_access(
            credential_fingerprint=getattr(
                request.state, "credential_fingerprint", None
            ),
            subject_id=(
                getattr(request.state, "audit_subject_pseudonym", None)
                if production_environment()
                else getattr(request.state, "identity_subject", None)
            ),
            tenant_id=(
                getattr(request.state, "audit_tenant_pseudonym", None)
                if production_environment()
                else getattr(request.state, "identity_tenant", None)
            ),
            authentication_method=getattr(
                request.state, "authentication_method", None
            ),
            action=f"{request.method} {action}",
            outcome_code=response.status_code,
            authorization_engine=getattr(
                request.state, "authorization_engine", None
            ),
            authorization_decision=getattr(
                request.state, "authorization_decision", None
            ),
            authorization_policy_version=getattr(
                request.state, "authorization_policy_version", None
            ),
        )
    finally:
        if context_token is not None:
            current_identity.reset(context_token)
    return response


orchestrator = SanctumUnifiedOrchestrator()
analytics = AnalyticsStoreEngine()
rules_gen = DetectionRuleGenerator()
anomaly_detector = MLAnomalyDetector()
control_catalog: ControlCatalog | None = None
incident_case_store: IncidentCaseStore | None = None
incident_governance_store: IncidentGovernanceStore | None = None
immutable_audit_store: MinioImmutableAuditStore | None = None
audit_pseudonymizer: AuditPseudonymizer | None = None
security_report_signer: SecurityReportSigner | None = None
incident_playbook_store: IncidentPlaybookStore | None = None
telemetry_event_store: TelemetryEventStore | None = None
onchain_risk_store: OnChainRiskStore | None = None
_tenant_control_catalogs: Dict[str, ControlCatalog] = {}
_tenant_case_stores: Dict[str, IncidentCaseStore] = {}
_tenant_governance_stores: Dict[str, IncidentGovernanceStore] = {}
_tenant_playbook_stores: Dict[str, IncidentPlaybookStore] = {}
_tenant_telemetry_stores: Dict[str, TelemetryEventStore] = {}
_tenant_onchain_risk_stores: Dict[str, OnChainRiskStore] = {}
onchain_block_store: OnChainBlockStore | None = None
_tenant_onchain_block_stores: Dict[str, OnChainBlockStore] = {}
regulatory_case_checklist_store: RegulatoryCaseChecklistStore | None = None
_tenant_regulatory_case_checklist_stores: Dict[str, RegulatoryCaseChecklistStore] = {}
xdr_correlator = RealtimeXdrMeshCorrelator()
purple_team_coordinator = PurpleTeamEmulationCoordinator()
synthetic_incident_lab = SyntheticIncidentLab(xdr_correlator)
telemetry_adapter_registry = TelemetryAdapterRegistry()
license_manager = CommercialLicenseManager()
audits_total = 0


def get_control_catalog() -> ControlCatalog:
    global control_catalog
    tenant_path = tenant_database_path("controls")
    if tenant_path is not None:
        if tenant_path not in _tenant_control_catalogs:
            _tenant_control_catalogs[tenant_path] = ControlCatalog(tenant_path)
        return _tenant_control_catalogs[tenant_path]
    if control_catalog is None:
        default_controls_db = Path.home() / ".sanctum-suite" / "controls.sqlite3"
        control_catalog = ControlCatalog(
            os.environ.get("SANCTUM_CONTROLS_DB", str(default_controls_db))
        )
    return control_catalog


def get_incident_case_store() -> IncidentCaseStore:
    global incident_case_store
    tenant_path = tenant_database_path("cases")
    if tenant_path is not None:
        if tenant_path not in _tenant_case_stores:
            _tenant_case_stores[tenant_path] = IncidentCaseStore(tenant_path)
        return _tenant_case_stores[tenant_path]
    if incident_case_store is None:
        default_cases_db = Path.home() / ".sanctum-suite" / "cases.sqlite3"
        incident_case_store = IncidentCaseStore(
            os.environ.get("SANCTUM_CASES_DB", str(default_cases_db))
        )
    return incident_case_store


def get_regulatory_case_checklist_store() -> RegulatoryCaseChecklistStore:
    global regulatory_case_checklist_store
    case_store = get_incident_case_store()
    tenant_path = tenant_database_path("cases")
    if tenant_path is not None:
        key = str(tenant_path)
        if key not in _tenant_regulatory_case_checklist_stores:
            _tenant_regulatory_case_checklist_stores[key] = RegulatoryCaseChecklistStore(
                tenant_path
            )
        return _tenant_regulatory_case_checklist_stores[key]
    if (
        regulatory_case_checklist_store is None
        or regulatory_case_checklist_store.db_path != case_store.db_path
    ):
        regulatory_case_checklist_store = RegulatoryCaseChecklistStore(
            case_store.db_path
        )
    return regulatory_case_checklist_store


def get_onchain_rpc_client(chain: ChainName) -> BitcoinCoreClient | EthereumJsonRpcClient:
    if chain is ChainName.BITCOIN:
        endpoint = os.environ.get("SANCTUM_BITCOIN_RPC_URL", "").strip()
        username = os.environ.get("SANCTUM_BITCOIN_RPC_USERNAME")
        password = os.environ.get("SANCTUM_BITCOIN_RPC_PASSWORD")
        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Bitcoin Core RPC is not configured",
            )
        try:
            return BitcoinCoreClient(
                endpoint,
                username=username,
                password=password,
            )
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Bitcoin Core RPC configuration is invalid",
            ) from error

    endpoint = os.environ.get("SANCTUM_ETHEREUM_RPC_URL", "").strip()
    if not endpoint:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ethereum JSON-RPC is not configured",
        )
    try:
        return EthereumJsonRpcClient(endpoint)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ethereum JSON-RPC configuration is invalid",
        ) from error


def get_onchain_risk_store() -> OnChainRiskStore:
    global onchain_risk_store
    case_store = get_incident_case_store()
    db_path = str(case_store.db_path)
    pseudonymize = (
        get_audit_pseudonymizer().pseudonymize
        if production_environment()
        else None
    )
    tenant_path = tenant_database_path("cases")
    if tenant_path is not None:
        key = str(tenant_path)
        if key not in _tenant_onchain_risk_stores:
            _tenant_onchain_risk_stores[key] = OnChainRiskStore(
                tenant_path,
                pseudonymize=pseudonymize,
            )
        return _tenant_onchain_risk_stores[key]
    if onchain_risk_store is None or onchain_risk_store.db_path != db_path:
        onchain_risk_store = OnChainRiskStore(
            db_path,
            pseudonymize=pseudonymize,
        )
    return onchain_risk_store


def get_onchain_block_store() -> OnChainBlockStore | None:
    global onchain_block_store
    enabled = os.environ.get("SANCTUM_ONCHAIN_STORAGE_ENABLED", "").strip().lower()
    if enabled not in {"", "true", "false"}:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SANCTUM_ONCHAIN_STORAGE_ENABLED must be true or false",
        )
    if enabled != "true":
        return None
    raw_retention_days = os.environ.get("SANCTUM_ONCHAIN_RETENTION_DAYS", "").strip()
    try:
        retention_days = int(raw_retention_days)
        if not 1 <= retention_days <= 36_500:
            raise ValueError
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Configure SANCTUM_ONCHAIN_RETENTION_DAYS from 1 to 36500 before enabling on-chain storage",
        ) from error

    case_store = get_incident_case_store()
    database_path = str(case_store.db_path)
    tenant_path = tenant_database_path("cases")
    if tenant_path is not None:
        key = str(tenant_path)
        store = _tenant_onchain_block_stores.get(key)
        if store is None or store.retention_days != retention_days:
            store = OnChainBlockStore(tenant_path, retention_days=retention_days)
            _tenant_onchain_block_stores[key] = store
        return store
    if (
        onchain_block_store is None
        or onchain_block_store.db_path != database_path
        or onchain_block_store.retention_days != retention_days
    ):
        onchain_block_store = OnChainBlockStore(
            database_path,
            retention_days=retention_days,
        )
    return onchain_block_store


def get_incident_playbook_store() -> IncidentPlaybookStore:
    global incident_playbook_store
    tenant_path = tenant_database_path("cases")
    if tenant_path is not None:
        if tenant_path not in _tenant_playbook_stores:
            _tenant_playbook_stores[tenant_path] = IncidentPlaybookStore(tenant_path)
        return _tenant_playbook_stores[tenant_path]
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


class SecurityCapabilityEvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: str = Field(
        min_length=1,
        max_length=200,
        description="Target environment label, e.g. edge-domain or prod-tenant",
    )
    environment: str = Field(
        min_length=1,
        max_length=200,
        description="Logical environment name, e.g. gcp, hybrid, or production",
    )
    capability_id: str = Field(
        min_length=1,
        max_length=256,
        description="Stable capability identifier like security-capability:gcp-platform",
    )
    technology: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Human-readable technology name such as Google Cloud Platform (GCP)",
    )
    source_type: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^(artifact_store|asset_inventory|cloud_inventory|data_platform_api|gcp_api|logging_api|model_registry|attestation_api|iac_api|host_policy_api|source_repository|threat_intel_api|soar_api|firmware_api|manifest_store|certificate_service|metadata_feed|mission_api)$",
        description="Normalized evidence source type",
    )
    evidence: Dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-specific evidence values normalized to the common capability schema",
    )
    status: Literal["PLAN_ONLY", "READY", "NOT_CONFIGURED", "ERROR"] = Field(
        default="PLAN_ONLY",
        description="Current evidence status. The default remains PLAN_ONLY in the safe, operator-managed model.",
    )


class SecurityCapabilitySyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: str | None = Field(default=None, min_length=1, max_length=200)
    environment: str | None = Field(default=None, min_length=1, max_length=200)
    force_refresh: bool = Field(default=False, description="Force a fresh sync pass instead of returning cached records when present")


class MissionControlSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: str = Field(min_length=1, max_length=200, description="Mission target or operational domain")
    environment: str = Field(min_length=1, max_length=200, description="Environment label such as production, field, or ops")
    mission_id: str = Field(default="PRISM-US-984XN", min_length=1, max_length=256, description="Operational mission identifier")
    mission_status: str = Field(default="ACTIVE", min_length=1, max_length=128, description="Current mission status")
    operator_scope: str = Field(default="full_scope", min_length=1, max_length=128, description="Authorized operator scope")
    system_attestations: List[str] = Field(
        default_factory=lambda: ["boot_measurement_verified", "identity_scope_verified", "telemetry_context_attached"],
        min_length=1,
        max_length=20,
        description="Attestation values from the mission control layer",
    )
    telemetry_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Real-time telemetry metadata and mission context for the live connection",
    )


class SecurityCapabilityRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    target: str
    environment: str
    capability_id: str
    technology: str | None = None
    source_type: str
    evidence: Dict[str, Any]
    status: Literal["PLAN_ONLY", "READY", "NOT_CONFIGURED", "ERROR"] = "PLAN_ONLY"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SecurityCapabilityEvidenceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    capability_id: str
    target: str
    environment: str
    source_type: str
    evidence: Dict[str, Any]
    status: Literal["PLAN_ONLY", "READY", "NOT_CONFIGURED", "ERROR"] = "PLAN_ONLY"
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SecurityCapabilityEventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability_id: str = Field(min_length=1, max_length=256)
    target: str = Field(min_length=1, max_length=200)
    environment: str = Field(min_length=1, max_length=200)
    source_type: str = Field(min_length=1, max_length=128)
    status: Literal["PLAN_ONLY", "READY", "NOT_CONFIGURED", "ERROR"] = "PLAN_ONLY"
    evidence: Dict[str, Any] = Field(default_factory=dict)
    producer: str = Field(default="sanctum-suite", max_length=128)


class PrivacyCredentialObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_id: str = Field(min_length=1, max_length=128)
    category: str = Field(min_length=1, max_length=64)


class PrivacyCredentialRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$",
    )
    categories: List[str] = Field(min_length=1, max_length=32)
    observations: List[PrivacyCredentialObservation] = Field(max_length=10_000)
    epsilon: float = Field(ge=0.01, le=1, allow_inf_nan=False)


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


class RegulatoryCaseControlUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    updated_by: str = Field(min_length=1, max_length=200)
    applicability: Applicability | None = None
    review_state: ReviewState | None = None
    summary: str | None = Field(default=None, min_length=1, max_length=4_000)

    @model_validator(mode="after")
    def validate_update(self) -> "RegulatoryCaseControlUpdateRequest":
        if self.applicability is None and self.review_state is None and self.summary is None:
            raise ValueError("At least one review field must be provided")
        if self.applicability == "out_of_scope" and self.summary is None:
            raise ValueError("Out-of-scope controls require a recorded rationale")
        return self


class RegulatoryCaseEvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1, max_length=100)
    reference: str = Field(min_length=1, max_length=2_048)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    recorded_by: str = Field(min_length=1, max_length=200)


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
    detection_scenario_id: str | None = Field(default=None, min_length=1, max_length=128)
    detection_rule_id: str | None = Field(default=None, min_length=1, max_length=128)
    correlation_token: str | None = Field(
        default=None, pattern=_CORRELATION_TOKEN_PATTERN
    )

    @field_validator("source_event_id", "event_type")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value cannot be blank")
        return value

    @field_validator("event_type", "detection_scenario_id", "detection_rule_id")
    @classmethod
    def require_structured_labels(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            return validate_event_label(value)
        except ValueError as error:
            raise ValueError(
                "Telemetry labels must be structured identifiers without free text"
            ) from error

    @model_validator(mode="after")
    def require_detection_identifier_pair(self):
        if (self.detection_scenario_id is None) != (self.detection_rule_id is None):
            raise ValueError(
                "detection_scenario_id and detection_rule_id must be provided together"
            )
        if (
            self.detection_scenario_id is not None
            and (
                not self.detection_scenario_id.strip()
                or not self.detection_rule_id
                or not self.detection_rule_id.strip()
            )
        ):
            raise ValueError("detection identifiers cannot be blank")
        return self

class TelemetryIngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: List[NormalizedTelemetryEvent] = Field(min_length=1, max_length=1_000)

class TelemetryPullRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cursor: str | None = Field(default=None, max_length=4_096)
    limit: int = Field(default=100, ge=1, le=1_000)

class TelemetryImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1, max_length=64)
    format: Literal["json", "jsonl", "cef"]
    content: str = Field(min_length=1, max_length=4_000_000)

    @field_validator("source_id")
    @classmethod
    def validate_source_name(cls, value: str) -> str:
        return validate_source_id(value)


class OnChainRiskImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=1_000_000)


class CaseTimelineEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1, max_length=128)
    event_type: str = Field(min_length=1, max_length=128)
    source: str | None = Field(default=None, min_length=1, max_length=128)
    observed_at: AwareDatetime | None = None
    reported_severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"] | None = None
    detection_scenario_id: str | None = Field(default=None, min_length=1, max_length=128)
    detection_rule_id: str | None = Field(default=None, min_length=1, max_length=128)

    @model_validator(mode="after")
    def require_detection_identifier_pair(self):
        if (self.detection_scenario_id is None) != (self.detection_rule_id is None):
            raise ValueError(
                "detection_scenario_id and detection_rule_id must be provided together"
            )
        return self


class PurpleTeamReplayRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(min_length=1, max_length=128)
    expected_rule_id: str = Field(min_length=1, max_length=128)
    evaluated_by: str = Field(min_length=1, max_length=200)

    @field_validator("scenario_id", "expected_rule_id", "evaluated_by")
    @classmethod
    def reject_blank_identifiers(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value cannot be blank")
        return value

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


_security_capability_store: List[SecurityCapabilityRecord] = []
_security_capability_evidence_store: Dict[str, List[SecurityCapabilityEvidenceRecord]] = {}
_security_capability_event_store: List[Dict[str, Any]] = []


def _publish_capability_event(event: Dict[str, Any]) -> Dict[str, Any]:
    _security_capability_event_store.append(event)
    adapter = security_capability_adapter_registry.get("security-capability:kafka-event-bus")
    if adapter is not None and hasattr(adapter, "publish_event"):
        result = adapter.publish_event(event=event)
        return {
            "status": result.get("status", "accepted"),
            "queued": result.get("queued", True),
            "event_id": event.get("event_id"),
            "schema_version": event.get("schema_version", COMMON_CAPABILITY_EVENT_SCHEMA),
            "topic": result.get("topic"),
        }
    return {
        "status": "accepted",
        "queued": True,
        "event_id": event.get("event_id"),
        "schema_version": event.get("schema_version", COMMON_CAPABILITY_EVENT_SCHEMA),
        "topic": None,
    }


def _build_event_from_adapter(
    *,
    capability_id: str,
    target: str,
    environment: str,
    source_type: str,
    evidence: Dict[str, Any],
    status: str,
    producer: str = "sanctum-suite",
) -> Dict[str, Any]:
    event = build_capability_event(
        capability_id=capability_id,
        target=target,
        environment=environment,
        source_type=source_type,
        evidence=evidence,
        status=status,
        producer=producer,
    )
    return event


def _phase_1_runtime_status() -> Dict[str, Any]:
    """Evaluate whether the first operational wave has the required runtime configuration."""
    registry = SecurityCapabilityAdapterRegistry()
    wave_caps = registry.list_supported_by_wave().get("phase_1", [])
    status_by_capability: Dict[str, Any] = {}
    for capability_id in wave_caps:
        try:
            requirements = registry.get_runtime_requirements(capability_id)
        except KeyError:
            continue
        env_names = requirements.get("env", [])
        present = {name: bool(os.environ.get(name, "").strip()) for name in env_names}
        required = [name for name, is_set in present.items() if not is_set]
        status_by_capability[capability_id] = {
            "status": "READY" if not required else "NOT_CONFIGURED",
            "required_env": env_names,
            "present_env": present,
            "missing_env": required,
            "auth": requirements.get("auth", {}),
        }
    ready_count = sum(1 for entry in status_by_capability.values() if entry["status"] == "READY")
    return {
        "wave": "phase_1",
        "overall_status": "READY" if ready_count == len(status_by_capability) and status_by_capability else "NOT_CONFIGURED",
        "ready_count": ready_count,
        "total_count": len(status_by_capability),
        "capabilities": status_by_capability,
    }


@app.get("/api/v1/security-capabilities", dependencies=[Security(verify_api_key)])
async def list_security_capabilities(
    target: str = Query(default="enterprise-environment", description="Target environment label"),
    capability_id: str | None = Query(default=None, description="Optional capability filter"),
    technology: str | None = Query(default=None, description="Optional technology filter"),
    environment: str | None = Query(default=None, description="Optional environment filter"),
) -> Dict[str, Any]:
    """Return the platform technology catalog as a machine-readable capability map."""
    catalog = PlatformTechnologyCatalog().assess_platform_stack(target=target)
    mapped = catalog["security_capability_mapping"]
    if capability_id:
        mapped = [item for item in mapped if item["capability_id"] == capability_id]
    if technology:
        mapped = [item for item in mapped if item["technology"] == technology]
    if environment:
        filtered_records = [
            item for item in _security_capability_store if item.environment == environment
        ]
    else:
        filtered_records = list(_security_capability_store)

    return {
        "target": target,
        "environment": environment or "enterprise-environment",
        "catalog": catalog,
        "items": mapped,
        "stored_records": [record.model_dump(mode="json") for record in filtered_records],
    }


@app.get("/api/v1/security-capabilities/waves", dependencies=[Security(verify_api_key)])
async def list_security_capability_waves() -> Dict[str, Any]:
    """Expose the staged live-ready wave catalog with runtime requirements and env guards."""
    registry = SecurityCapabilityAdapterRegistry()
    catalog = PlatformTechnologyCatalog()
    wave_catalog = registry.list_supported_by_wave()
    runtime_requirements: Dict[str, Dict[str, Any]] = {}
    for capability_ids in wave_catalog.values():
        for capability_id in capability_ids:
            try:
                runtime_requirements[capability_id] = registry.get_runtime_requirements(capability_id)
            except KeyError:
                continue
    first_wave = wave_catalog.get("phase_1", [])
    required_env = sorted({
        env_name
        for requirements in runtime_requirements.values()
        for env_name in requirements.get("env", [])
        if env_name
    })
    return {
        "phase_roadmap": catalog.phase_roadmap(),
        "supported_wave_catalog": wave_catalog,
        "capability_runtime_requirements": runtime_requirements,
        "first_operational_wave": {
            "phase": "phase_1",
            "capabilities": first_wave,
            "required_env": [
                env_name for env_name in required_env if env_name in {
                    env_name for capability_id in first_wave for env_name in runtime_requirements.get(capability_id, {}).get("env", [])
                }
            ],
        },
    }


@app.get("/api/v1/security-capabilities/waves/{wave_name}", dependencies=[Security(verify_api_key)])
async def get_security_capability_wave(wave_name: str) -> Dict[str, Any]:
    """Get the full module inventory and runtime metadata for one implementation wave."""
    registry = SecurityCapabilityAdapterRegistry()
    catalog = PlatformTechnologyCatalog()
    wave_catalog = registry.list_supported_by_wave()
    if wave_name not in wave_catalog:
        raise HTTPException(status_code=404, detail="Wave not found")

    capabilities = []
    for capability_id in wave_catalog[wave_name]:
        runtime_requirements = {}
        try:
            runtime_requirements = registry.get_runtime_requirements(capability_id)
        except KeyError:
            runtime_requirements = {}
        capabilities.append({
            "capability_id": capability_id,
            "adapter_available": registry.get(capability_id) is not None,
            "runtime_requirements": runtime_requirements,
        })

    return {
        "wave_name": wave_name,
        "phase": catalog.phase_roadmap().get(wave_name, {}),
        "capabilities": capabilities,
    }


def _wave_runtime_status(wave_name: str) -> Dict[str, Any]:
    """Compute the readiness status for an implementation wave from env and auth requirements."""
    registry = SecurityCapabilityAdapterRegistry()
    wave_catalog = registry.list_supported_by_wave()
    if wave_name not in wave_catalog:
        raise HTTPException(status_code=404, detail="Wave not found")

    statuses: Dict[str, Any] = {}
    for capability_id in wave_catalog[wave_name]:
        try:
            requirements = registry.get_runtime_requirements(capability_id)
        except KeyError:
            continue
        env_names = requirements.get("env", [])
        alias_groups = requirements.get("env_aliases", [])
        present = {name: bool(os.environ.get(name, "").strip()) for name in env_names}
        satisfied_aliases = {
            name
            for group in alias_groups
            if any(present.get(candidate, False) for candidate in group)
            for name in group
        }
        missing = []
        seen = set()
        for name in env_names:
            if name in satisfied_aliases:
                continue
            if not present.get(name, False):
                if name not in seen:
                    missing.append(name)
                    seen.add(name)
        for group in alias_groups:
            if any(present.get(name, False) for name in group):
                continue
            for name in group:
                if name not in seen:
                    missing.append(name)
                    seen.add(name)
        statuses[capability_id] = {
            "status": "READY" if not missing else "NOT_CONFIGURED",
            "adapter_available": registry.get(capability_id) is not None,
            "required_env": env_names,
            "present_env": present,
            "missing_env": missing,
            "auth": requirements.get("auth", {}),
            "endpoint": requirements.get("endpoint"),
        }

    ready_count = sum(1 for entry in statuses.values() if entry["status"] == "READY")
    return {
        "wave_name": wave_name,
        "overall_status": "READY" if ready_count == len(statuses) and statuses else "NOT_CONFIGURED",
        "ready_count": ready_count,
        "total_count": len(statuses),
        "capabilities": statuses,
    }


@app.get("/api/v1/security-capabilities/waves/{wave_name}/status", dependencies=[Security(verify_api_key)])
async def get_security_capability_wave_status(wave_name: str) -> Dict[str, Any]:
    """Return a practical readiness assessment for the selected live-ready wave."""
    return _wave_runtime_status(wave_name)


@app.get("/api/v1/security-capabilities/{capability_id}", dependencies=[Security(verify_api_key)])
async def get_security_capability(
    capability_id: str,
    target: str = Query(default="enterprise-environment", description="Target environment label"),
) -> Dict[str, Any]:
    """Return the normalized capability record for one security capability."""
    catalog = PlatformTechnologyCatalog().assess_platform_stack(target=target)
    match = next(
        (
            item
            for item in catalog["security_capability_mapping"]
            if item["capability_id"] == capability_id
        ),
        None,
    )
    if match is None:
        raise HTTPException(status_code=404, detail="Capability not found")
    stored = [
        record.model_dump(mode="json")
        for record in _security_capability_store
        if record.capability_id == capability_id and record.target == target
    ]
    return {
        "target": target,
        "capability": match,
        "stored_records": stored,
        "api_contract": catalog["api_contract"],
    }


@app.post("/api/v1/security-capabilities", dependencies=[Security(verify_api_key)])
async def ingest_security_capability(payload: SecurityCapabilityEvidenceRequest) -> Dict[str, Any]:
    """Persist a structured evidence record for a security capability."""
    record = SecurityCapabilityRecord(
        target=payload.target,
        environment=payload.environment,
        capability_id=payload.capability_id,
        technology=payload.technology,
        source_type=payload.source_type,
        evidence=payload.evidence,
        status=payload.status,
    )
    _security_capability_store.append(record)
    event = _build_event_from_adapter(
        capability_id=payload.capability_id,
        target=payload.target,
        environment=payload.environment,
        source_type=payload.source_type,
        evidence=payload.evidence,
        status=payload.status,
    )
    publish = _publish_capability_event(event)
    return {
        "status": "accepted",
        "record": record.model_dump(mode="json"),
        "event": event,
        "publish": publish,
        "api_contract": PlatformTechnologyCatalog().assess_platform_stack(target=payload.target)["api_contract"],
    }


@app.get("/api/v1/security-capabilities/{capability_id}/evidence", dependencies=[Security(verify_api_key)])
async def get_security_capability_evidence(
    capability_id: str,
    target: str = Query(default="enterprise-environment", description="Target environment label"),
    environment: str = Query(default="enterprise-environment", description="Environment name"),
) -> Dict[str, Any]:
    """Return the evidence records for a specific capability, using the adapter registry when available."""
    catalog = PlatformTechnologyCatalog().assess_platform_stack(target=target)
    match = next(
        (
            item
            for item in catalog["security_capability_mapping"]
            if item["capability_id"] == capability_id
        ),
        None,
    )
    if match is None:
        raise HTTPException(status_code=404, detail="Capability not found")

    records = _security_capability_evidence_store.get(capability_id, [])
    filtered = [
        record.model_dump(mode="json")
        for record in records
        if record.target == target and record.environment == environment
    ]

    adapter = security_capability_adapter_registry.get(capability_id)
    if not filtered and adapter is not None:
        evidence = adapter.sync_evidence(target=target, environment=environment)
        filtered = [{
            "id": str(uuid.uuid4()),
            "capability_id": capability_id,
            "target": target,
            "environment": environment,
            "source_type": adapter.source_type,
            "evidence": evidence,
            "status": evidence.get("status", "PLAN_ONLY"),
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }]

    return {
        "capability_id": capability_id,
        "target": target,
        "environment": environment,
        "capability": match,
        "records": filtered,
        "adapter": None if adapter is None else {"name": adapter.name, "source_type": adapter.source_type},
    }


@app.post("/api/v1/security-capabilities/{capability_id}/evidence", dependencies=[Security(verify_api_key)])
async def submit_security_capability_evidence(
    capability_id: str,
    payload: SecurityCapabilityEvidenceRequest,
) -> Dict[str, Any]:
    """Submit evidence for a specific capability and normalize it for later retrieval."""
    if payload.capability_id != capability_id:
        raise HTTPException(status_code=400, detail="Capability id in path and payload must match")

    record = SecurityCapabilityEvidenceRecord(
        capability_id=capability_id,
        target=payload.target,
        environment=payload.environment,
        source_type=payload.source_type,
        evidence=payload.evidence,
        status=payload.status,
    )
    _security_capability_evidence_store.setdefault(capability_id, []).append(record)
    event = _build_event_from_adapter(
        capability_id=capability_id,
        target=payload.target,
        environment=payload.environment,
        source_type=payload.source_type,
        evidence=payload.evidence,
        status=payload.status,
    )
    publish = _publish_capability_event(event)
    return {
        "status": "accepted",
        "record": record.model_dump(mode="json"),
        "event": event,
        "publish": publish,
    }


@app.post("/api/v1/security-capabilities/{capability_id}/sync", dependencies=[Security(verify_api_key)])
async def sync_security_capability(
    capability_id: str,
    payload: SecurityCapabilitySyncRequest | None = None,
    target: str = Query(default="enterprise-environment", description="Target environment label"),
    environment: str = Query(default="enterprise-environment", description="Environment name"),
) -> Dict[str, Any]:
    """Synchronize evidence for a capability using the registry-backed adapter contract."""
    if payload is not None:
        target = payload.target or target
        environment = payload.environment or environment

    catalog = PlatformTechnologyCatalog().assess_platform_stack(target=target)
    match = next(
        (
            item
            for item in catalog["security_capability_mapping"]
            if item["capability_id"] == capability_id
        ),
        None,
    )
    if match is None:
        raise HTTPException(status_code=404, detail="Capability not found")

    adapter = security_capability_adapter_registry.get(capability_id)
    if adapter is None:
        raise HTTPException(status_code=404, detail="No adapter registered for capability")

    evidence = adapter.sync_evidence(target=target, environment=environment)
    record = SecurityCapabilityEvidenceRecord(
        capability_id=capability_id,
        target=target,
        environment=environment,
        source_type=adapter.source_type,
        evidence=evidence,
        status=evidence.get("status", "PLAN_ONLY"),
    )
    _security_capability_evidence_store.setdefault(capability_id, []).append(record)
    event = _build_event_from_adapter(
        capability_id=capability_id,
        target=target,
        environment=environment,
        source_type=adapter.source_type,
        evidence=evidence,
        status=evidence.get("status", "PLAN_ONLY"),
    )
    publish = _publish_capability_event(event)
    return {
        "status": "accepted",
        "capability_id": capability_id,
        "target": target,
        "environment": environment,
        "capability": match,
        "record": record.model_dump(mode="json"),
        "event": event,
        "publish": publish,
        "adapter": {"name": adapter.name, "source_type": adapter.source_type},
    }


@app.get("/api/v1/security-capabilities/{capability_id}/health", dependencies=[Security(verify_api_key)])
async def healthcheck_security_capability(
    capability_id: str,
    target: str = Query(default="enterprise-environment", description="Target environment label"),
    environment: str = Query(default="enterprise-environment", description="Environment name"),
) -> Dict[str, Any]:
    """Return adapter health details for a capability and emit a normalized event snapshot."""
    adapter = security_capability_adapter_registry.get(capability_id)
    if adapter is None:
        raise HTTPException(status_code=404, detail="No adapter registered for capability")

    health = adapter.health_check(target=target, environment=environment)
    event = _build_event_from_adapter(
        capability_id=capability_id,
        target=target,
        environment=environment,
        source_type=adapter.source_type,
        evidence=health.get("details", {}),
        status=health.get("status", "PLAN_ONLY"),
    )
    publish = _publish_capability_event(event)
    return {
        "capability_id": capability_id,
        "target": target,
        "environment": environment,
        "status": health.get("status", "PLAN_ONLY"),
        "healthy": bool(health.get("healthy", False)),
        "adapter": {"name": adapter.name, "source_type": adapter.source_type},
        "health": health,
        "event": event,
        "publish": publish,
        "event_schema": COMMON_CAPABILITY_EVENT_SCHEMA,
    }


@app.get("/api/v1/security-capabilities/events", dependencies=[Security(verify_api_key)])
async def list_security_capability_events(
    capability_id: str | None = Query(default=None, description="Optional capability filter"),
    limit: int = Query(default=20, ge=1, le=200, description="Maximum events to return"),
) -> Dict[str, Any]:
    """Return the normalized capability event stream emitted by the registry and API layer."""
    events = list(_security_capability_event_store)
    if capability_id is not None:
        events = [event for event in events if event.get("capability_id") == capability_id]
    events = events[-limit:]
    return {
        "count": len(events),
        "events": events,
        "event_schema": COMMON_CAPABILITY_EVENT_SCHEMA,
    }


@app.post("/api/v1/security-capabilities/{capability_id}/events", dependencies=[Security(verify_api_key)])
async def publish_security_capability_event(
    capability_id: str,
    payload: SecurityCapabilityEventEnvelope,
) -> Dict[str, Any]:
    """Publish a normalized event to the local registry and Kafka bridge when configured."""
    if payload.capability_id != capability_id:
        raise HTTPException(status_code=400, detail="Capability id in path and payload must match")

    event = _build_event_from_adapter(
        capability_id=payload.capability_id,
        target=payload.target,
        environment=payload.environment,
        source_type=payload.source_type,
        evidence=payload.evidence,
        status=payload.status,
        producer=payload.producer,
    )
    publish = _publish_capability_event(event)
    return {
        "status": "accepted",
        "event": event,
        "publish": publish,
        "event_schema": COMMON_CAPABILITY_EVENT_SCHEMA,
    }


@app.get("/api/v1/mission-control", dependencies=[Security(verify_api_key)])
async def get_mission_control_status(
    target: str = Query(default="enterprise-environment", description="Target environment label"),
    environment: str = Query(default="enterprise-environment", description="Environment name"),
) -> Dict[str, Any]:
    """Return the live mission-control status contract for US-984XN / PRISM integration."""
    adapter = security_capability_adapter_registry.get("security-capability:mission-integration")
    if adapter is None:
        raise HTTPException(status_code=404, detail="Mission control adapter not registered")

    evidence = adapter.fetch_evidence(target=target, environment=environment)
    example_payload = {
        "target": target,
        "environment": environment,
        "mission_id": "PRISM-US-984XN",
        "mission_status": "ACTIVE",
        "operator_scope": "full_scope",
        "system_attestations": [
            "boot_measurement_verified",
            "identity_scope_verified",
            "telemetry_context_attached",
        ],
        "telemetry_context": {
            "source": "mission-control",
            "status": "READY",
            "last_seen": datetime.now(timezone.utc).isoformat(),
            "stream": "ops",
            "operator_scope": "full_scope",
        },
    }
    return {
        "status": "LIVE",
        "capability_id": "security-capability:mission-integration",
        "target": target,
        "environment": environment,
        "payload": evidence,
        "example_payload": example_payload,
        "contract": {
            "method": "POST",
            "route": "/api/v1/mission-control/sync",
            "source_type": "mission_api",
            "required_fields": [
                "target",
                "environment",
                "mission_id",
                "mission_status",
                "operator_scope",
                "system_attestations",
                "telemetry_context",
            ],
        },
    }


@app.post("/api/v1/mission-control/sync", dependencies=[Security(verify_api_key)])
async def sync_mission_control(payload: MissionControlSyncRequest) -> Dict[str, Any]:
    """Accept a live mission-control payload and normalize it for PRISM/US-984XN integration."""
    evidence = {
        "provider": "us-984xn",
        "mission_id": payload.mission_id,
        "mission_status": payload.mission_status,
        "operator_scope": payload.operator_scope,
        "system_attestations": payload.system_attestations,
        "telemetry_context": {
            **payload.telemetry_context,
            "source": payload.telemetry_context.get("source", "mission-control"),
            "status": "READY",
            "operator_scope": payload.operator_scope,
            "target": payload.target,
            "environment": payload.environment,
        },
        "target": payload.target,
        "environment": payload.environment,
        "source_type": "mission_api",
    }
    record = SecurityCapabilityEvidenceRecord(
        capability_id="security-capability:mission-integration",
        target=payload.target,
        environment=payload.environment,
        source_type="mission_api",
        evidence=evidence,
        status="READY",
    )
    _security_capability_evidence_store.setdefault("security-capability:mission-integration", []).append(record)
    return {
        "status": "accepted",
        "capability_id": "security-capability:mission-integration",
        "target": payload.target,
        "environment": payload.environment,
        "record": record.model_dump(mode="json"),
        "example_payload": {
            "target": payload.target,
            "environment": payload.environment,
            "mission_id": payload.mission_id,
            "mission_status": payload.mission_status,
            "operator_scope": payload.operator_scope,
            "system_attestations": payload.system_attestations,
            "telemetry_context": evidence["telemetry_context"],
        },
    }


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


def get_privacy_credential_issuer() -> DifferentialPrivacyCredentialIssuer:
    encoded_key = os.environ.get("SANCTUM_DP_VC_ED25519_PRIVATE_KEY", "").strip()
    if not encoded_key:
        raise ValueError("SANCTUM_DP_VC_ED25519_PRIVATE_KEY is required")
    configured_database = os.environ.get("SANCTUM_PRIVACY_BUDGET_DB", "").strip()
    if production_environment() and not configured_database:
        raise ValueError(
            "SANCTUM_PRIVACY_BUDGET_DB must be configured in production"
        )
    database_path = configured_database or "sanctum_privacy_budget.sqlite3"
    try:
        max_epsilon = float(os.environ.get("SANCTUM_DP_MAX_EPSILON", "3"))
    except ValueError as error:
        raise ValueError("SANCTUM_DP_MAX_EPSILON must be a number") from error
    return DifferentialPrivacyCredentialIssuer(
        database_path=database_path,
        signing_key=ed25519_private_key_from_base64(encoded_key),
        max_epsilon=max_epsilon,
    )


@app.post(
    "/api/v1/privacy/credentials",
    dependencies=[Security(verify_api_key)],
)
async def issue_privacy_credential(
    payload: PrivacyCredentialRequest,
) -> Dict[str, Any]:
    """Issues a subject-level DP histogram as a signed Ed25519 VC-JWT."""
    try:
        issuer = get_privacy_credential_issuer()
    except sqlite3.Error as error:
        _LOGGER.exception("Privacy budget storage initialization failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Privacy budget storage is unavailable",
        ) from error
    except (OSError, ValueError) as error:
        _LOGGER.error("Privacy credential service configuration is invalid: %s", error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Privacy credential signing is not configured",
        ) from error
    try:
        return await run_in_threadpool(
            issuer.issue,
            dataset_id=payload.dataset_id,
            observations=[
                observation.model_dump() for observation in payload.observations
            ],
            categories=payload.categories,
            epsilon=payload.epsilon,
        )
    except PrivacyBudgetExceeded as error:
        raise HTTPException(status_code=429, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except sqlite3.Error as error:
        _LOGGER.exception("Privacy budget storage operation failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Privacy budget storage is unavailable",
        ) from error


@app.get("/api/v1/controls", dependencies=[Security(verify_api_key)])
async def list_controls(framework: str | None = Query(default=None, max_length=100)) -> Dict[str, Any]:
    """Lists versioned control definitions without claiming compliance."""
    return {
        "catalog_version": CATALOG_VERSION,
        "controls": get_control_catalog().list_controls(framework),
    }


@app.get("/api/v1/controls/coverage", dependencies=[Security(verify_api_key)])
async def get_control_coverage_report(
    framework: str | None = Query(default=None, max_length=100),
) -> Dict[str, Any]:
    """Returns a versioned assessment-gap report, not a compliance determination."""
    try:
        report = get_control_catalog().get_coverage_report(framework=framework)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    canonical_report = json.dumps(
        report, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    report["report_sha256"] = hashlib.sha256(
        canonical_report.encode("utf-8")
    ).hexdigest()
    if production_environment():
        try:
            signer = get_report_signer()
            signature = signer.sign_bytes(
                json.dumps(
                    report,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            )
        except (OSError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Compliance report signing is unavailable",
                headers={"Retry-After": "5"},
            ) from error
        report["report_signature"] = {
            "algorithm": "RSA-PSS-SHA256",
            "signer_sha256": signer.public_key_fingerprint,
            "signature_base64": signature,
        }
    return report


@app.get(
    "/api/v1/controls/mappings/history",
    dependencies=[Security(verify_api_key)],
)
async def list_control_mapping_history(
    framework: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=500, ge=1, le=2_000),
) -> Dict[str, Any]:
    """Returns append-only catalog mapping snapshots across internal catalog versions."""
    return {
        "catalog_version": CATALOG_VERSION,
        "mappings": get_control_catalog().list_mapping_history(
            framework=framework, limit=limit
        ),
    }


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
            assessed_by=_authenticated_actor_label(payload.assessed_by),
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
                "modes": [
                    "push_api",
                    "file_import",
                    *(
                        ["pull_api"]
                        if telemetry_adapter_registry.get_pull_adapter(source_id)
                        else []
                    ),
                ],
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
    "/api/v1/telemetry/connectors/{source_id}/pull",
    dependencies=[Security(verify_api_key)],
)
async def pull_telemetry_from_connector(
    source_id: str,
    payload: TelemetryPullRequest,
) -> Dict[str, Any]:
    try:
        validate_source_id(source_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    source_keys = configured_event_source_keys()
    require_event_retention(source_keys)
    if source_id not in source_keys:
        raise HTTPException(
            status_code=403,
            detail="The pull source is not configured",
        )
    adapter = telemetry_adapter_registry.get_pull_adapter(source_id)
    if adapter is None:
        raise HTTPException(status_code=404, detail="No pull adapter is registered for this source")

    try:
        raw_events, next_cursor = await asyncio.wait_for(
            adapter.fetch_events(cursor=payload.cursor, limit=payload.limit),
            timeout=30,
        )
    except TimeoutError as error:
        raise HTTPException(status_code=504, detail="The telemetry source timed out") from error

    if (
        not isinstance(raw_events, Sequence)
        or isinstance(raw_events, (str, bytes, bytearray))
        or len(raw_events) > payload.limit
    ):
        raise HTTPException(
            status_code=502,
            detail="The pull adapter returned an invalid event batch",
        )
    if next_cursor is not None and (
        not isinstance(next_cursor, str) or len(next_cursor) > 4_096
    ):
        raise HTTPException(
            status_code=502,
            detail="The pull adapter returned an invalid cursor",
        )

    try:
        events = [
            NormalizedTelemetryEvent.model_validate(event)
            for event in raw_events
            if isinstance(event, Mapping)
        ]
        if len(events) != len(raw_events):
            raise ValueError("Every pull adapter event must be an object")
    except (ValidationError, ValueError) as error:
        details = (
            [
                {
                    "loc": item["loc"],
                    "msg": item["msg"],
                    "type": item["type"],
                }
                for item in error.errors()
            ]
            if isinstance(error, ValidationError)
            else str(error)
        )
        raise HTTPException(
            status_code=502,
            detail={"message": "The pull adapter returned invalid normalized events", "errors": details},
        ) from error

    ingestion = (
        _telemetry_store_events(source_id, events, ingestion_mode="pull_api")
        if events
        else None
    )
    return {
        "source_id": source_id,
        "pulled_count": len(events),
        "next_cursor": next_cursor,
        "ingestion": ingestion,
        "external_actions_executed": False,
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
                "detection_scenario_id": event["detection_scenario_id"],
                "detection_rule_id": event["detection_rule_id"],
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
            "detection_scenario_id": event.detection_scenario_id,
            "detection_rule_id": event.detection_rule_id,
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
            "detection_scenario_id": event["detection_scenario_id"],
            "detection_rule_id": event["detection_rule_id"],
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
            "and correlation tokens are retained only as keyed, namespace-separated "
            "pseudonyms in production; development uses unkeyed hashes. Structured "
            "labels are metadata and must not contain personal data. Correlation is "
            "exact pseudonymous-token grouping within the configured ingestion window "
            "and does not establish malicious activity."
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
            created_by=_authenticated_actor_label(payload.created_by),
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


@app.get(
    "/api/v1/cases/{case_id}/aml-mica-checklist",
    dependencies=[Security(verify_api_key)],
)
async def get_case_aml_mica_checklist(case_id: str) -> Dict[str, Any]:
    if get_incident_case_store().get_case(case_id) is None:
        raise HTTPException(status_code=404, detail="Incident case not found")
    return get_regulatory_case_checklist_store().get_checklist(case_id)


@app.patch(
    "/api/v1/cases/{case_id}/aml-mica-checklist/{control_id}",
    dependencies=[Security(verify_api_key)],
)
async def update_case_aml_mica_control(
    case_id: str,
    control_id: str,
    payload: RegulatoryCaseControlUpdateRequest,
) -> Dict[str, Any]:
    if get_incident_case_store().get_case(case_id) is None:
        raise HTTPException(status_code=404, detail="Incident case not found")
    try:
        return get_regulatory_case_checklist_store().update_control(
            case_id,
            control_id,
            updated_by=_authenticated_actor_label(payload.updated_by),
            applicability=payload.applicability,
            review_state=payload.review_state,
            summary=payload.summary,
        )
    except ValueError as error:
        if str(error).startswith("Unknown regulatory control:"):
            raise HTTPException(status_code=404, detail=str(error)) from error
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post(
    "/api/v1/cases/{case_id}/aml-mica-checklist/{control_id}/evidence",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Security(verify_api_key)],
)
async def add_case_aml_mica_evidence(
    case_id: str,
    control_id: str,
    payload: RegulatoryCaseEvidenceRequest,
) -> Dict[str, Any]:
    if get_incident_case_store().get_case(case_id) is None:
        raise HTTPException(status_code=404, detail="Incident case not found")
    try:
        return get_regulatory_case_checklist_store().add_evidence(
            case_id,
            control_id,
            source=payload.source,
            reference=payload.reference,
            sha256=payload.sha256,
            recorded_by=_authenticated_actor_label(payload.recorded_by),
        )
    except ValueError as error:
        if str(error).startswith("Unknown regulatory control:"):
            raise HTTPException(status_code=404, detail=str(error)) from error
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get(
    "/api/v1/cases/{case_id}/onchain-graph",
    dependencies=[Security(verify_api_key)],
)
async def get_case_onchain_graph(
    case_id: str,
    chain: ChainName = Query(...),
    height: int = Query(..., ge=0, le=2**64 - 1),
    block_hash: str | None = Query(default=None, min_length=1, max_length=128),
) -> Dict[str, Any]:
    case = get_incident_case_store().get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Incident case not found")
    try:
        store = get_onchain_block_store()
        if block_hash is not None:
            if store is None:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="On-chain snapshot storage is not enabled",
                )
            block = await run_in_threadpool(
                store.get_block,
                case_id,
                chain,
                height,
                block_hash,
            )
            if block is None:
                raise HTTPException(status_code=404, detail="Saved on-chain snapshot not found")
            storage_result: Dict[str, Any] = {
                "enabled": True,
                "snapshot_id": None,
                "inserted": False,
                "reorg_fork_preserved": False,
                "loaded_from_snapshot": True,
            }
        else:
            client = get_onchain_rpc_client(chain)
            block = await client.get_block(height)
            if store is None:
                storage_result = {
                    "enabled": False,
                    "snapshot_id": None,
                    "inserted": False,
                    "reorg_fork_preserved": False,
                    "loaded_from_snapshot": False,
                }
            else:
                storage_result = await run_in_threadpool(
                    store.store_block,
                    case_id,
                    block,
                )
                storage_result["loaded_from_snapshot"] = False
        addresses = [
            address
            for transaction in block.transactions
            for address in [
                *[item.address for item in transaction.inputs],
                *[item.address for item in transaction.outputs],
            ]
            if address is not None
        ]
        assessments = await run_in_threadpool(
            get_onchain_risk_store().list_for_addresses,
            case_id,
            chain,
            addresses,
        )
        graph = onchain_graph_builder.build(
            block,
            case_id=case_id,
            risk_assessments=assessments,
        )
        graph["storage"] = storage_result
        return graph
    except OnChainStoreCapacityError as error:
        raise HTTPException(status_code=413, detail=str(error)) from error
    except OnChainGraphTooLarge as error:
        raise HTTPException(status_code=413, detail=str(error)) from error
    except OnChainRiskResultTooLarge as error:
        raise HTTPException(status_code=413, detail=str(error)) from error
    except HTTPException:
        raise
    except OnChainProviderError as error:
        _LOGGER.warning(
            "On-chain RPC request failed for %s block %s (%s)",
            chain.value,
            height,
            type(error).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Configured blockchain RPC provider could not return a valid block",
        ) from error


@app.get(
    "/api/v1/cases/{case_id}/onchain-forensics",
    dependencies=[Security(verify_api_key)],
)
async def get_case_ethereum_forensics(
    case_id: str,
    height: int = Query(..., ge=0, le=2**64 - 1),
) -> Dict[str, Any]:
    if get_incident_case_store().get_case(case_id) is None:
        raise HTTPException(status_code=404, detail="Incident case not found")
    try:
        client = get_onchain_rpc_client(ChainName.ETHEREUM)
        block, logs, transfers = await client.get_block_logs(height)
        addresses = sorted(
            {
                address
                for transfer in transfers
                for address in (transfer.from_address, transfer.to_address)
            }
        )
        provider_assessments = await run_in_threadpool(
            get_onchain_risk_store().list_for_addresses,
            case_id,
            ChainName.ETHEREUM,
            addresses,
        )
        store = get_onchain_block_store()
        storage = (
            await run_in_threadpool(store.store_block, case_id, block)
            if store is not None
            else {"enabled": False, "inserted": False}
        )
        return {
            "case_id": case_id,
            "chain": ChainName.ETHEREUM.value,
            "block": {
                "height": block.height,
                "block_hash": block.block_hash,
                "parent_hash": block.parent_hash,
                "timestamp": block.timestamp.isoformat(),
                "source": block.source,
                "observed_at": block.fetched_at.isoformat(),
            },
            "logs": [item.model_dump(mode="json") for item in logs],
            "transfer_observations": [
                {
                    **item.model_dump(mode="json"),
                    "value_atomic": (
                        str(item.value_atomic)
                        if item.value_atomic is not None
                        else None
                    ),
                    "token_id": str(item.token_id) if item.token_id is not None else None,
                }
                for item in transfers
            ],
            "provider_assessments": provider_assessments,
            "storage": storage,
            "regulatory_assessment": {
                "status": "NOT_ASSESSED",
                "frameworks": ["AML", "MiCA"],
                "reason": "On-chain observations and provider labels do not determine legal or regulatory compliance.",
            },
            "limitations": [
                "Logs are provider-returned observations tied to this block hash, not independently verified chain proofs.",
                "A Transfer-shaped event is not token metadata, an entity attribution, or an AML conclusion.",
                "The same event signature can be emitted by contracts that do not implement ERC-20 or ERC-721.",
                "Logs are returned for the requested block only; they are not retained in the block snapshot.",
                "No compliance with AML requirements or MiCA obligations is inferred.",
            ],
        }
    except OnChainStoreCapacityError as error:
        raise HTTPException(status_code=413, detail=str(error)) from error
    except OnChainRiskResultTooLarge as error:
        raise HTTPException(status_code=413, detail=str(error)) from error
    except OnChainProviderError as error:
        _LOGGER.warning(
            "Ethereum forensic query failed for block %s (%s)",
            height,
            type(error).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Configured Ethereum node could not return valid forensic evidence",
        ) from error


@app.get(
    "/api/v1/cases/{case_id}/onchain-traces/{transaction_hash}",
    dependencies=[Security(verify_api_key)],
)
async def get_case_ethereum_transaction_trace(
    case_id: str,
    transaction_hash: str,
) -> Dict[str, Any]:
    if get_incident_case_store().get_case(case_id) is None:
        raise HTTPException(status_code=404, detail="Incident case not found")
    if re.fullmatch(r"0x[0-9a-fA-F]{64}", transaction_hash) is None:
        raise HTTPException(
            status_code=422,
            detail="transaction_hash must be a 32-byte EVM hash",
        )
    try:
        client = get_onchain_rpc_client(ChainName.ETHEREUM)
        result = await client.trace_transaction(transaction_hash)
        return {
            "case_id": case_id,
            **result,
            "regulatory_assessment": {
                "status": "NOT_ASSESSED",
                "frameworks": ["AML", "MiCA"],
                "reason": "A node trace does not determine legal or regulatory compliance.",
            },
        }
    except OnChainProviderError as error:
        _LOGGER.warning(
            "Ethereum trace query failed for transaction %s (%s)",
            transaction_hash[:10],
            type(error).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Configured Ethereum node could not return a valid transaction trace",
        ) from error


@app.get(
    "/api/v1/cases/{case_id}/onchain-blocks",
    dependencies=[Security(verify_api_key)],
)
async def list_case_onchain_snapshots(
    case_id: str,
    chain: ChainName | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0, le=MAX_SNAPSHOTS_PER_CASE),
) -> Dict[str, Any]:
    if get_incident_case_store().get_case(case_id) is None:
        raise HTTPException(status_code=404, detail="Incident case not found")
    store = get_onchain_block_store()
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="On-chain snapshot storage is not enabled",
        )
    try:
        return await run_in_threadpool(
            store.list_snapshots,
            case_id,
            chain=chain,
            limit=limit,
            offset=offset,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post(
    "/api/v1/cases/{case_id}/onchain-risk/import",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Security(verify_api_key)],
)
async def import_case_onchain_risk_report(
    case_id: str,
    payload: OnChainRiskImportRequest,
) -> Dict[str, Any]:
    if get_incident_case_store().get_case(case_id) is None:
        raise HTTPException(status_code=404, detail="Incident case not found")
    try:
        report, report_sha256 = OnChainRiskImportFile.parse_content(payload.content)
        result = await run_in_threadpool(
            get_onchain_risk_store().import_report,
            case_id,
            report,
            report_sha256=report_sha256,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail="Risk report is invalid; verify it matches the documented import schema",
        ) from error
    return {
        **result,
        "status": "IMPORTED_PROVIDER_REPORTS_UNVERIFIED",
        "raw_report_persisted": False,
        "limitations": [
            "The report is operator-supplied; Sanctum Suite does not authenticate the external provider or verify the provider's signature.",
            "Imported ratings retain their provider meaning and are not combined into a Sanctum risk score.",
        ],
    }


@app.post(
    "/api/v1/cases/{case_id}/purple-team/replays",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Security(verify_api_key)],
)
async def evaluate_case_purple_team_replay(
    case_id: str,
    payload: PurpleTeamReplayRequest,
) -> Dict[str, Any]:
    case_store = get_incident_case_store()
    case = case_store.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Incident case not found")
    observed_alerts = [
        {
            "scenario_id": event["detection_scenario_id"],
            "rule_id": event["detection_rule_id"],
            "event_id": event["event_id"],
            "event_type": event["event_type"],
            "source": event["source"],
        }
        for event in case["timeline"]
        if event.get("detection_scenario_id") is not None
        and event.get("detection_rule_id") is not None
    ]
    result = purple_team_coordinator.coordinate_emulation_cycle(
        payload.scenario_id,
        payload.expected_rule_id,
        observed_alerts,
    )
    replay = case_store.add_purple_team_replay(
        case_id,
        scenario_id=payload.scenario_id,
        expected_rule_id=payload.expected_rule_id,
        evaluated_by=_authenticated_actor_label(payload.evaluated_by),
        result=result,
    )
    if replay is None:
        raise HTTPException(status_code=404, detail="Incident case not found")
    return replay


@app.get("/api/v1/cases/{case_id}/report", dependencies=[Security(verify_api_key)])
async def export_incident_case_report(case_id: str) -> Dict[str, Any]:
    case = get_incident_case_store().get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Incident case not found")
    report: Dict[str, Any] = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_classification": "OPERATOR_PROVIDED",
        "case": case,
        "limitations": [
            "The report contains operator-provided metadata and evidence references, not evidence contents.",
            "Source-reported severities and Purple Team alert identifiers are not independently verified.",
            "Detection replay evaluates recorded alert metadata only; it does not execute attack behavior or contact an EDR/XDR service.",
            "A report digest identifies these serialized report contents; it does not establish their truth, completeness, or authenticity.",
        ],
    }
    canonical_report = json.dumps(
        report, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    report["report_sha256"] = hashlib.sha256(
        canonical_report.encode("utf-8")
    ).hexdigest()
    return report


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
            case_id,
            author=_authenticated_actor_label(payload.author),
            body=payload.body,
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
            added_by=_authenticated_actor_label(payload.added_by),
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
            case_id, simulated_by=_authenticated_actor_label(payload.simulated_by)
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
            reviewer=_authenticated_actor_label(payload.reviewer),
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
            "OIDC subject/tenant values come from validated token claims; legacy API-key "
            "requests identify only a shared credential fingerprint. Request bodies, "
            "credentials, client IP addresses, and query strings are not stored. This "
            "SQLite audit is operational metadata, not a tamper-proof immutable log."
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
    """Readiness probe checks that at least one complete authentication mode is configured."""
    try:
        configured_oidc = oidc_configuration()
    except OIDCAuthenticationError:
        configured_oidc = None
        oidc_invalid = True
    else:
        oidc_invalid = False
    opa_ready: bool | None = None
    opa_policy_version: str | None = None
    try:
        opa_client = get_opa_policy_client(required=production_environment())
    except OPAPolicyConfigurationError:
        opa_client = None
        opa_ready = False
    if opa_client is not None:
        try:
            opa_policy_version = await opa_client.verify_readiness()
        except OPAPolicyUnavailable as error:
            opa_ready = False
            _LOGGER.warning(
                "OPA readiness probe failed (%s)",
                type(error).__name__,
            )
        else:
            opa_ready = True
    elif production_environment():
        opa_ready = False

    tpm_ready: bool | None = None
    try:
        tpm_client = get_tpm_attestation_client(required=production_environment())
    except TPMAttestationConfigurationError as error:
        tpm_client = None
        tpm_ready = False
        _LOGGER.warning(
            "TPM measured-boot readiness configuration is invalid (%s)",
            type(error).__name__,
        )
    if tpm_client is not None:
        try:
            await tpm_client.verify_readiness()
        except TPMAttestationUnavailable as error:
            tpm_ready = False
            _LOGGER.warning(
                "TPM measured-boot readiness probe failed (%s)",
                type(error).__name__,
            )
        else:
            tpm_ready = True
    elif production_environment():
        tpm_ready = False

    tee_ready: bool | None = None
    try:
        tee_client = get_tee_attestation_client(required=production_environment())
    except TEEAttestationConfigurationError as error:
        tee_client = None
        tee_ready = False
        _LOGGER.warning(
            "Confidential-computing readiness configuration is invalid (%s)",
            type(error).__name__,
        )
    if tee_client is not None:
        try:
            await tee_client.verify_readiness()
        except TEEAttestationUnavailable as error:
            tee_ready = False
            _LOGGER.warning(
                "Confidential-computing readiness probe failed (%s)",
                type(error).__name__,
            )
        else:
            tee_ready = True
    elif production_environment():
        tee_ready = False

    legacy_configured = len(os.environ.get("SANCTUM_API_KEY", "").encode("utf-8")) >= 32
    oidc_required = production_environment()
    legacy_enabled = os.environ.get(
        "SANCTUM_ALLOW_LEGACY_API_KEY", ""
    ).casefold() in {"1", "true", "yes"}
    auth_ready = not oidc_invalid and (
        configured_oidc is not None
        if oidc_required
        else configured_oidc is not None or legacy_configured
    )
    if oidc_required and legacy_enabled:
        auth_ready = False

    kms_ready: bool | None = None
    audit_ready: bool | None = None
    pseudonymization_ready: bool | None = None
    report_signing_ready: bool | None = None
    if oidc_required:
        try:
            ZeroTrustKMSVault(require_production=True)
        except KMSConfigurationError:
            kms_ready = False
        else:
            kms_ready = True
        try:
            get_audit_pseudonymizer()
        except AuditPseudonymizationConfigurationError:
            pseudonymization_ready = False
        else:
            pseudonymization_ready = True
        try:
            get_report_signer()
        except (OSError, ValueError):
            report_signing_ready = False
        else:
            report_signing_ready = True
    if immutable_audit_required():
        try:
            await run_in_threadpool(get_immutable_audit_store().verify_configuration)
        except ImmutableAuditConfigurationError:
            audit_ready = False
        else:
            audit_ready = True

    if (
        not auth_ready
        or kms_ready is False
        or audit_ready is False
        or pseudonymization_ready is False
        or report_signing_ready is False
        or opa_ready is False
        or tpm_ready is False
        or tee_ready is False
    ):
        return Response(
            content=json.dumps(
                {
                    "status": "NOT_READY",
                    "components": {
                        "oidc": auth_ready,
                        "vault_transit_configuration": kms_ready,
                        "minio_object_lock_configuration": audit_ready,
                        "audit_pseudonymization": pseudonymization_ready,
                        "report_signing": report_signing_ready,
                        "opa_policy": opa_ready,
                        "tpm_measured_boot": tpm_ready,
                        "confidential_computing": tee_ready,
                    },
                }
            ),
            status_code=503,
            media_type="application/json",
        )
    return {
        "status": "READY",
        "api_auth_configured": auth_ready,
        "authentication_modes": (
            ["oidc"] if configured_oidc is not None else ["legacy_api_key"]
        ),
        "vault_transit_configured": kms_ready,
        "minio_object_lock_configured": audit_ready,
        "audit_pseudonymization_configured": pseudonymization_ready,
        "report_signing_configured": report_signing_ready,
        "opa_policy_configured": opa_ready,
        "opa_policy_version": opa_policy_version,
        "tpm_measured_boot_configured": tpm_ready,
        "confidential_computing_configured": tee_ready,
    }

@app.get("/metrics")
async def metrics():
    """Endpoint eksportu metryk w formacie Prometheus."""
    metrics_data = (
        "# HELP sanctum_audits_total Audits completed by this API process.\n"
        "# TYPE sanctum_audits_total counter\n"
        f"sanctum_audits_total {audits_total}\n"
    )
    return Response(content=metrics_data, media_type="text/plain")
