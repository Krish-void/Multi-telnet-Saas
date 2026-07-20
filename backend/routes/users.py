from fastapi import APIRouter, HTTPException, Depends
from backend.models import UserCreate, UserUpdate, UserOut, RoleOut, LogOut
from backend.database import get_connection
from backend.middleware import require_permission
from backend.auth import hash_password
from typing import List

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/roles", response_model=List[RoleOut])
def list_roles(session: dict = Depends(require_permission("users:read"))):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT role_id, role_name FROM roles ORDER BY role_id")
            rows = cur.fetchall()
        conn.commit()
        return rows
    finally:
        conn.close()


@router.get("/logs", response_model=List[LogOut])
def list_logs(session: dict = Depends(require_permission("logs:read"))):
    conn = get_connection()
    company_id = session.get("company_id")
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT l.log_id, l.action, l.user_id,
                       u.username, l.details, l.created_at
                FROM logs l
                LEFT JOIN users u ON l.user_id = u.user_id
                WHERE u.company_id = %s OR l.user_id IS NULL
                ORDER BY l.log_id DESC LIMIT 100
                """,
                (company_id,)
            )
            rows = cur.fetchall()
        conn.commit()
        return rows
    finally:
        conn.close()


@router.get("/view", response_model=List[dict])
def list_users_restricted(session: dict = Depends(require_permission("users:read"))):
    """Uses the restricted_employee_view (hides password_hash)."""
    conn = get_connection()
    company_id = session.get("company_id")
    try:
        with conn.cursor() as cur:
            # We must filter the view manually, since views don't take parameters.
            # In MySQL, we can join the view with users to filter, or since the view has user_id, 
            # actually we can't easily get company_id if we didn't include it in the view.
            # Wait, the view has user_id, username, email, role_name, company_name, tenant_uuid. 
            # We can filter by tenant_uuid? Or better, we can join with users to filter.
            cur.execute(
                "SELECT v.* FROM restricted_employee_view v JOIN users u ON v.user_id = u.user_id WHERE u.company_id = %s",
                (company_id,)
            )
            rows = cur.fetchall()
        conn.commit()
        return rows
    finally:
        conn.close()


@router.get("/", response_model=List[UserOut])
def list_users(session: dict = Depends(require_permission("users:read"))):
    conn = get_connection()
    company_id = session.get("company_id")
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.user_id, u.username, u.email,
                       r.role_name, c.name AS company_name, u.company_id, u.created_at
                FROM users u
                JOIN roles r ON u.role_id = r.role_id
                JOIN companies c ON u.company_id = c.company_id
                WHERE u.company_id = %s
                ORDER BY u.user_id
                """,
                (company_id,)
            )
            rows = cur.fetchall()
        conn.commit()
        return rows
    finally:
        conn.close()


@router.get("/count")
def count_users(session: dict = Depends(require_permission("users:read"))):
    conn = get_connection()
    company_id = session.get("company_id")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT count_users_per_company(%s) AS user_count", (company_id,))
            row = cur.fetchone()
        conn.commit()
        return {"user_count": row["user_count"]}
    finally:
        conn.close()


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, session: dict = Depends(require_permission("users:read"))):
    conn = get_connection()
    company_id = session.get("company_id")
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.user_id, u.username, u.email,
                       r.role_name, c.name AS company_name, u.company_id, u.created_at
                FROM users u
                JOIN roles r ON u.role_id = r.role_id
                JOIN companies c ON u.company_id = c.company_id
                WHERE u.user_id = %s AND u.company_id = %s
                """,
                (user_id, company_id),
            )
            row = cur.fetchone()
        conn.commit()
        if not row:
            raise HTTPException(status_code=404, detail="User not found or unauthorized")
        return row
    except HTTPException:
        raise
    finally:
        conn.close()


@router.post("/", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, session: dict = Depends(require_permission("users:write"))):
    conn = get_connection()
    company_id = session.get("company_id")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM users WHERE username = %s", (body.username,))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="Username already exists")

            pw_hash = hash_password(body.password)
            cur.execute(
                "INSERT INTO users (username, password_hash, email, role_id, company_id) VALUES (%s, %s, %s, %s, %s)",
                (body.username, pw_hash, body.email, body.role_id, company_id),
            )
            new_id = cur.lastrowid
            cur.execute(
                """
                SELECT u.user_id, u.username, u.email,
                       r.role_name, c.name AS company_name, u.company_id, u.created_at
                FROM users u
                JOIN roles r ON u.role_id = r.role_id
                JOIN companies c ON u.company_id = c.company_id
                WHERE u.user_id = %s
                """,
                (new_id,),
            )
            row = cur.fetchone()
        conn.commit()
        return row
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate, session: dict = Depends(require_permission("users:write"))):
    conn = get_connection()
    company_id = session.get("company_id")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM users WHERE user_id = %s AND company_id = %s", (user_id, company_id))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="User not found or unauthorized")

            updates = {}
            if body.email is not None:
                updates["email"] = body.email
            if body.role_id is not None:
                updates["role_id"] = body.role_id

            if updates:
                set_clause = ", ".join(f"{k} = %s" for k in updates)
                values = list(updates.values()) + [user_id]
                cur.execute(f"UPDATE users SET {set_clause} WHERE user_id = %s", values)

            cur.execute(
                """
                SELECT u.user_id, u.username, u.email,
                       r.role_name, c.name AS company_name, u.company_id, u.created_at
                FROM users u
                JOIN roles r ON u.role_id = r.role_id
                JOIN companies c ON u.company_id = c.company_id
                WHERE u.user_id = %s
                """,
                (user_id,),
            )
            row = cur.fetchone()
        conn.commit()
        return row
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@router.delete("/{user_id}")
def delete_user(user_id: int, session: dict = Depends(require_permission("users:delete"))):
    conn = get_connection()
    company_id = session.get("company_id")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM users WHERE user_id = %s AND company_id = %s", (user_id, company_id))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="User not found or unauthorized")
            cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        conn.commit()
        return {"message": f"User {user_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()
