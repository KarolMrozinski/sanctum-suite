import re
from typing import Any


_TENANT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


class TenantProvisioningManager:
    """Validates a tenant-registration request but does not store or isolate tenants."""

    def register_tenant(self, tenant_id: str, company_name: str) -> dict[str, Any]:
        if not _TENANT_ID_PATTERN.fullmatch(tenant_id):
            raise ValueError("tenant_id must be 1-64 safe identifier characters")
        name = company_name.strip()
        if not name or len(name) > 200:
            raise ValueError("company_name must contain between 1 and 200 characters")
        return {
            "tenant_id": tenant_id,
            "company_name": name,
            "status": "NOT_IMPLEMENTED",
            "data_isolation": "NOT_IMPLEMENTED",
            "tenant_authentication": "NOT_IMPLEMENTED",
            "record_persisted": False,
        }

    def get_tenant_config(self, tenant_id: str) -> dict[str, Any]:
        raise RuntimeError(
            f"Tenant configuration storage is not implemented for {tenant_id!r}"
        )
