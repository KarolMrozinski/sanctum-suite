from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError


_BUCKET_PATTERN = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_RETENTION_YEARS = 7
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

        object_retention = retention.get("Retention", {})
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
