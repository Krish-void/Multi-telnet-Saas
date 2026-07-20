from fastapi import HTTPException, Header
from typing import Optional, List
from backend.auth import get_session

ROLE_PERMISSIONS: dict[str, List[str]] = {
    "Database Admin": ["users:read", "users:write", "users:delete", "logs:read"],
    "HR":             ["users:read", "users:write"],
    "Developer":      ["users:read"],
    "Designer":       ["users:read"],
    "Employee":       ["users:read"],
    "Customer":       [],
}


def require_auth(authorization: Optional[str] = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return session


def require_permission(permission: str):
    def checker(authorization: Optional[str] = Header(default=None)) -> dict:
        session = require_auth(authorization)
        user_type = session.get("user_type", "tenant")
        
        if user_type == "superadmin":
            if permission.startswith("companies:"):
                return session
            else:
                raise HTTPException(status_code=403, detail="Super Admin can only manage companies")

        role = session.get("role", "")
        allowed = ROLE_PERMISSIONS.get(role, [])
        if permission not in allowed:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{role}' does not have permission: {permission}",
            )
        return session
    return checker
