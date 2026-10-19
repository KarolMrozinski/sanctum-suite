import hashlib
import json
import asyncio
from types import SimpleNamespace
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from sanctum_suite.api import server
from sanctum_suite.core.immutable_audit import (
    ImmutableAuditConfigurationError,
    ImmutableAuditError,
    MinioImmutableAuditStore,
)
from sanctum_suite.core.incident_cases import IncidentCaseStore
from sanctum_suite.core.incident_governance import IncidentGovernanceStore
from sanctum_suite.core.audit_pseudonymizer import (
    AuditPseudonymizationConfigurationError,
    AuditPseudonymizer,
)


class FakeObjectLockClient:
    def __init__(self, *, versioning="Enabled", object_lock="Enabled"):
        self.versioning = versioning
        self.object_lock = object_lock
        self.put_arguments = []
        self.retain_until = None

    def get_bucket_versioning(self, **_kwargs):
        return {"Status": self.versioning}

    def get_object_lock_configuration(self, **_kwargs):
        return {
            "ObjectLockConfiguration": {
                "ObjectLockEnabled": self.object_lock,
            }
        }

    def put_object(self, **kwargs):
        self.put_arguments.append(kwargs)
        self.retain_until = kwargs["ObjectLockRetainUntilDate"]
        return {"VersionId": "version-1"}

    def get_object_retention(self, **_kwargs):
        return {
            "Retention": {
                "Mode": "COMPLIANCE",
                "RetainUntilDate": self.retain_until,
            }
        }


def _configure_minio(monkeypatch):
    monkeypatch.setenv("SANCTUM_AUDIT_S3_ENDPOINT", "https://minio.internal")
    monkeypatch.setenv("SANCTUM_AUDIT_S3_BUCKET", "sanctum-audit-worm")
    monkeypatch.setenv("SANCTUM_AUDIT_S3_ACCESS_KEY_ID", "test-access-key")
    monkeypatch.setenv("SANCTUM_AUDIT_S3_SECRET_ACCESS_KEY", "test-secret-key")


def test_minio_requires_bucket_versioning_and_object_lock(monkeypatch):
    _configure_minio(monkeypatch)
    with pytest.raises(
        ImmutableAuditConfigurationError, match="versioning enabled"
    ):
        MinioImmutableAuditStore(client=FakeObjectLockClient(versioning="Suspended"))

    with pytest.raises(
        ImmutableAuditConfigurationError, match="Object Lock enabled"
    ):
        MinioImmutableAuditStore(client=FakeObjectLockClient(object_lock="Disabled"))


def test_minio_reads_credentials_from_protected_files(monkeypatch, tmp_path):
    _configure_minio(monkeypatch)
    monkeypatch.delenv("SANCTUM_AUDIT_S3_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("SANCTUM_AUDIT_S3_SECRET_ACCESS_KEY", raising=False)
    access_key_file = tmp_path / "access-key"
    secret_key_file = tmp_path / "secret-key"
    access_key_file.write_text("minio-access\n", encoding="utf-8")
    secret_key_file.write_text("minio-secret\n", encoding="utf-8")
    monkeypatch.setenv("SANCTUM_AUDIT_S3_ACCESS_KEY_FILE", str(access_key_file))
    monkeypatch.setenv(
        "SANCTUM_AUDIT_S3_SECRET_ACCESS_KEY_FILE", str(secret_key_file)
    )

    store = MinioImmutableAuditStore(client=FakeObjectLockClient())

    assert store.bucket == "sanctum-audit-worm"


def test_minio_writes_compliance_locked_audit_object_for_seven_years(monkeypatch):
    _configure_minio(monkeypatch)
    client = FakeObjectLockClient()
    store = MinioImmutableAuditStore(client=client)
    event = {
        "event_id": "b2b5fb01-e42c-4ea5-9d97-07d2d4737932",
        "event_type": "request_completed",
        "credential_fingerprint": hashlib.sha256(b"api-key").hexdigest(),
        "route": "/api/v1/cases",
        "outcome_code": 200,
    }

    key = store.write_event(event)

    assert key.endswith(f"{event['event_id']}.json")
    stored = client.put_arguments[0]
    assert stored["ObjectLockMode"] == "COMPLIANCE"
    assert stored["ObjectLockRetainUntilDate"].year == (
        datetime.now(timezone.utc).year + 7
    )
    assert stored["Metadata"]["sha256"] == hashlib.sha256(stored["Body"]).hexdigest()
    assert json.loads(stored["Body"])["credential_fingerprint"] == event[
        "credential_fingerprint"
    ]
    assert "api-key" not in stored["Body"].decode("utf-8")


def test_audit_pseudonymizer_uses_keyed_namespace_separated_values(
    monkeypatch, tmp_path
):
    key_file = tmp_path / "audit-pseudonym-key"
    key_file.write_bytes(b"k" * 32)
    monkeypatch.setenv("SANCTUM_AUDIT_PSEUDONYM_KEY_FILE", str(key_file))
    pseudonymizer = AuditPseudonymizer()

    subject = pseudonymizer.pseudonymize("subject", "alice")
    tenant = pseudonymizer.pseudonymize("tenant", "alice")

    assert subject == pseudonymizer.pseudonymize("subject", "alice")
    assert subject != tenant
    assert len(subject) == 64
    assert subject != hashlib.sha256(b"alice").hexdigest()


def test_audit_pseudonymizer_requires_a_strong_secret_file(monkeypatch, tmp_path):
    key_file = tmp_path / "weak-key"
    key_file.write_bytes(b"short")
    monkeypatch.setenv("SANCTUM_AUDIT_PSEUDONYM_KEY_FILE", str(key_file))

    with pytest.raises(AuditPseudonymizationConfigurationError, match="32 bytes"):
        AuditPseudonymizer()


def test_production_audit_prewrite_stores_only_identity_pseudonyms(
    monkeypatch, tmp_path
):
    key_file = tmp_path / "audit-pseudonym-key"
    key_file.write_bytes(b"k" * 32)
    monkeypatch.setenv("SANCTUM_ENVIRONMENT", "air-gapped")
    monkeypatch.setenv("SANCTUM_AUDIT_PSEUDONYM_KEY_FILE", str(key_file))
    monkeypatch.setattr(server, "audit_pseudonymizer", None)

    class RecordingAuditStore:
        def __init__(self):
            self.records = []

        def write_event(self, record):
            self.records.append(record)
            return "audit/object"

    store = RecordingAuditStore()
    monkeypatch.setattr(server, "immutable_audit_store", store)
    request = SimpleNamespace(
        url=SimpleNamespace(path="/api/v1/cases"),
        method="GET",
        scope={"route": SimpleNamespace(path="/api/v1/cases")},
        state=SimpleNamespace(),
    )
    identity = server.AuthenticatedIdentity(
        subject="alice",
        tenant_id="tenant-a",
        roles=frozenset({"ADMIN"}),
        credential_fingerprint="a" * 16,
        authentication_method="oidc",
    )

    asyncio.run(server.record_immutable_audit_start(request, "bearer-token", identity))

    event = store.records[0]
    assert event["subject_pseudonym"] == server.get_audit_pseudonymizer().pseudonymize(
        "subject", "alice"
    )
    assert event["tenant_pseudonym"] == server.get_audit_pseudonymizer().pseudonymize(
        "tenant", "tenant-a"
    )
    assert "alice" not in json.dumps(event)
    assert "tenant-a" not in json.dumps(event)


def test_minio_preflight_writes_a_locked_canary(monkeypatch):
    _configure_minio(monkeypatch)
    client = FakeObjectLockClient()
    store = MinioImmutableAuditStore(client=client)

    store.verify_access()

    assert len(client.put_arguments) == 1
    assert json.loads(client.put_arguments[0]["Body"])["event_type"] == (
        "storage_preflight"
    )


def test_minio_rejects_unapproved_record_fields_before_upload(monkeypatch):
    _configure_minio(monkeypatch)
    client = FakeObjectLockClient()
    store = MinioImmutableAuditStore(client=client)

    with pytest.raises(ValueError, match="unsupported fields"):
        store.write_event(
            {
                "event_id": "b2b5fb01-e42c-4ea5-9d97-07d2d4737932",
                "request_body": "classified content",
            }
        )
    assert client.put_arguments == []


def test_minio_rejects_unverified_object_retention(monkeypatch):
    _configure_minio(monkeypatch)

    class IncompleteLockClient(FakeObjectLockClient):
        def get_object_retention(self, **_kwargs):
            return {
                "Retention": {
                    "Mode": "GOVERNANCE",
                    "RetainUntilDate": self.retain_until,
                }
            }

    store = MinioImmutableAuditStore(client=IncompleteLockClient())
    with pytest.raises(ImmutableAuditError, match="seven-year Compliance"):
        store.write_event(
            {
                "event_id": "b2b5fb01-e42c-4ea5-9d97-07d2d4737932",
                "event_type": "request_started",
            }
        )


def test_production_request_is_not_processed_if_audit_prewrite_fails(
    monkeypatch, tmp_path
):
    monkeypatch.delenv("SANCTUM_ENVIRONMENT", raising=False)
    monkeypatch.setenv("SANCTUM_IMMUTABLE_AUDIT_ENABLED", "true")
    monkeypatch.setenv("SANCTUM_API_KEY", "test-api-key-" + "x" * 40)
    monkeypatch.setattr(
        server,
        "incident_case_store",
        IncidentCaseStore(tmp_path / "cases.sqlite3"),
    )
    monkeypatch.setattr(
        server,
        "incident_governance_store",
        IncidentGovernanceStore(tmp_path / "cases.sqlite3"),
    )

    class UnavailableAuditStore:
        def write_event(self, _record):
            raise ImmutableAuditError("MinIO unavailable")

    monkeypatch.setattr(server, "immutable_audit_store", UnavailableAuditStore())
    monkeypatch.setattr(
        server,
        "get_incident_case_store",
        lambda: pytest.fail("The route must not run when the audit pre-write fails"),
    )
    response = TestClient(server.app).get(
        "/api/v1/cases",
        headers={"X-API-Key": "test-api-key-" + "x" * 40},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Immutable audit storage is unavailable"


def test_production_request_writes_start_and_completion_audit_events(
    monkeypatch, tmp_path
):
    monkeypatch.delenv("SANCTUM_ENVIRONMENT", raising=False)
    monkeypatch.setenv("SANCTUM_IMMUTABLE_AUDIT_ENABLED", "true")
    api_key = "test-api-key-" + "x" * 40
    monkeypatch.setenv("SANCTUM_API_KEY", api_key)
    cases = IncidentCaseStore(tmp_path / "cases.sqlite3")
    monkeypatch.setattr(server, "incident_case_store", cases)
    monkeypatch.setattr(
        server,
        "incident_governance_store",
        IncidentGovernanceStore(tmp_path / "cases.sqlite3"),
    )

    class RecordingAuditStore:
        def __init__(self):
            self.records = []

        def write_event(self, record):
            self.records.append(record)
            return "audit/object"

    audit_store = RecordingAuditStore()
    monkeypatch.setattr(server, "immutable_audit_store", audit_store)
    response = TestClient(server.app).get(
        "/api/v1/cases",
        headers={"X-API-Key": api_key},
    )

    assert response.status_code == 200
    assert [record["event_type"] for record in audit_store.records] == [
        "request_started",
        "request_completed",
    ]
    assert audit_store.records[0]["route_group"] == "/api/v1"
    assert audit_store.records[1]["route"] == "/api/v1/cases"
    assert audit_store.records[1]["outcome_code"] == 200
    assert audit_store.records[0]["request_id"] == audit_store.records[1]["request_id"]
    assert audit_store.records[0]["credential_fingerprint"] == hashlib.sha256(
        api_key.encode("utf-8")
    ).hexdigest()
    assert "subject_id" not in audit_store.records[1]
    assert "tenant_id" not in audit_store.records[1]


def test_invalid_credentials_do_not_create_immutable_objects(monkeypatch, tmp_path):
    monkeypatch.delenv("SANCTUM_ENVIRONMENT", raising=False)
    monkeypatch.setenv("SANCTUM_IMMUTABLE_AUDIT_ENABLED", "true")
    monkeypatch.setenv("SANCTUM_API_KEY", "test-api-key-" + "x" * 40)
    monkeypatch.setattr(
        server, "incident_case_store", IncidentCaseStore(tmp_path / "cases.sqlite3")
    )
    monkeypatch.setattr(
        server,
        "incident_governance_store",
        IncidentGovernanceStore(tmp_path / "cases.sqlite3"),
    )

    class RecordingAuditStore:
        def __init__(self):
            self.records = []

        def write_event(self, record):
            self.records.append(record)
            return "audit/object"

    audit_store = RecordingAuditStore()
    monkeypatch.setattr(server, "immutable_audit_store", audit_store)
    response = TestClient(server.app).get("/api/v1/cases")

    assert response.status_code == 401
    assert audit_store.records == []


def test_air_gapped_profile_rejects_legacy_api_key_authentication(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("SANCTUM_ENVIRONMENT", "air-gapped")
    monkeypatch.setenv("SANCTUM_API_KEY", "test-api-key-" + "x" * 40)
    monkeypatch.setenv("SANCTUM_ALLOW_LEGACY_API_KEY", "true")
    monkeypatch.delenv("SANCTUM_OIDC_ISSUER", raising=False)
    monkeypatch.delenv("SANCTUM_OIDC_AUDIENCE", raising=False)
    monkeypatch.setattr(
        server, "incident_case_store", IncidentCaseStore(tmp_path / "cases.sqlite3")
    )
    monkeypatch.setattr(
        server,
        "incident_governance_store",
        IncidentGovernanceStore(tmp_path / "cases.sqlite3"),
    )

    class RecordingAuditStore:
        def write_event(self, _record):
            return "audit/object"

    monkeypatch.setattr(server, "immutable_audit_store", RecordingAuditStore())
    response = TestClient(server.app).get(
        "/api/v1/cases",
        headers={"X-API-Key": "test-api-key-" + "x" * 40},
    )

    assert response.status_code == 503
    assert "requires Keycloak/OIDC" in response.json()["detail"]


def test_air_gapped_profile_rejects_legacy_authentication_opt_in(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("SANCTUM_ENVIRONMENT", "air-gapped")
    monkeypatch.setenv("SANCTUM_ALLOW_LEGACY_API_KEY", "true")
    monkeypatch.setenv("SANCTUM_OIDC_ISSUER", "https://keycloak.internal/realms/lab")
    monkeypatch.setenv("SANCTUM_OIDC_AUDIENCE", "sanctum-api")
    monkeypatch.delenv("SANCTUM_OIDC_CA_CERT", raising=False)
    monkeypatch.setattr(
        server, "incident_case_store", IncidentCaseStore(tmp_path / "cases.sqlite3")
    )
    monkeypatch.setattr(
        server,
        "incident_governance_store",
        IncidentGovernanceStore(tmp_path / "cases.sqlite3"),
    )

    class RecordingAuditStore:
        def write_event(self, _record):
            return "audit/object"

    monkeypatch.setattr(server, "immutable_audit_store", RecordingAuditStore())
    response = TestClient(server.app).get(
        "/api/v1/cases",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 503
    assert "Legacy shared API-key authentication is disabled" in response.json()[
        "detail"
    ]


def test_air_gapped_readiness_rejects_legacy_only_configuration(monkeypatch):
    monkeypatch.setenv("SANCTUM_ENVIRONMENT", "air-gapped")
    monkeypatch.setenv("SANCTUM_API_KEY", "test-api-key-" + "x" * 40)
    monkeypatch.delenv("SANCTUM_OIDC_ISSUER", raising=False)
    monkeypatch.delenv("SANCTUM_OIDC_AUDIENCE", raising=False)
    monkeypatch.delenv("SANCTUM_KMS_BACKEND", raising=False)

    class ReadyAuditStore:
        def verify_configuration(self):
            return None

    monkeypatch.setattr(server, "immutable_audit_store", ReadyAuditStore())
    response = TestClient(server.app).get("/readyz")

    assert response.status_code == 503
    assert response.json()["components"] == {
        "oidc": False,
        "vault_transit_configuration": False,
        "minio_object_lock_configuration": True,
        "audit_pseudonymization": False,
    }
