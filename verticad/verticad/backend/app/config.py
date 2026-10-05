"""Backend settings. Paths resolve relative to the repo root; override with env vars."""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_SRC = Path(os.environ.get("VERTICAD_PIPELINE_SRC", REPO_ROOT / "pipeline" / "src"))
DATASET_ROOT = Path(os.environ.get("VERTICAD_DATASET_ROOT", REPO_ROOT / "pipeline" / "Schependomlaan")).resolve()
PROCESSED = DATASET_ROOT / "processed"
RAW_IFC_DIR = DATASET_ROOT / "raw" / "ifc"
RAW_PC_DIR = DATASET_ROOT / "raw" / "pointcloud"
WEB_DIST = Path(os.environ.get("VERTICAD_WEB_DIST", REPO_ROOT / "web" / "dist"))
CORS_ORIGINS = [o.strip() for o in os.environ.get(
    "VERTICAD_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]
MAX_IFC_BYTES = int(os.environ.get("VERTICAD_MAX_IFC_MB", "500")) * 1024 * 1024

# API path -> (file under processed/, media type). Mirrors web/src/api/client.ts ENDPOINTS exactly.
ENDPOINTS: dict[str, tuple[str, str]] = {
    "/api/building": ("building.json", "application/json"),
    "/api/floors": ("floors.json", "application/json"),
    "/api/units": ("property_units.json", "application/json"),
    "/api/ulpins": ("ulpins.json", "application/json"),
    "/api/validation": ("topology_validation.json", "application/json"),
    "/api/provenance": ("provenance.json", "application/json"),
    "/api/metrics": ("pipeline_report.json", "application/json"),
    "/api/pointcloud": ("pointcloud_inventory.json", "application/json"),
    "/api/cadastral": ("3d_cadastral_model.json", "application/json"),
    "/api/spaces": ("space_classification.json", "application/json"),
    "/api/spaces/geometry": ("geometry/space_geometry.json", "application/json"),
    "/api/assets/property_units.glb": ("geometry/property_units.glb", "model/gltf-binary"),
}
