import hashlib
import hmac
import os
from pathlib import Path


class AuditPseudonymizationConfigurationError(ValueError):
    """Raised when the audit pseudonymization key is not safely configured."""


class AuditPseudonymizer:
    """Creates stable, namespace-separated keyed pseudonyms for privacy-sensitive IDs."""

    def __init__(self) -> None:
        key_file = os.environ.get("SANCTUM_AUDIT_PSEUDONYM_KEY_FILE", "").strip()
        if not key_file:
            raise AuditPseudonymizationConfigurationError(
                "SANCTUM_AUDIT_PSEUDONYM_KEY_FILE is required for pseudonymized audit"
            )
        try:
            key = Path(key_file).expanduser().read_bytes()
        except OSError as error:
            raise AuditPseudonymizationConfigurationError(
                "Unable to read SANCTUM_AUDIT_PSEUDONYM_KEY_FILE"
            ) from error
        if len(key) < 32:
            raise AuditPseudonymizationConfigurationError(
                "Audit pseudonymization key must contain at least 32 bytes"
            )
        self._key = key

    def pseudonymize(self, namespace: str, value: str) -> str:
        max_lengths = {
            "subject": 255,
            "tenant": 128,
            "source_event_id": 256,
            "correlation_token": 64,
        }
        max_length = max_lengths.get(namespace)
        if max_length is None:
            raise ValueError("Pseudonym namespace is not supported")
        if not isinstance(value, str) or not value or len(value) > max_length:
            raise ValueError("Pseudonym input value is invalid")
        message = f"{namespace}:{value}".encode("utf-8")
        return hmac.new(self._key, message, hashlib.sha256).hexdigest()
