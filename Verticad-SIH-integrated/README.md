# VERTICAD — SIH 2026 integrated demo

This package connects the existing landing page, the existing React/Three.js 3D viewer, and a FastAPI backend.

## Architecture

Landing page (Vite :5173)
        |
        | "Open 3D Viewer"
        v
3D viewer (Vite :5174)
        |
        | REST + GLB requests
        v
FastAPI backend (:8000)
        |
        +--> viewer/public/data/  (generated runtime model + JSON)
        +--> backend/data/processed/ (processed source datasets)
        +--> backend/pipeline_src/  (Python generation/validation scripts)

## Important model path

Do NOT point the backend at `C:\Users\DELL\Desktop\SIH Model\src`.

That `src` directory contains the Python generation/validation scripts.

With this integrated project, the actual runtime model is:

`C:\Users\DELL\Desktop\SIH Model\viewer\public\data\kingfisher_building_3d.glb`

If your folders are arranged differently, set `MODEL_DATA_DIR` in the backend environment.

## Run on Windows

### 1. Backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:MODEL_DATA_DIR = "..\viewer\public\data"
uvicorn main:app --reload --port 8000
```

Check:
- http://localhost:8000/api/health
- http://localhost:8000/docs

### 2. 3D viewer

Open another PowerShell:

```powershell
cd viewer
npm install
$env:VITE_API_BASE_URL = "http://localhost:8000"
npm run dev -- --port 5174
```

### 3. Landing page

Open another PowerShell:

```powershell
cd landing
npm install
$env:VITE_VIEWER_URL = "http://localhost:5174"
npm run dev -- --port 5173
```

Open http://localhost:5173.

## What was changed

1. Added `backend/main.py` with read-only APIs for building, floors, units, ULPINs, validation, metrics, and generated assets.
2. Added CORS for the local landing/viewer ports.
3. Changed the 3D viewer from directly reading `/data/*.json` and `/data/*.glb` to reading them through the backend API.
4. Changed the landing-page 3D viewer actions to link to the viewer app.
5. Kept the existing Three.js model, floor explorer, unit inspector, themes, camera controls, and UI intact.
6. Added environment variables so paths/ports can be changed without editing source code.
7. Included the processed source datasets and the existing Python pipeline scripts for the backend/project package.

## Data/provenance note

The supplied project itself classifies the building height/floor count/unit partitions as prototype/derived demonstration data. The backend exposes those existing outputs; it does not silently turn them into official cadastral facts.
