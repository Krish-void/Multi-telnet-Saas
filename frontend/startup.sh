#!/usr/bin/env bash
set -e
echo "=== Starting Streamlit Frontend ==="
exec streamlit run frontend/app.py \
    --server.port 5000 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false
