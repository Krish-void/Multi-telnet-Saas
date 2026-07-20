import streamlit as st
import requests

import os

API_BASE = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="SaaS DBMS MVP",
    page_icon="🗄️",
    layout="wide",
)

# ─── Session state defaults ───────────────────────────────────────────────────
for key, default in {
    "token": None,
    "user": None,
    "page": "login",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def auth_headers() -> dict:
    return {"Authorization": f"Bearer {st.session_state.token}"}


def api_get(path: str):
    try:
        r = requests.get(f"{API_BASE}{path}", headers=auth_headers(), timeout=8)
        return r
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the API server. Make sure the backend is running.")
        return None


def api_post(path: str, json: dict):
    try:
        r = requests.post(f"{API_BASE}{path}", json=json, headers=auth_headers(), timeout=8)
        return r
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the API server.")
        return None


def api_put(path: str, json: dict):
    try:
        r = requests.put(f"{API_BASE}{path}", json=json, headers=auth_headers(), timeout=8)
        return r
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the API server.")
        return None


def api_delete(path: str):
    try:
        r = requests.delete(f"{API_BASE}{path}", headers=auth_headers(), timeout=8)
        return r
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the API server.")
        return None


# ─── Pages ────────────────────────────────────────────────────────────────────

def page_login():
    st.title("🗄️ SaaS DBMS MVP")
    
    tab1, tab2 = st.tabs(["🏢 Company Login", "⚙️ System Admin"])
    
    with tab1:
        st.subheader("Tenant Login")
        st.info("**Demo Accounts**\n\n"
                "Acme Corp: `87d7a672...` | `admin` | `admin123`\n\n"
                "Globex Inc: `87d7b729...` | `globex_admin` | `gadmin123`\n\n"
                "(Check DB for exact UUIDs)")
        
        with st.form("tenant_login_form"):
            tenant_id = st.text_input("Tenant ID (UUID)")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login as Company", use_container_width=True)
            
        if submitted:
            if not tenant_id or not username or not password:
                st.warning("All fields are required.")
            else:
                try:
                    r = requests.post(
                        f"{API_BASE}/auth/tenant-login",
                        json={"tenant_id": tenant_id, "username": username, "password": password},
                        timeout=8,
                    )
                    if r.status_code == 200:
                        data = r.json()
                        st.session_state.token = data["token"]
                        st.session_state.user = data
                        st.session_state.page = "dashboard"
                        st.rerun()
                    else:
                        st.error(r.json().get("detail", "Login failed"))
                except requests.exceptions.ConnectionError:
                    st.error("Cannot reach API server.")

    with tab2:
        st.subheader("Super Admin Login")
        st.info("**Default Super Admin**\n\n`superadmin` / `superadmin123`")
        
        with st.form("super_login_form"):
            s_username = st.text_input("Admin Username")
            s_password = st.text_input("Admin Password", type="password")
            s_submitted = st.form_submit_button("Login as System Admin", use_container_width=True)
            
        if s_submitted:
            if not s_username or not s_password:
                st.warning("All fields are required.")
            else:
                try:
                    r = requests.post(
                        f"{API_BASE}/auth/super-login",
                        json={"username": s_username, "password": s_password},
                        timeout=8,
                    )
                    if r.status_code == 200:
                        data = r.json()
                        st.session_state.token = data["token"]
                        st.session_state.user = data
                        st.session_state.page = "companies"
                        st.rerun()
                    else:
                        st.error(r.json().get("detail", "Login failed"))
                except requests.exceptions.ConnectionError:
                    st.error("Cannot reach API server.")


def page_dashboard():
    user = st.session_state.user
    st.title(f"📊 Dashboard")
    if user.get("user_type") == "superadmin":
        st.markdown(f"Welcome, **{user['username']}** &nbsp;|&nbsp; Role: `System Admin`")
    else:
        st.markdown(f"Welcome, **{user['username']}** &nbsp;|&nbsp; Role: `{user['role']}` &nbsp;|&nbsp; Company: **{user['company_name']}**")
    st.divider()

    col1, col2, col3 = st.columns(3)

    if user.get("user_type") != "superadmin":
        r = api_get("/users/count")
        if r and r.status_code == 200:
            count = r.json().get("user_count", "—")
            col1.metric("Users in Your Company", count)
        else:
            col1.metric("Users in Your Company", "—")
            
        r3 = api_get("/users/")
        if r3 and r3.status_code == 200:
            col3.metric("Total Users", len(r3.json()))
        else:
            col3.metric("Total Users", "—")
    else:
        col1.metric("Mode", "System Administration")
        col3.metric("Scope", "Global")

    r2 = api_get("/companies/")
    if r2 and r2.status_code == 200:
        col2.metric("Total Companies", len(r2.json()))
    elif r2:
        col2.metric("Total Companies", "—")
        col2.caption(r2.json().get("detail", "No access"))

    st.divider()
    
    if user.get("user_type") != "superadmin":
        st.subheader("👥 Your Company Users")
        r_users = api_get("/users/")
        if r_users and r_users.status_code == 200:
            rows = r_users.json()
            if rows:
                import pandas as pd
                df = pd.DataFrame(rows)[["user_id", "username", "email", "role_name", "created_at"]]
                df.columns = ["ID", "Username", "Email", "Role", "Created At"]
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No users found.")

def page_users():
    user = st.session_state.user
    st.title("👥 Users")

    has_write = user["role"] in ["Database Admin", "HR"]
    
    tabs_to_show = ["Directory"]
    if has_write:
        tabs_to_show.append("Manage Users")
    if user["role"] == "Database Admin":
        tabs_to_show.append("Audit Logs")
        
    selected_tab = st.tabs(tabs_to_show)

    # ── Directory (Read-Only) ──
    with selected_tab[0]:
        r = api_get("/users/view")
        if r and r.status_code == 200:
            rows = r.json()
            st.caption(f"Showing {len(rows)} employees in your company (Password hashes hidden)")
            if rows:
                import pandas as pd
                df = pd.DataFrame(rows)[["user_id", "username", "email", "role_name", "created_at"]]
                df.columns = ["ID", "Username", "Email", "Role", "Created At"]
                st.dataframe(df, use_container_width=True)
        elif r:
            st.warning(r.json().get("detail", "Access denied"))

    # ── Manage Users (CRUD) ──
    if has_write:
        with selected_tab[1]:
            st.subheader("Manage Employees")
            r_roles = api_get("/users/roles")
            roles = r_roles.json() if r_roles and r_roles.status_code == 200 else []
            role_options = {r["role_name"]: r["role_id"] for r in roles}
            
            col_create, col_update, col_delete = st.columns(3)
            
            # Create Form
            with col_create:
                st.markdown("#### Create User")
                with st.form("create_user_form"):
                    new_username = st.text_input("Username")
                    new_password = st.text_input("Password", type="password")
                    new_email = st.text_input("Email")
                    selected_role = st.selectbox("Role", options=list(role_options.keys()))
                    submitted = st.form_submit_button("Create", use_container_width=True)

                if submitted:
                    if not new_username or not new_password or not new_email:
                        st.warning("All fields are required.")
                    else:
                        payload = {
                            "username": new_username, "password": new_password,
                            "email": new_email, "role_id": role_options[selected_role],
                            "company_id": user["company_id"]
                        }
                        cr = api_post("/users/", payload)
                        if cr and cr.status_code == 201:
                            st.success(f"User '{new_username}' created!")
                            st.rerun()
                        elif cr:
                            st.error(cr.json().get("detail", "Error creating user"))
                            
            # Update Form
            with col_update:
                st.markdown("#### Update User")
                with st.form("update_user_form"):
                    upd_uid = st.number_input("User ID to Update", min_value=1, step=1)
                    upd_email = st.text_input("New Email (optional)")
                    upd_role = st.selectbox("New Role (optional)", options=["(Unchanged)"] + list(role_options.keys()))
                    upd_sub = st.form_submit_button("Update", use_container_width=True)
                    
                if upd_sub:
                    payload = {}
                    if upd_email: payload["email"] = upd_email
                    if upd_role != "(Unchanged)": payload["role_id"] = role_options[upd_role]
                    
                    if payload:
                        ur = api_put(f"/users/{int(upd_uid)}", payload)
                        if ur and ur.status_code == 200:
                            st.success(f"User {upd_uid} updated!")
                            st.rerun()
                        elif ur:
                            st.error(ur.json().get("detail", "Error updating user"))
                    else:
                        st.warning("No changes specified.")

            # Delete Form
            with col_delete:
                if user["role"] == "Database Admin":
                    st.markdown("#### Delete User")
                    with st.form("delete_user_form"):
                        del_uid = st.number_input("User ID to Delete", min_value=1, step=1)
                        del_sub = st.form_submit_button("Delete User", type="primary", use_container_width=True)
                        
                    if del_sub:
                        dr = api_delete(f"/users/{int(del_uid)}")
                        if dr and dr.status_code == 200:
                            st.success(dr.json()["message"])
                            st.rerun()
                        elif dr:
                            st.error(dr.json().get("detail", "Error deleting user"))
                else:
                    st.info("Delete permission requires Database Admin role.")

    # ── Audit Logs ──
    if user["role"] == "Database Admin":
        with selected_tab[-1]:
            st.caption("Populated automatically by trigger `trg_after_user_insert`")
            r = api_get("/users/logs")
            if r and r.status_code == 200:
                rows = r.json()
                if rows:
                    import pandas as pd
                    df = pd.DataFrame(rows)[["log_id", "action", "username", "details", "created_at"]]
                    df.columns = ["Log ID", "Action", "User", "Details", "Timestamp"]
                    st.dataframe(df, use_container_width=True)


def page_companies():
    user = st.session_state.user
    st.title("🏢 Companies")

    r = api_get("/companies/")
    if r is None:
        return
    if r.status_code != 200:
        st.warning(r.json().get("detail", "Access denied"))
        return

    companies = r.json()

    # Summary cards
    cols = st.columns(min(len(companies), 4))
    for i, comp in enumerate(companies):
        cr = api_get(f"/companies/{comp['company_id']}/user-count")
        ucount = cr.json().get("user_count", "?") if cr and cr.status_code == 200 else "?"
        with cols[i % len(cols)]:
            st.metric(comp["name"], f"{ucount} users", help=f"DB: {comp['db_name']}")

    st.divider()

    # Table
    import pandas as pd
    df = pd.DataFrame(companies)[["company_id", "name", "db_name", "tenant_uuid", "created_at"]]
    df.columns = ["ID", "Name", "DB Name", "Tenant UUID", "Created At"]
    st.dataframe(df, use_container_width=True)

    if user.get("user_type") == "superadmin":
        st.divider()
        col_create, col_delete = st.columns(2)

        with col_create:
            st.subheader("Register New Company")
            with st.form("create_company_form"):
                cname = st.text_input("Company Name")
                cdb = st.text_input("Database Name (slug)")
                st.markdown("---")
                st.caption("Initial DB Admin Credentials")
                a_user = st.text_input("Admin Username")
                a_pass = st.text_input("Admin Password", type="password")
                a_email = st.text_input("Admin Email")
                
                sub = st.form_submit_button("Create Company & Admin", use_container_width=True)
            if sub:
                if not cname or not cdb or not a_user or not a_pass or not a_email:
                    st.warning("All fields required.")
                else:
                    payload = {
                        "name": cname, "db_name": cdb,
                        "admin_username": a_user, "admin_password": a_pass, "admin_email": a_email
                    }
                    pr = api_post("/companies/", payload)
                    if pr and pr.status_code == 201:
                        data = pr.json()
                        st.success(f"Company '{cname}' created successfully!")
                        st.info(f"**Generated Tenant ID:** `{data['tenant_uuid']}`\n\nProvide this ID to the company along with their credentials.")
                    elif pr:
                        st.error(pr.json().get("detail", "Error"))

        with col_delete:
            st.subheader("Delete Company")
            cid = st.number_input("Company ID", min_value=1, step=1, key="del_cid")
            if st.button("Delete Company", type="primary", key="del_comp_btn"):
                dr = api_delete(f"/companies/{int(cid)}")
                if dr and dr.status_code == 200:
                    st.success(dr.json()["message"])
                    st.rerun()
                elif dr:
                    st.error(dr.json().get("detail", "Error"))


# ─── Navigation sidebar ───────────────────────────────────────────────────────

def sidebar():
    user = st.session_state.user
    with st.sidebar:
        st.markdown("## 🗄️ DBMS MVP")
        if user.get("user_type") == "superadmin":
            st.markdown(f"**{user['username']}**  \n`System Admin`")
            st.divider()
            if st.button("📊 Dashboard", use_container_width=True):
                st.session_state.page = "dashboard"
                st.rerun()
            if st.button("🏢 Companies", use_container_width=True):
                st.session_state.page = "companies"
                st.rerun()
        else:
            st.markdown(f"**{user['username']}**  \n`{user['role']}`  \n_{user['company_name']}_")
            st.divider()
            if st.button("📊 Dashboard", use_container_width=True):
                st.session_state.page = "dashboard"
                st.rerun()
            if st.button("👥 Users", use_container_width=True):
                st.session_state.page = "users"
                st.rerun()

        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            requests.post(f"{API_BASE}/auth/logout", headers=auth_headers())
            st.session_state.token = None
            st.session_state.user = None
            st.session_state.page = "login"
            st.rerun()

        st.divider()
        st.caption("FastAPI Docs → [/docs](http://localhost:8000/docs)")


# ─── Router ──────────────────────────────────────────────────────────────────

if not st.session_state.token:
    page_login()
else:
    sidebar()
    page = st.session_state.page
    if page == "dashboard":
        page_dashboard()
    elif page == "users":
        page_users()
    elif page == "companies":
        page_companies()
    else:
        page_dashboard()
