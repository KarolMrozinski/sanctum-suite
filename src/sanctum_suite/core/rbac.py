from enum import Enum
from fastapi import HTTPException, status
from typing import List


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    AUDITOR = "AUDITOR"
    VIEWER = "VIEWER"


class RBACPermissionManager:
    """Zarządcza warstwa uprawnień RBAC i wielotenantowości."""

    ROLE_PERMISSIONS = {
        UserRole.ADMIN: ["RUN_AUDIT", "INSPECT_PROMPT", "EXPORT_SIEM", "VIEW_ANALYTICS"],
        UserRole.AUDITOR: ["RUN_AUDIT", "VIEW_ANALYTICS"],
        UserRole.VIEWER: ["VIEW_ANALYTICS"],
    }

    @classmethod
    def verify_permission(cls, user_role: UserRole, required_permission: str) -> None:
        allowed_permissions = cls.ROLE_PERMISSIONS.get(user_role, [])
        if required_permission not in allowed_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user_role.value}' lacks required permission: '{required_permission}'",
            )