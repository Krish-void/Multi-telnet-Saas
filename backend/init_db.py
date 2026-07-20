"""
Database initialization: creates schema, triggers, view, stored function, and sample data.
Run once after MariaDB starts.
"""
import hashlib
import sys
import time

import pymysql
import os

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")   # Ya tera actual password
DB_NAME = os.getenv("DB_NAME", "saas_dbms")

def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def wait_for_mysql(retries: int = 30, delay: float = 1.5):
    for i in range(retries):
        try:
            conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD)
            conn.close()
            print("MySQL is ready.")
            return
        except Exception:
            print(f"Waiting for MySQL... ({i+1}/{retries})")
            time.sleep(delay)
    print("ERROR: MySQL did not start in time.", file=sys.stderr)
    sys.exit(1)


DDL = f"""
CREATE DATABASE IF NOT EXISTS `{DB_NAME}`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `{DB_NAME}`;

-- ─────────────────────────────────────────────────────────
--  Tables
-- ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS system_admins (
    admin_id      INT UNSIGNED     NOT NULL AUTO_INCREMENT,
    username      VARCHAR(60)      NOT NULL UNIQUE,
    password_hash CHAR(64)         NOT NULL,
    PRIMARY KEY (admin_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS companies (
    company_id   INT UNSIGNED     NOT NULL AUTO_INCREMENT,
    tenant_uuid  CHAR(36)         NOT NULL DEFAULT (UUID()),
    name         VARCHAR(120)     NOT NULL,
    db_name      VARCHAR(120)     NOT NULL UNIQUE,
    created_at   DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (company_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS roles (
    role_id    TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    role_name  VARCHAR(60)      NOT NULL UNIQUE,
    PRIMARY KEY (role_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS users (
    user_id       INT UNSIGNED     NOT NULL AUTO_INCREMENT,
    company_id    INT UNSIGNED     NOT NULL,
    role_id       TINYINT UNSIGNED NOT NULL,
    username      VARCHAR(60)      NOT NULL UNIQUE,
    password_hash CHAR(64)         NOT NULL,
    email         VARCHAR(120)     NOT NULL,
    created_at    DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    CONSTRAINT fk_users_company FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
    CONSTRAINT fk_users_role    FOREIGN KEY (role_id)    REFERENCES roles(role_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS logs (
    log_id     INT UNSIGNED NOT NULL AUTO_INCREMENT,
    action     VARCHAR(120) NOT NULL,
    user_id    INT UNSIGNED,
    details    TEXT,
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (log_id),
    CONSTRAINT fk_logs_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ─────────────────────────────────────────────────────────
--  Trigger: log every new user creation
-- ─────────────────────────────────────────────────────────

DROP TRIGGER IF EXISTS trg_after_user_insert;
CREATE TRIGGER trg_after_user_insert
AFTER INSERT ON users
FOR EACH ROW
BEGIN
    INSERT INTO logs (action, user_id, details)
    VALUES ('USER_CREATED', NEW.user_id,
            CONCAT('username=', NEW.username, '; company_id=', NEW.company_id));
END;

-- ─────────────────────────────────────────────────────────
--  View: restricted employee data (no password_hash)
-- ─────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW restricted_employee_view AS
SELECT
    u.user_id,
    u.username,
    u.email,
    r.role_name,
    c.name   AS company_name,
    c.tenant_uuid,
    u.created_at
FROM users u
JOIN roles    r ON u.role_id    = r.role_id
JOIN companies c ON u.company_id = c.company_id;

-- ─────────────────────────────────────────────────────────
--  Stored Function: count users per company
-- ─────────────────────────────────────────────────────────

DROP FUNCTION IF EXISTS count_users_per_company;
CREATE FUNCTION count_users_per_company(p_company_id INT UNSIGNED)
RETURNS INT
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE total INT DEFAULT 0;
    SELECT COUNT(*) INTO total FROM users WHERE company_id = p_company_id;
    RETURN total;
END;
"""

SAMPLE_DATA = f"""
USE `{DB_NAME}`;

INSERT IGNORE INTO system_admins (username, password_hash) VALUES
    ('superadmin', '{hash_password("superadmin123")}');

INSERT IGNORE INTO roles (role_name) VALUES
    ('Database Admin'),
    ('HR'),
    ('Developer'),
    ('Employee'),
    ('Customer'),
    ('Designer'),
    ('Manager'),
    ('QA Engineer'),
    ('DevOps'),
    ('Product Owner'),
    ('Sales'),
    ('Support'),
    ('Data Analyst'),
    ('Marketing'),
    ('Finance'),
    ('Legal'),
    ('Intern'),
    ('Contractor'),
    ('System Operator'),
    ('Content Creator');

INSERT IGNORE INTO companies (name, db_name) VALUES
    ('Acme Corp',       'acme_db'),
    ('Globex Inc',      'globex_db'),
    ('Initech LLC',     'initech_db');

INSERT IGNORE INTO users (company_id, role_id, username, password_hash, email) VALUES
    (1, 1, 'admin',    '{hash_password("admin123")}',    'admin@acme.com'),
    (1, 2, 'hr_alice', '{hash_password("alice123")}',    'alice@acme.com'),
    (1, 3, 'dev_bob',  '{hash_password("bob123")}',      'bob@acme.com'),
    (1, 4, 'emp_carl', '{hash_password("carl123")}',     'carl@acme.com'),
    (2, 1, 'globex_admin', '{hash_password("gadmin123")}','admin@globex.com'),
    (2, 3, 'dev_diana', '{hash_password("diana123")}',   'diana@globex.com'),
    (2, 6, 'des_eve',  '{hash_password("eve123")}',      'eve@globex.com'),
    (3, 2, 'hr_frank', '{hash_password("frank123")}',    'frank@initech.com'),
    (3, 5, 'cust_grace','{hash_password("grace123")}',   'grace@initech.com');

INSERT IGNORE INTO logs (action, user_id, details) VALUES
    ('SYSTEM_BOOT', NULL, 'Database initialized with sample data');
"""


def run_sql_block(conn, sql_block: str):
    """Execute a multi-statement block, skipping empty statements."""
    statements = [s.strip() for s in sql_block.split(";") if s.strip()]
    with conn.cursor() as cur:
        for stmt in statements:
            cur.execute(stmt)


def main():
    wait_for_mysql()

    # Run DDL (schema)
    conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, autocommit=True)
    try:
        with conn.cursor() as cur:
            # Split on DELIMITER blocks for trigger and function
            parts = DDL.split("END;")
            statements = []
            for part in parts:
                sub = [s.strip() for s in part.split(";") if s.strip()]
                statements.extend(sub)
                statements.append("END")

            full_stmts = []
            i = 0
            raw = DDL
            # simpler: execute file using multi-statement approach
        conn.close()

        # Reconnect and execute each statement individually
        conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, autocommit=True)

        # Parse and run DDL carefully (handle CREATE TRIGGER / FUNCTION with BEGIN...END)
        _execute_ddl(conn)
        print("Schema created/verified.")

        # Sample data
        for stmt in [s.strip() for s in SAMPLE_DATA.split(";") if s.strip()]:
            try:
                with conn.cursor() as cur:
                    cur.execute(stmt)
            except Exception as e:
                print(f"  (sample data skip): {e}")
        print("Sample data loaded.")
    finally:
        conn.close()

    print("Database initialization complete.")


def _execute_ddl(conn):
    """Execute DDL statements, properly handling BEGIN...END blocks."""
    simple_stmts = [
        f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci",
        f"USE `{DB_NAME}`",
        """CREATE TABLE IF NOT EXISTS system_admins (
            admin_id      INT UNSIGNED     NOT NULL AUTO_INCREMENT,
            username      VARCHAR(60)      NOT NULL UNIQUE,
            password_hash CHAR(64)         NOT NULL,
            PRIMARY KEY (admin_id)
        ) ENGINE=InnoDB""",
        """CREATE TABLE IF NOT EXISTS companies (
            company_id   INT UNSIGNED     NOT NULL AUTO_INCREMENT,
            tenant_uuid  CHAR(36)         NOT NULL DEFAULT (UUID()),
            name         VARCHAR(120)     NOT NULL,
            db_name      VARCHAR(120)     NOT NULL UNIQUE,
            created_at   DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (company_id)
        ) ENGINE=InnoDB""",
        """CREATE TABLE IF NOT EXISTS roles (
            role_id    TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
            role_name  VARCHAR(60)      NOT NULL UNIQUE,
            PRIMARY KEY (role_id)
        ) ENGINE=InnoDB""",
        """CREATE TABLE IF NOT EXISTS users (
            user_id       INT UNSIGNED     NOT NULL AUTO_INCREMENT,
            company_id    INT UNSIGNED     NOT NULL,
            role_id       TINYINT UNSIGNED NOT NULL,
            username      VARCHAR(60)      NOT NULL UNIQUE,
            password_hash CHAR(64)         NOT NULL,
            email         VARCHAR(120)     NOT NULL,
            created_at    DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id),
            CONSTRAINT fk_users_company FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
            CONSTRAINT fk_users_role    FOREIGN KEY (role_id)    REFERENCES roles(role_id)
        ) ENGINE=InnoDB""",
        """CREATE TABLE IF NOT EXISTS logs (
            log_id     INT UNSIGNED NOT NULL AUTO_INCREMENT,
            action     VARCHAR(120) NOT NULL,
            user_id    INT UNSIGNED,
            details    TEXT,
            created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (log_id),
            CONSTRAINT fk_logs_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
        ) ENGINE=InnoDB""",
        "DROP TRIGGER IF EXISTS trg_after_user_insert",
        """CREATE TRIGGER trg_after_user_insert
AFTER INSERT ON users
FOR EACH ROW
BEGIN
    INSERT INTO logs (action, user_id, details)
    VALUES ('USER_CREATED', NEW.user_id,
            CONCAT('username=', NEW.username, '; company_id=', NEW.company_id));
END""",
        """CREATE OR REPLACE VIEW restricted_employee_view AS
SELECT
    u.user_id,
    u.username,
    u.email,
    r.role_name,
    c.name   AS company_name,
    c.tenant_uuid,
    u.created_at
FROM users u
JOIN roles    r ON u.role_id    = r.role_id
JOIN companies c ON u.company_id = c.company_id""",
        "DROP FUNCTION IF EXISTS count_users_per_company",
        """CREATE FUNCTION count_users_per_company(p_company_id INT UNSIGNED)
RETURNS INT
READS SQL DATA
DETERMINISTIC
BEGIN
    DECLARE total INT DEFAULT 0;
    SELECT COUNT(*) INTO total FROM users WHERE company_id = p_company_id;
    RETURN total;
END""",
    ]

    for stmt in simple_stmts:
        try:
            with conn.cursor() as cur:
                cur.execute(stmt)
        except Exception as e:
            print(f"  DDL note: {e}")


if __name__ == "__main__":
    main()
