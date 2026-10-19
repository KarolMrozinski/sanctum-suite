import base64
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

import httpx
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


_VAULT_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_VAULT_NAMESPACE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9/_-]{0,127}$")
_VAULT_TIMEOUT_SECONDS = 5.0


class KMSConfigurationError(ValueError):
    """Raised when the selected key-management backend is not safely configured."""


class VaultTransitError(RuntimeError):
    """Raised when HashiCorp Vault Transit cannot encrypt or decrypt a payload."""


class ZeroTrustKMSVault:
    """Encrypts payloads locally for development or via Vault Transit when configured."""

    def __init__(self, *, require_production: bool = False) -> None:
        backend = os.environ.get("SANCTUM_KMS_BACKEND", "").strip().lower()
        vault_configured = any(
            os.environ.get(name, "").strip()
            for name in (
                "SANCTUM_VAULT_ADDR",
                "SANCTUM_VAULT_TOKEN",
                "SANCTUM_VAULT_TOKEN_FILE",
                "SANCTUM_VAULT_TRANSIT_KEY",
            )
        )
        if not backend:
            if vault_configured:
                raise KMSConfigurationError(
                    "Set SANCTUM_KMS_BACKEND=vault-transit to use the configured Vault"
                )
            backend = "local-ephemeral"
        if backend not in {"local-ephemeral", "vault-transit"}:
            raise KMSConfigurationError(
                "SANCTUM_KMS_BACKEND must be local-ephemeral or vault-transit"
            )

        environment = os.environ.get("SANCTUM_ENVIRONMENT", "").strip().lower()
        production_mode = require_production or environment in {
            "production",
            "prod",
            "air-gapped",
            "air_gapped",
        }
        if production_mode and backend != "vault-transit":
            raise KMSConfigurationError(
                "Production requires SANCTUM_KMS_BACKEND=vault-transit"
            )

        self.backend = backend
        self.master_key: bytes | None = None
        self._vault: dict[str, str] | None = None
        if backend == "local-ephemeral":
            self.master_key = AESGCM.generate_key(bit_length=256)
        else:
            self._vault = self._load_vault_configuration()

    @staticmethod
    def _load_vault_configuration() -> dict[str, str]:
        address = os.environ.get("SANCTUM_VAULT_ADDR", "").strip()
        parsed_address = urlparse(address)
        if (
            parsed_address.scheme != "https"
            or not parsed_address.netloc
            or parsed_address.path not in {"", "/"}
            or parsed_address.username is not None
            or parsed_address.password is not None
            or parsed_address.query
            or parsed_address.fragment
        ):
            raise KMSConfigurationError(
                "SANCTUM_VAULT_ADDR must be an HTTPS Vault origin without credentials or path"
            )

        mount = os.environ.get("SANCTUM_VAULT_TRANSIT_MOUNT", "transit").strip()
        key_name = os.environ.get("SANCTUM_VAULT_TRANSIT_KEY", "").strip()
        if not _VAULT_COMPONENT.fullmatch(mount) or not _VAULT_COMPONENT.fullmatch(
            key_name
        ):
            raise KMSConfigurationError(
                "Configure a valid SANCTUM_VAULT_TRANSIT_MOUNT and "
                "SANCTUM_VAULT_TRANSIT_KEY"
            )

        token = os.environ.get("SANCTUM_VAULT_TOKEN", "").strip()
        token_file = os.environ.get("SANCTUM_VAULT_TOKEN_FILE", "").strip()
        if token and token_file:
            raise KMSConfigurationError(
                "Configure only one of SANCTUM_VAULT_TOKEN or SANCTUM_VAULT_TOKEN_FILE"
            )
        if token_file:
            try:
                token = Path(token_file).expanduser().read_text(encoding="utf-8").strip()
            except OSError as error:
                raise KMSConfigurationError(
                    "Unable to read SANCTUM_VAULT_TOKEN_FILE"
                ) from error
        if not token or "\n" in token or "\r" in token:
            raise KMSConfigurationError(
                "Configure a non-empty Vault token through the deployment secret manager"
            )

        namespace = os.environ.get("SANCTUM_VAULT_NAMESPACE", "").strip()
        if namespace and not _VAULT_NAMESPACE.fullmatch(namespace):
            raise KMSConfigurationError("SANCTUM_VAULT_NAMESPACE is invalid")
        ca_bundle = os.environ.get("SANCTUM_VAULT_CA_CERT", "").strip()
        if ca_bundle and not Path(ca_bundle).expanduser().is_file():
            raise KMSConfigurationError(
                "SANCTUM_VAULT_CA_CERT must reference an existing CA bundle file"
            )

        return {
            "address": address.rstrip("/"),
            "mount": mount,
            "key_name": key_name,
            "token": token,
            "namespace": namespace,
            "ca_bundle": str(Path(ca_bundle).expanduser()) if ca_bundle else "",
        }

    def encrypt_payload(self, raw_data: str) -> dict[str, str]:
        if self.backend == "vault-transit":
            assert self._vault is not None
            result = self._transit_request(
                "encrypt",
                {"plaintext": base64.b64encode(raw_data.encode("utf-8")).decode("ascii")},
            )
            ciphertext = result.get("ciphertext")
            if not isinstance(ciphertext, str) or not ciphertext.startswith("vault:v"):
                raise VaultTransitError(
                    "Vault Transit encrypt response is missing ciphertext"
                )
            return {
                "ciphertext": ciphertext,
                "key_management": "HASHICORP_VAULT_TRANSIT",
                "production_kms_configured": "true",
                "vault_transit_mount": self._vault["mount"],
                "vault_transit_key": self._vault["key_name"],
            }

        assert self.master_key is not None
        dek = AESGCM.generate_key(bit_length=256)
        nonce_data = os.urandom(12)
        ciphertext = AESGCM(dek).encrypt(nonce_data, raw_data.encode("utf-8"), None)
        nonce_dek = os.urandom(12)
        encrypted_dek = AESGCM(self.master_key).encrypt(nonce_dek, dek, None)
        return {
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
            "nonce_data": base64.b64encode(nonce_data).decode("ascii"),
            "encrypted_dek": base64.b64encode(encrypted_dek).decode("ascii"),
            "nonce_dek": base64.b64encode(nonce_dek).decode("ascii"),
            "key_management": "LOCAL_EPHEMERAL_PROCESS_MEMORY",
            "production_kms_configured": "false",
        }

    def decrypt_payload(self, envelope: dict[str, str]) -> str:
        if self.backend == "vault-transit":
            assert self._vault is not None
            if (
                envelope.get("key_management") != "HASHICORP_VAULT_TRANSIT"
                or envelope.get("vault_transit_mount") != self._vault["mount"]
                or envelope.get("vault_transit_key") != self._vault["key_name"]
            ):
                raise VaultTransitError(
                    "Envelope does not match the configured Vault Transit key"
                )
            ciphertext = envelope.get("ciphertext")
            if not isinstance(ciphertext, str) or not ciphertext.startswith("vault:v"):
                raise VaultTransitError("Envelope contains invalid Vault ciphertext")
            result = self._transit_request("decrypt", {"ciphertext": ciphertext})
            plaintext = result.get("plaintext")
            if not isinstance(plaintext, str):
                raise VaultTransitError(
                    "Vault Transit decrypt response is missing plaintext"
                )
            try:
                return base64.b64decode(plaintext, validate=True).decode("utf-8")
            except (ValueError, UnicodeDecodeError) as error:
                raise VaultTransitError(
                    "Vault Transit decrypt response contains invalid plaintext"
                ) from error

        if envelope.get("key_management") != "LOCAL_EPHEMERAL_PROCESS_MEMORY":
            raise ValueError("Envelope is not encrypted with the local ephemeral backend")
        assert self.master_key is not None
        try:
            encrypted_dek = base64.b64decode(envelope["encrypted_dek"], validate=True)
            nonce_dek = base64.b64decode(envelope["nonce_dek"], validate=True)
            ciphertext = base64.b64decode(envelope["ciphertext"], validate=True)
            nonce_data = base64.b64decode(envelope["nonce_data"], validate=True)
            dek = AESGCM(self.master_key).decrypt(nonce_dek, encrypted_dek, None)
            decrypted = AESGCM(dek).decrypt(nonce_data, ciphertext, None)
            return decrypted.decode("utf-8")
        except (InvalidTag, KeyError, ValueError, UnicodeDecodeError) as error:
            raise ValueError("Local ephemeral envelope is invalid or cannot be decrypted") from error

    def verify_production_access(self) -> None:
        if self.backend != "vault-transit":
            raise KMSConfigurationError(
                "Production key-management verification requires Vault Transit"
            )
        probe = "sanctum-vault-transit-preflight"
        if self.decrypt_payload(self.encrypt_payload(probe)) != probe:
            raise VaultTransitError("Vault Transit preflight round-trip verification failed")

    def _transit_request(self, operation: str, payload: dict[str, str]) -> dict[str, Any]:
        assert self._vault is not None
        mount = quote(self._vault["mount"], safe="")
        key_name = quote(self._vault["key_name"], safe="")
        url = (
            f"{self._vault['address']}/v1/{mount}/{operation}/{key_name}"
        )
        headers = {"X-Vault-Token": self._vault["token"]}
        if self._vault["namespace"]:
            headers["X-Vault-Namespace"] = self._vault["namespace"]
        verify: bool | str = self._vault["ca_bundle"] or True
        try:
            with httpx.Client(
                timeout=_VAULT_TIMEOUT_SECONDS,
                verify=verify,
                follow_redirects=False,
            ) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                document = response.json()
        except httpx.HTTPStatusError as error:
            raise VaultTransitError(
                f"Vault Transit {operation} request failed with HTTP "
                f"{error.response.status_code}"
            ) from error
        except (httpx.HTTPError, ValueError) as error:
            raise VaultTransitError(
                f"Vault Transit {operation} request failed"
            ) from error
        data = document.get("data") if isinstance(document, dict) else None
        if not isinstance(data, dict):
            raise VaultTransitError(
                f"Vault Transit {operation} response has an invalid shape"
            )
        return data
