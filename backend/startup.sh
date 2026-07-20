#!/usr/bin/env bash
set -e

MYSQL_DATA_DIR="/tmp/mysql-data"
MYSQL_SOCKET="/tmp/mysql.sock"
MYSQL_PORT=3306
MYSQL_LOGFILE="/tmp/mysql.log"

echo "=== SaaS DBMS Backend Startup ==="

# ── 1. Initialize MariaDB data directory if it doesn't exist ──
if [ ! -d "$MYSQL_DATA_DIR/mysql" ]; then
    echo "Initializing MySQL data directory..."
    mysql_install_db \
        --datadir="$MYSQL_DATA_DIR" \
        --auth-root-authentication-method=normal \
        --skip-test-db \
        2>/dev/null || true
    echo "Data directory initialized."
fi

# ── 2. Kill any stale mysqld process ──
pkill -f "mysqld.*$MYSQL_DATA_DIR" 2>/dev/null || true
rm -f "$MYSQL_SOCKET" /tmp/mysql.pid

# ── 3. Start MariaDB ──
echo "Starting MariaDB..."
mysqld \
    --datadir="$MYSQL_DATA_DIR" \
    --socket="$MYSQL_SOCKET" \
    --port=$MYSQL_PORT \
    --user="$(whoami)" \
    --pid-file=/tmp/mysql.pid \
    --skip-networking=OFF \
    --bind-address=127.0.0.1 \
    --log-error="$MYSQL_LOGFILE" \
    --character-set-server=utf8mb4 \
    --collation-server=utf8mb4_unicode_ci \
    &

# ── 4. Wait for socket ──
echo "Waiting for MySQL socket..."
for i in $(seq 1 40); do
    if [ -S "$MYSQL_SOCKET" ]; then
        echo "MySQL socket is ready."
        break
    fi
    sleep 1
done

if [ ! -S "$MYSQL_SOCKET" ]; then
    echo "ERROR: MySQL socket not found after 40 seconds."
    cat "$MYSQL_LOGFILE" 2>/dev/null || true
    exit 1
fi

# ── 5. Initialize database schema and sample data ──
echo "Initializing database..."
python backend/init_db.py

# ── 6. Start FastAPI ──
echo "Starting FastAPI on port 8000..."
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload
