from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent

# Runtime assets are the already-generated outputs from the web/model project.
# Override MODEL_DATA_DIR if the viewer assets live elsewhere on your machine.
MODEL_DATA_DIR = Path(
    os.getenv("MODEL_DATA_DIR", str(PROJECT_DIR / "viewer" / "public" / "data"))
).expanduser().resolve()

BUILDING = "Prestige Kingfisher Towers"
FILES = {
    "model": "kingfisher_building_3d.glb",
    "units_model": "kingfisher_units.glb",
    "metadata": "kingfisher_3d_metadata.json",
    "floors": "kingfisher_floors.json",
    "units": "kingfisher_units.json",
    "ulpins": "kingfisher_ulpin_prototypes.json",
    "validation": "kingfisher_final_validation.json",
    "metrics": "kingfisher_demo_metrics.json",
}


def read_json(name: str) -> Any:
    path = MODEL_DATA_DIR / FILES[name]
    if not path.is_file():
        raise HTTPException(status_code=500, detail=f"Runtime asset missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Invalid JSON asset: {path}") from exc


def asset_path(name: str) -> Path:
    path = MODEL_DATA_DIR / FILES[name]
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Asset not found: {path.name}")
    return path


app = FastAPI(
    title="VERTICAD Backend",
    version="1.0.0",
    description="API for the SIH 3D Vertical Cadastre demonstration.",
)

# Local development ports for the landing page and 3D viewer.
# In production, put both behind the same origin/reverse proxy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    model = MODEL_DATA_DIR / FILES["model"]
    return {
        "status": "ok",
        "building": BUILDING,
        "model_available": model.is_file(),
        "model_path": str(model),
        "data_directory": str(MODEL_DATA_DIR),
    }


@app.get("/api/config")
def config():
    return {
        "building": BUILDING,
        "model_url": "/api/assets/kingfisher_building_3d.glb",
        "units_model_url": "/api/assets/kingfisher_units.glb",
        "endpoints": {
            "floors": "/api/floors",
            "units": "/api/units",
            "ulpins": "/api/ulpins",
            "validation": "/api/validation",
            "metrics": "/api/metrics",
        },
    }


@app.get("/api/building")
def building():
    metadata = read_json("metadata")
    metrics = read_json("metrics")
    validation = read_json("validation")
    return {
        "building": BUILDING,
        "classification": metadata.get("classification"),
        "crs": metadata.get("crs"),
        "model": {
            "url": "/api/assets/kingfisher_building_3d.glb",
            "filename": FILES["model"],
        },
        "metrics": metrics,
        "validation": validation,
    }


@app.get("/api/floors")
def floors():
    return read_json("floors")


@app.get("/api/units")
def units(floor_id: str | None = Query(default=None)):
    data = read_json("units")
    if floor_id is None:
        return data

    floor = next((f for f in data.get("floors", []) if f.get("floor_id") == floor_id), None)
    if floor is None:
        raise HTTPException(status_code=404, detail=f"Unknown floor: {floor_id}")
    return {
        "building": data.get("building"),
        "floor_id": floor_id,
        "units": floor.get("units", []),
    }


@app.get("/api/ulpins")
def ulpins(
    q: str | None = Query(default=None, description="Search ULPIN, floor or unit ID"),
    floor_id: str | None = Query(default=None),
):
    data = read_json("ulpins")
    records = data.get("records", [])

    if floor_id:
        records = [r for r in records if r.get("floor_id") == floor_id]

    if q:
        needle = q.lower()
        records = [
            r for r in records
            if needle in str(r.get("ulpin_prototype", "")).lower()
            or needle in str(r.get("unit_id", "")).lower()
            or needle in str(r.get("floor_id", "")).lower()
        ]

    return {
        "building": data.get("building", BUILDING),
        "count": len(records),
        "records": records,
        "provenance_statement": data.get("provenance_statement"),
        "geometry_statement": data.get("geometry_statement"),
    }


@app.get("/api/validation")
def validation():
    return read_json("validation")


@app.get("/api/metrics")
def metrics():
    return read_json("metrics")


@app.get("/api/assets/{asset_name}")
def assets(asset_name: str):
    # Only expose the known generated runtime assets, never arbitrary filesystem paths.
    allowed = set(FILES.values())
    if asset_name not in allowed:
        raise HTTPException(status_code=404, detail="Asset not available")
    path = asset_path(next(key for key, value in FILES.items() if value == asset_name))
    return FileResponse(path)


@app.get("/")
def root():
    return {
        "service": "VERTICAD Backend",
        "docs": "/docs",
        "health": "/api/health",
    }
