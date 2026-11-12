from __future__ import annotations

import base64
import os
from abc import ABC, abstractmethod
from typing import Any

from sanctum_suite.core.kms_vault import KMSConfigurationError, ZeroTrustKMSVault


class KeyManagementProvider(ABC):
    """Provider-neutral key-management abstraction for local or managed KMS backends."""

    @abstractmethod
    def encrypt(self, plaintext: str) -> dict[str, str]:
        raise NotImplementedError

    @abstractmethod
    def decrypt(self, envelope: dict[str, str]) -> str:
        raise NotImplementedError

    @abstractmethod
    def verify_production_access(self) -> None:
        raise NotImplementedError


class ExternalKMSAdapter(KeyManagementProvider):
    def __init__(self, *, require_production: bool = False, config: dict[str, Any] | None = None) -> None:
        if config:
            for key, value in config.items():
                if value is not None:
                    os.environ[str(key)] = str(value)
        self._vault = ZeroTrustKMSVault(require_production=require_production)

    def encrypt(self, plaintext: str) -> dict[str, str]:
        return self._vault.encrypt_payload(plaintext)

    def decrypt(self, envelope: dict[str, str]) -> str:
        return self._vault.decrypt_payload(envelope)

    def verify_production_access(self) -> None:
        self._vault.verify_production_access()

    @property
    def backend(self) -> str:
        return self._vault.backend


class ManagedKeyProvider(ExternalKMSAdapter):
    pass


class KeyRotationError(RuntimeError):
    pass


class ExternalKMSFacade:
    def __init__(self, provider: KeyManagementProvider | None = None) -> None:
        self.provider = provider or ExternalKMSAdapter()

    def encrypt(self, plaintext: str) -> dict[str, str]:
        return self.provider.encrypt(plaintext)

    def decrypt(self, envelope: dict[str, str]) -> str:
        return self.provider.decrypt(envelope)

    def rotate(self, plaintext: str) -> dict[str, str]:
        encrypted = self.provider.encrypt(plaintext)
        if not encrypted.get("ciphertext"):
            raise KeyRotationError("KMS provider did not return a ciphertext")
        return encrypted

    def status(self) -> dict[str, str]:
        return {"backend": self.provider.backend if hasattr(self.provider, "backend") else "configured"}


__all__ = [
    "KeyManagementProvider",
    "ExternalKMSAdapter",
    "ManagedKeyProvider",
    "KeyRotationError",
    "ExternalKMSFacade",
]
