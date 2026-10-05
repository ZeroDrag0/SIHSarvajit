"""Coordinate-reference handling. Nothing is assumed to be georeferenced unless verified."""
from __future__ import annotations

from typing import Any

SUPPORTED = {"local": None, "RD_New": "EPSG:28992", "RDNAP": "EPSG:7415", "NAP_height": "EPSG:5709"}


def crs_record(*, graph: dict[str, Any] | None = None, control_points: list[dict] | None = None,
               declared_target: str | None = None) -> dict[str, Any]:
    """Return the CRS record every output carries.

    `control_points` (GNSS/CORS) are only accepted when supplied locally; none are fabricated.
    """
    geo = (graph or {}).get("georeferencing", {})
    declared = geo.get("coordinate_status", "local/unverified")
    rec = {
        "source_crs": "IFC local engineering coordinates",
        "source_crs_declared_in_ifc": geo.get("ifc_projected_crs"),
        "target_crs": declared_target,
        "vertical_reference": "local datum (NAP not verified)",
        "transformation_status": "not_performed",
        "coordinate_status": "local/unverified" if declared in ("local/unverified",) else declared,
        "gnss_cors_control": "not_available",
        "notes": ["IFC is not assumed to be georeferenced"],
    }
    if control_points:
        rec["gnss_cors_control"] = f"{len(control_points)} control points supplied locally; transformation not applied automatically"
        rec["notes"].append("control points present: a fit can be computed with fit_helmert_2d_z()")
    return rec


def load_control_points(path) -> list[dict]:
    """CSV/JSON of {id, local_x, local_y, local_z, rd_x, rd_y, nap_z}; returns [] when absent."""
    import csv, json
    from pathlib import Path
    p = Path(path) if path else None
    if not p or not p.is_file():
        return []
    if p.suffix.lower() == ".json":
        return json.loads(p.read_text())
    with open(p, newline="") as f:
        return [{k: (float(v) if k != "id" else v) for k, v in row.items()} for row in csv.DictReader(f)]


def fit_helmert_2d_z(points: list[dict]) -> dict[str, Any]:
    """Least-squares 4-parameter (scale, rotation, tx, ty) + z-offset from >=2 control points."""
    import numpy as np
    if len(points) < 2:
        return {"status": "insufficient_control_points", "required": 2, "given": len(points)}
    L = np.array([[p["local_x"], p["local_y"]] for p in points])
    R = np.array([[p["rd_x"], p["rd_y"]] for p in points])
    Lc, Rc = L.mean(0), R.mean(0)
    l, r = L - Lc, R - Rc
    num_a = (l[:, 0] * r[:, 0] + l[:, 1] * r[:, 1]).sum()
    num_b = (l[:, 0] * r[:, 1] - l[:, 1] * r[:, 0]).sum()
    den = (l ** 2).sum()
    A, B = num_a / den, num_b / den
    tx = Rc[0] - (A * Lc[0] - B * Lc[1])
    ty = Rc[1] - (B * Lc[0] + A * Lc[1])
    pred = np.c_[A * L[:, 0] - B * L[:, 1] + tx, B * L[:, 0] + A * L[:, 1] + ty]
    rmse = float(np.sqrt(((pred - R) ** 2).sum(1).mean()))
    dz = float(np.mean([p["nap_z"] - p["local_z"] for p in points])) if all("nap_z" in p for p in points) else None
    return {"status": "fitted", "scale": float(np.hypot(A, B)), "rotation_rad": float(np.arctan2(B, A)),
            "tx": float(tx), "ty": float(ty), "dz": dz, "rmse_m": rmse, "n": len(points),
            "note": "RMSE of control-point fit; not an official RDNAP transformation"}
