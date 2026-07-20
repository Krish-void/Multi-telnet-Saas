from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional
from backend.models import TenantLoginRequest, SuperLoginRequest, LoginResponse
from backend.database import get_connection
from backend.auth import verify_password, create_token, revoke_token
from backend.middleware import require_auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/super-login", response_model=LoginResponse)
def super_login(body: SuperLoginRequest):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT admin_id, username, password_hash FROM system_admins WHERE username = %s",
                (body.username,),
            )
            admin = cur.fetchone()
    finally:
        conn.close()

    if not admin or not verify_password(body.password, admin["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid super admin credentials")

    session_data = {
        "user_id": admin["admin_id"],
        "user_type": "superadmin",
        "username": admin["username"],
    }
    token = create_token(session_data)
    return LoginResponse(token=token, **session_data)


@router.post("/tenant-login", response_model=LoginResponse)
def tenant_login(body: TenantLoginRequest):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.user_id, u.username, u.password_hash,
                       r.role_name, c.company_id, c.name AS company_name, c.tenant_uuid
                FROM users u
                JOIN roles r ON u.role_id = r.role_id
                JOIN companies c ON u.company_id = c.company_id
                WHERE u.username = %s AND c.tenant_uuid = %s
                """,
                (body.username, body.tenant_id),
            )
            user = cur.fetchone()
    finally:
        conn.close()

    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid tenant credentials")

    session_data = {
        "user_id": user["user_id"],
        "user_type": "tenant",
        "username": user["username"],
        "role": user["role_name"],
        "company_id": user["company_id"],
        "company_name": user["company_name"],
    }
    token = create_token(session_data)
    return LoginResponse(token=token, **session_data)


@router.post("/logout")
def logout(authorization: Optional[str] = Header(default=None)):
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        revoke_token(token)
    return {"message": "Logged out successfully"}


@router.get("/me")
def me(session: dict = Depends(require_auth)):
    return session
