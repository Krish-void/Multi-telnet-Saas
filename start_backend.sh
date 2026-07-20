#!/bin/bash
set -e

echo "Starting backend..."

# Run the database initialization script
# It has its own wait_for_mysql loop built-in, so it will wait until MariaDB is ready.
echo "Running init_db.py..."
python backend/init_db.py

# Start the FastAPI application
echo "Starting FastAPI server..."
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
