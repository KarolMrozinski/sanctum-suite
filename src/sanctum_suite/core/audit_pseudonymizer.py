import hashlib
import hmac
import os
from pathlib import Path


class AuditPseudonymizationConfigurationError(ValueError):
    """Raised when the audit pseudonymization key is not safely configured."""


class AuditPseudonymizer:
    """Creates stable, keyed pseudonyms for identity fields in audit records."""

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
        if namespace not in {"subject", "tenant"}:
            raise ValueError("Audit pseudonym namespace is not supported")
        if not value or len(value) > 255:
            raise ValueError("Audit identity value is invalid")
        message = f"{namespace}:{value}".encode("utf-8")
        return hmac.new(self._key, message, hashlib.sha256).hexdigest()
