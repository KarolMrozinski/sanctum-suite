from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import boto3
from sanctum_suite.core.audit_chain import canonical_json
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError


_BUCKET_PATTERN = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_AUDIT_OBJECT_KEY_PATTERN = re.compile(
    r"^api-access/\d{4}/\d{2}/\d{2}/"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.json$"
)
_RETENTION_YEARS = 7
_MAX_CHECKPOINT_RECORDS = 100_000
_MAX_AUDIT_OBJECT_BYTES = 64_000
_MAX_CHECKPOINT_ARCHIVE_BYTES = 256_000_000
_ALLOWED_RECORD_FIELDS = {
    "event_id",
    "request_id",
    "event_type",
    "method",
    "route_group",
    "route",
    "credential_fingerprint",
    "subject_pseudonym",
    "tenant_pseudonym",
    "authentication_method",
    "outcome_code",
    "source",
}


class ImmutableAuditConfigurationError(ValueError):
    """Raised when the immutable audit store is missing or unsafe configuration."""


class ImmutableAuditError(RuntimeError):
    """Raised when an immutable audit record cannot be durably verified."""


class MinioImmutableAuditStore:
    """Writes minimal audit events to an S3-compatible Object Lock bucket."""

    def __init__(self, client: BaseClient | None = None) -> None:
        endpoint = os.environ.get("SANCTUM_AUDIT_S3_ENDPOINT", "").strip()
        parsed_endpoint = urlparse(endpoint)
        if (
            parsed_endpoint.scheme != "https"
            or not parsed_endpoint.netloc
            or parsed_endpoint.username is not None
            or parsed_endpoint.password is not None
            or parsed_endpoint.query
            or parsed_endpoint.fragment
        ):
            raise ImmutableAuditConfigurationError(
                "SANCTUM_AUDIT_S3_ENDPOINT must be an HTTPS endpoint without credentials"
            )
        bucket = os.environ.get("SANCTUM_AUDIT_S3_BUCKET", "").strip()
        if not _BUCKET_PATTERN.fullmatch(bucket):
            raise ImmutableAuditConfigurationError(
                "SANCTUM_AUDIT_S3_BUCKET must be a valid lowercase bucket name"
            )
        access_key = MinioImmutableAuditStore._read_secret(
            "SANCTUM_AUDIT_S3_ACCESS_KEY_ID",
            "SANCTUM_AUDIT_S3_ACCESS_KEY_FILE",
        )
        secret_key = MinioImmutableAuditStore._read_secret(
            "SANCTUM_AUDIT_S3_SECRET_ACCESS_KEY",
            "SANCTUM_AUDIT_S3_SECRET_ACCESS_KEY_FILE",
        )
        if not access_key or not secret_key:
            raise ImmutableAuditConfigurationError(
                "Configure MinIO credentials through the deployment secret manager"
            )
        region = os.environ.get("SANCTUM_AUDIT_S3_REGION", "us-east-1").strip()
        if not region:
            raise ImmutableAuditConfigurationError(
                "SANCTUM_AUDIT_S3_REGION must not be empty"
            )
        ca_bundle = os.environ.get("SANCTUM_AUDIT_S3_CA_CERT", "").strip()
        if ca_bundle and not Path(ca_bundle).expanduser().is_file():
            raise ImmutableAuditConfigurationError(
                "SANCTUM_AUDIT_S3_CA_CERT must reference an existing CA bundle"
            )

        self.bucket = bucket
        if client is not None:
            self._client = client
        else:
            try:
                self._client = boto3.client(
                    "s3",
                    endpoint_url=endpoint,
                    region_name=region,
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    verify=str(Path(ca_bundle).expanduser()) if ca_bundle else True,
                    config=Config(
                        signature_version="s3v4",
                        connect_timeout=3,
                        read_timeout=5,
                        retries={"max_attempts": 2, "mode": "standard"},
                        s3={"addressing_style": "path"},
                    ),
                )
            except (BotoCoreError, ClientError, ValueError) as error:
                raise ImmutableAuditConfigurationError(
                    "Unable to initialize the MinIO audit client"
                ) from error
        self.verify_configuration()

    @staticmethod
    def _read_secret(value_name: str, file_name: str) -> str:
        value = os.environ.get(value_name, "").strip()
        file_path = os.environ.get(file_name, "").strip()
        if value and file_path:
            raise ImmutableAuditConfigurationError(
                f"Configure only one of {value_name} or {file_name}"
            )
        if file_path:
            try:
                value = Path(file_path).expanduser().read_text(encoding="utf-8").strip()
            except OSError as error:
                raise ImmutableAuditConfigurationError(
                    f"Unable to read {file_name}"
                ) from error
        return value

    def verify_configuration(self) -> None:
        try:
            versioning = self._client.get_bucket_versioning(Bucket=self.bucket)
            lock = self._client.get_object_lock_configuration(Bucket=self.bucket)
        except (BotoCoreError, ClientError) as error:
            raise ImmutableAuditConfigurationError(
                "Unable to verify MinIO bucket versioning and Object Lock configuration"
            ) from error
        if versioning.get("Status") != "Enabled":
            raise ImmutableAuditConfigurationError(
                "MinIO audit bucket must have versioning enabled"
            )
        configuration = lock.get("ObjectLockConfiguration", {})
        if configuration.get("ObjectLockEnabled") != "Enabled":
            raise ImmutableAuditConfigurationError(
                "MinIO audit bucket must have Object Lock enabled"
            )

    @staticmethod
    def _retention_date(now: datetime) -> datetime:
        try:
            return now.replace(year=now.year + _RETENTION_YEARS)
        except ValueError:
            return now.replace(year=now.year + _RETENTION_YEARS, day=28)

    def write_event(self, record: dict[str, Any]) -> str:
        event_id = record.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("Immutable audit records require an event_id")
        try:
            event_id = str(uuid.UUID(event_id))
        except ValueError as error:
            raise ValueError("Immutable audit event_id must be a UUID") from error
        if set(record) - _ALLOWED_RECORD_FIELDS:
            raise ValueError("Immutable audit record contains unsupported fields")
        credential_fingerprint = record.get("credential_fingerprint")
        if credential_fingerprint is not None and (
            not isinstance(credential_fingerprint, str)
            or not _SHA256_PATTERN.fullmatch(credential_fingerprint)
        ):
            raise ValueError("credential_fingerprint must be a SHA-256 hex digest")
        for field in ("subject_pseudonym", "tenant_pseudonym"):
            pseudonym = record.get(field)
            if pseudonym is not None and (
                not isinstance(pseudonym, str)
                or not _SHA256_PATTERN.fullmatch(pseudonym)
            ):
                raise ValueError(f"{field} must be a SHA-256 hex digest")
        request_id = record.get("request_id")
        if request_id is not None:
            try:
                uuid.UUID(request_id)
            except (TypeError, ValueError) as error:
                raise ValueError("request_id must be a UUID") from error
        event_type = record.get("event_type")
        if event_type not in {
            "request_started",
            "request_completed",
            "storage_preflight",
        }:
            raise ValueError("Immutable audit event_type is not supported")
        outcome_code = record.get("outcome_code")
        if outcome_code is not None and (
            isinstance(outcome_code, bool)
            or not isinstance(outcome_code, int)
            or not 100 <= outcome_code <= 599
        ):
            raise ValueError("outcome_code must be a valid HTTP status code")
        now = datetime.now(timezone.utc)
        timestamp = now.isoformat()
        body = json.dumps(
            {**record, "event_id": event_id, "occurred_at": timestamp},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        digest = hashlib.sha256(body).hexdigest()
        key = f"api-access/{now:%Y/%m/%d}/{event_id}.json"
        try:
            response = self._client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=body,
                ContentType="application/json",
                Metadata={"sha256": digest},
                ObjectLockMode="COMPLIANCE",
                ObjectLockRetainUntilDate=self._retention_date(now),
            )
            version_id = response.get("VersionId")
            if not isinstance(version_id, str) or not version_id:
                raise ImmutableAuditError(
                    "MinIO did not return a version ID for the immutable audit record"
                )
            retention = self._client.get_object_retention(
                Bucket=self.bucket,
                Key=key,
                VersionId=version_id,
            )
        except ImmutableAuditError:
            raise
        except (BotoCoreError, ClientError) as error:
            raise ImmutableAuditError(
                "MinIO failed to store or verify an immutable audit record"
            ) from error

        object_retention = (
            retention.get("Retention", {}) if isinstance(retention, dict) else {}
        )
        mode = object_retention.get("Mode")
        retain_until = object_retention.get("RetainUntilDate")
        if (
            mode != "COMPLIANCE"
            or not isinstance(retain_until, datetime)
            or retain_until < self._retention_date(now)
        ):
            raise ImmutableAuditError(
                "MinIO did not apply the required seven-year Compliance retention"
            )
        return key

    def verify_access(self) -> None:
        self.write_event(
            {
                "event_id": str(uuid.uuid4()),
                "event_type": "storage_preflight",
                "source": "sanctum-suite",
            }
        )

    def _list_audit_versions_once(self) -> list[tuple[str, str]]:
        versions: list[tuple[str, str]] = []
        key_marker: str | None = None
        version_marker: str | None = None
        seen_markers: set[tuple[str | None, str | None]] = set()
        while True:
            arguments: dict[str, Any] = {
                "Bucket": self.bucket,
                "Prefix": "api-access/",
                "MaxKeys": 1_000,
            }
            if key_marker is not None:
                arguments["KeyMarker"] = key_marker
            if version_marker is not None:
                arguments["VersionIdMarker"] = version_marker
            try:
                page = self._client.list_object_versions(**arguments)
            except (BotoCoreError, ClientError) as error:
                raise ImmutableAuditError(
                    "MinIO failed to enumerate immutable audit object versions"
                ) from error
            if page.get("DeleteMarkers"):
                raise ImmutableAuditError(
                    "Audit checkpoint refused because the WORM prefix contains delete markers"
                )
            for version in page.get("Versions", []):
                key = version.get("Key")
                version_id = version.get("VersionId")
                if (
                    not isinstance(key, str)
                    or not _AUDIT_OBJECT_KEY_PATTERN.fullmatch(key)
                    or not isinstance(version_id, str)
                    or not version_id
                ):
                    raise ImmutableAuditError(
                        "MinIO returned an invalid audit object version"
                    )
                versions.append((key, version_id))
                if len(versions) > _MAX_CHECKPOINT_RECORDS:
                    raise ImmutableAuditError(
                        "Audit checkpoint exceeds the 100000-version limit"
                    )
            if not page.get("IsTruncated"):
                break
            next_key_marker = page.get("NextKeyMarker")
            next_version_marker = page.get("NextVersionIdMarker")
            cursor = (next_key_marker, next_version_marker)
            if (
                not isinstance(next_key_marker, str)
                or not next_key_marker
                or cursor in seen_markers
            ):
                raise ImmutableAuditError(
                    "MinIO returned an invalid audit version pagination cursor"
                )
            seen_markers.add(cursor)
            key_marker, version_marker = cursor
        return sorted(versions)

    def _stable_audit_inventory(self) -> list[tuple[str, str]]:
        previous: list[tuple[str, str]] | None = None
        for _ in range(5):
            current = self._list_audit_versions_once()
            if current == previous:
                return current
            previous = current
            time.sleep(0.05)
        raise ImmutableAuditError(
            "Audit object inventory changed during checkpoint creation; retry later"
        )

    def read_audit_records(self) -> list[dict[str, str | bytes]]:
        """Read a stable, version-pinned snapshot of retained audit objects."""
        inventory = self._stable_audit_inventory()
        records: list[dict[str, str | bytes]] = []
        total_bytes = 0
        for key, version_id in inventory:
            try:
                response = self._client.get_object(
                    Bucket=self.bucket,
                    Key=key,
                    VersionId=version_id,
                )
                body_stream = response["Body"]
                try:
                    body = body_stream.read(1_000_001)
                finally:
                    body_stream.close()
                retention = self._client.get_object_retention(
                    Bucket=self.bucket,
                    Key=key,
                    VersionId=version_id,
                )
            except (BotoCoreError, ClientError, KeyError, OSError) as error:
                raise ImmutableAuditError(
                    "MinIO failed to read or verify an audit object version"
                ) from error
            if len(body) > _MAX_AUDIT_OBJECT_BYTES:
                raise ImmutableAuditError(
                    "Audit object exceeds the 64-kilobyte checkpoint limit"
                )
            metadata = response.get("Metadata", {})
            recorded_digest = metadata.get("sha256") if isinstance(metadata, dict) else None
            digest = hashlib.sha256(body).hexdigest()
            if not isinstance(recorded_digest, str) or not hmac.compare_digest(
                recorded_digest, digest
            ):
                raise ImmutableAuditError(
                    "MinIO audit object content does not match its SHA-256 metadata"
                )
            try:
                record = json.loads(body)
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ImmutableAuditError(
                    "MinIO audit object is not valid UTF-8 JSON"
                ) from error
            event_id = record.get("event_id") if isinstance(record, dict) else None
            try:
                expected_event_id = str(uuid.UUID(key.rsplit("/", 1)[1][:-5]))
            except (ValueError, IndexError) as error:
                raise ImmutableAuditError(
                    "MinIO returned an invalid audit object key"
                ) from error
            object_retention = retention.get("Retention", {})
            occurred_at = record.get("occurred_at") if isinstance(record, dict) else None
            try:
                record_timestamp = datetime.fromisoformat(occurred_at)
            except (TypeError, ValueError) as error:
                raise ImmutableAuditError(
                    "MinIO audit record has an invalid occurrence timestamp"
                ) from error
            retain_until = object_retention.get("RetainUntilDate")
            if (
                not isinstance(record, dict)
                or canonical_json(record) != body
                or event_id != expected_event_id
                or record.get("event_type")
                not in {
                    "request_started",
                    "request_completed",
                    "storage_preflight",
                }
                or record_timestamp.tzinfo is None
                or record_timestamp.utcoffset() is None
                or not isinstance(object_retention, dict)
                or object_retention.get("Mode") != "COMPLIANCE"
                or not isinstance(retain_until, datetime)
                or retain_until.tzinfo is None
                or retain_until < self._retention_date(record_timestamp)
            ):
                raise ImmutableAuditError(
                    "MinIO audit object version failed content or retention verification"
                )
            records.append(
                {
                    "key": key,
                    "version_id": version_id,
                    "record_sha256": digest,
                    "body": body,
                }
            )
            total_bytes += len(body)
            if total_bytes > _MAX_CHECKPOINT_ARCHIVE_BYTES:
                raise ImmutableAuditError(
                    "Audit checkpoint archive exceeds the 256-megabyte limit"
                )
        return records
