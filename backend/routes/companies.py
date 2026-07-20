from fastapi import APIRouter, HTTPException, Depends
from backend.models import CompanyCreate, CompanyUpdate, CompanyOut
from backend.database import get_connection
from backend.middleware import require_permission
from backend.auth import hash_password
from typing import List

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/", response_model=List[CompanyOut])
def list_companies(session: dict = Depends(require_permission("companies:read"))):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT company_id, tenant_uuid, name, db_name, created_at FROM companies ORDER BY company_id")
            rows = cur.fetchall()
        conn.commit()
        return rows
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.get("/{company_id}", response_model=CompanyOut)
def get_company(company_id: int, session: dict = Depends(require_permission("companies:read"))):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT company_id, tenant_uuid, name, db_name, created_at FROM companies WHERE company_id = %s",
                (company_id,),
            )
            row = cur.fetchone()
        conn.commit()
        if not row:
            raise HTTPException(status_code=404, detail="Company not found")
        return row
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.post("/", response_model=CompanyOut, status_code=201)
def create_company(body: CompanyCreate, session: dict = Depends(require_permission("companies:write"))):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO companies (name, db_name) VALUES (%s, %s)",
                (body.name, body.db_name),
            )
            new_id = cur.lastrowid
            
            # Create the initial admin user for this company (role_id = 1 = Database Admin)
            pw_hash = hash_password(body.admin_password)
            cur.execute(
                "INSERT INTO users (company_id, role_id, username, password_hash, email) VALUES (%s, %s, %s, %s, %s)",
                (new_id, 1, body.admin_username, pw_hash, body.admin_email)
            )

            cur.execute(
                "SELECT company_id, tenant_uuid, name, db_name, created_at FROM companies WHERE company_id = %s",
                (new_id,),
            )
            row = cur.fetchone()
        conn.commit()
        return row
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@router.put("/{company_id}", response_model=CompanyOut)
def update_company(company_id: int, body: CompanyUpdate, session: dict = Depends(require_permission("companies:write"))):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT company_id FROM companies WHERE company_id = %s", (company_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Company not found")

            updates = {}
            if body.name is not None:
                updates["name"] = body.name
            if body.db_name is not None:
                updates["db_name"] = body.db_name

            if updates:
                set_clause = ", ".join(f"{k} = %s" for k in updates)
                values = list(updates.values()) + [company_id]
                cur.execute(f"UPDATE companies SET {set_clause} WHERE company_id = %s", values)

            cur.execute(
                "SELECT company_id, tenant_uuid, name, db_name, created_at FROM companies WHERE company_id = %s",
                (company_id,),
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


@router.delete("/{company_id}")
def delete_company(company_id: int, session: dict = Depends(require_permission("companies:delete"))):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT company_id FROM companies WHERE company_id = %s", (company_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Company not found")
            cur.execute("DELETE FROM companies WHERE company_id = %s", (company_id,))
        conn.commit()
        return {"message": f"Company {company_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@router.get("/{company_id}/user-count")
def company_user_count(company_id: int, session: dict = Depends(require_permission("companies:read"))):
    """Uses the stored function count_users_per_company()."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT count_users_per_company(%s) AS user_count", (company_id,))
            row = cur.fetchone()
        conn.commit()
        return {"company_id": company_id, "user_count": row["user_count"]}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
