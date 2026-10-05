# VERTICAD – 3D vertical cadastre (SIH26011)

```
pipeline/   the model: IFC -> floors -> property units -> 3D geometry -> validation -> prototype 3D ULPIN
backend/    FastAPI: serves the model's outputs to the web app, and runs the model (upload IFC, run, publish)
web/        React + Three.js frontend (reads everything from the backend)
```

Flow: `web  --GET /api/*-->  backend  --reads-->  pipeline/Schependomlaan/processed/`
and `backend --POST /api/pipeline/run--> pipeline (subprocess) --> processed/` (atomic swap).

## Quick start (one command)
```
python run.py        # Windows: py run.py
```
Creates `.venv`, installs Python + npm dependencies on first run, starts the backend (:8000) and the frontend (:5173),
and opens http://localhost:5173. Ctrl+C stops both. Open `localhost`, never `0.0.0.0` (a bind address, not browsable).

## Landing page
The home route (`#/overview`) is the SIH landing page: `web/src/landing/Landing.tsx` + `landing.css`. It runs inside the same
app, dev server and backend as the viewer: "Open 3D Viewer" goes to `#/viewer`, and Explore / Data / Help scroll to sections.
The hero caption shows the loaded building's name and validation state. Styling uses Tailwind v4 (`tailwindcss`, `@tailwindcss/vite`),
isolated to the landing (no global reset, scanning limited to `src/landing`). After pulling, run `npm install` in `web/`.

## Run (development, two terminals)
```
pip install -r pipeline/src/Schependomlaan/requirements.txt -r backend/requirements.txt
cd backend && python -m uvicorn app.main:app --reload --port 8000

cd web && npm install && npm run dev          # http://localhost:5173 (vite proxies /api to :8000)
```

## Run (single server, demo / deployment)
```
cd web && npm install && npm run build
cd ../backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000   # app + API on http://localhost:8000
```

## API
The 12 data endpoints are exactly those in `web/src/api/client.ts` (the contract test enforces this) and return the
pipeline files unchanged. Extra endpoints:

| Endpoint | Purpose |
| --- | --- |
| GET /api/health | all contract files present? |
| GET /api/pipeline/status | IFC available, what is currently published |
| POST /api/pipeline/ifc | upload an `.ifc` (multipart field `file`) |
| POST /api/pipeline/run `{"stage":"all"}` | start the model (async, returns a job id); 409 if no IFC |
| GET /api/pipeline/jobs/{id} | job state + log |

A run works on a staging copy and replaces `processed/` only if the pipeline read a real IFC
(`source_mode == live_ifc`); the previous outputs are kept in `processed.prev/`. A failed run changes nothing.

The original Schependomlaan IFC is not in the repo (it was not in the upload). Put it in
`pipeline/Schependomlaan/raw/ifc/` or upload it through the API to regenerate the data. The committed `processed/`
outputs are what the app shows until then.

## Tests
```
cd backend && python -m pytest tests -q                         # API contract + end-to-end upload/run/publish
cd pipeline && PYTHONPATH=src python -m pytest tests -q         # the model
```
Env overrides: `VERTICAD_DATASET_ROOT`, `VERTICAD_WEB_DIST`, `VERTICAD_CORS_ORIGINS`, `VERTICAD_MAX_IFC_MB`.
