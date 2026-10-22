from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any


class VaultPKISecretsEngine:
    """Represents the Vault PKI secrets engine used for issuing certificates for controlled workloads."""

    def __init__(self, *, vault_addr: str | None = None, token: str | None = None, mount: str = "pki", namespace: str | None = None, ca_cert: str | None = None) -> None:
        self.vault_addr = vault_addr or os.environ.get("SANCTUM_VAULT_ADDR") or "https://vault.internal:8200"
        self.token = token or os.environ.get("SANCTUM_VAULT_TOKEN") or "vault-token"
        self.mount = mount
        self.namespace = namespace or os.environ.get("SANCTUM_VAULT_NAMESPACE")
        self.ca_cert = ca_cert or os.environ.get("SANCTUM_VAULT_CA_CERT")

    def issue_certificate(
        self,
        common_name: str,
        *,
        role: str = "sanctum-default",
        ttl: str = "24h",
        alt_names: list[str] | None = None,
        ip_sans: list[str] | None = None,
        uri_sans: list[str] | None = None,
        csr: str | None = None,
    ) -> dict[str, Any]:
        if not common_name:
            raise ValueError("common_name is required")
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(hours=int(ttl.rstrip("h")) if ttl.endswith("h") else 24)).isoformat()
        cert = {
            "common_name": common_name,
            "serial_number": f"{now.strftime('%Y%m%d%H%M%S')}-{abs(hash(common_name)) % 1_000_000:06d}",
            "issued_at": now.isoformat(),
            "expires_at": expires_at,
            "mount": self.mount,
            "role": role,
            "certificate": f"-----BEGIN CERTIFICATE-----\nMIIB... {common_name}\n-----END CERTIFICATE-----",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIE...\n-----END PRIVATE KEY-----",
            "ca_chain": ["-----BEGIN CERTIFICATE-----\nMIIC...\n-----END CERTIFICATE-----"],
            "alt_names": alt_names or [],
            "ip_sans": ip_sans or [],
            "uri_sans": uri_sans or [],
            "csr": csr,
        }
        return cert

    def revoke_certificate(self, serial_number: str) -> dict[str, Any]:
        return {"serial_number": serial_number, "revoked": True, "reason": "manual revocation"}

    def status(self) -> dict[str, Any]:
        return {"vault_addr": self.vault_addr, "mount": self.mount, "namespace": self.namespace, "ca_cert": self.ca_cert}


HashiCorpVaultPKI = VaultPKISecretsEngine
