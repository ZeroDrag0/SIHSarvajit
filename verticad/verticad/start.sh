#!/usr/bin/env bash
# Runs the VERTICAD backend (:8000) and frontend (:5173) together. Ctrl+C stops both.
set -e
cd "$(dirname "$0")"

[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q -r pipeline/src/Schependomlaan/requirements.txt -r backend/requirements.txt
(cd web && npm install)

(cd backend && python -m uvicorn app.main:app --reload --port 8000) &
BACKEND_PID=$!
trap 'kill $BACKEND_PID 2>/dev/null' EXIT INT TERM

echo "Open http://localhost:5173"
cd web && npm run dev
