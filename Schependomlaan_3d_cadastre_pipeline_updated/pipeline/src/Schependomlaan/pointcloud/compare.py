"""Point cloud <-> IFC geometry comparison (overlap, vertical range, point-to-surface distance, coverage).

Metrics are computed ONLY when the cloud is in a frame that is either
  (a) declared by a user-supplied registration file (`registration.json`, see `load_registrations`), or
  (b) judged "plausibly_co-registered" by `inventory.coverage_and_alignment` (unit scale + frame offset heuristic).
Otherwise the result is `not_computed_registration_unverified`; no alignment is ever estimated or invented here
(no ICP), and the vertical/horizontal extents are still reported as diagnostics.

Distance reference surface: the IfcSpace (room) meshes, i.e. the *net internal* room envelope.  Clouds captured
during construction contain scaffolding, partial structure and exterior surfaces, so low coverage / large distances
are expected for them and must not be read as model errors.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import trimesh


def load_registrations(dirs: list[Path]) -> list[dict[str, Any]]:
    """Optional `registration.json`: {"registrations": [{"file_name_contains": str, "unit_scale_to_m": float,
    "matrix_4x4": [[..]*4]*4 (applied after unit scaling, cloud -> IFC frame), "source": str}]}"""
    for d in dirs:
        f = Path(d) / "registration.json"
        if f.is_file():
            doc = json.loads(f.read_text(encoding="utf-8"))
            regs = doc.get("registrations", [])
            for r in regs:
                r["_file"] = str(f)
            return regs
    return []


def registration_for(name: str, regs: list[dict[str, Any]]) -> dict[str, Any] | None:
    for r in regs:
        if r.get("file_name_contains", "") in name:
            return r
    return None


def apply_registration(pts: np.ndarray, scale: float, matrix: list[list[float]] | None) -> np.ndarray:
    p = pts * scale
    if matrix is not None:
        M = np.asarray(matrix, dtype=float)
        p = p @ M[:3, :3].T + M[:3, 3]
    return p


def surface_samples(meshes: dict[str, trimesh.Trimesh], spacing_m: float, max_points: int, seed: int = 0) -> np.ndarray:
    """Area-weighted, seeded (deterministic) surface samples of all meshes."""
    total = sum(float(m.area) for m in meshes.values())
    if total <= 0:
        return np.empty((0, 3))
    n = int(min(max_points, max(1000, total / (spacing_m ** 2))))
    rng = np.random.default_rng(seed)
    out = []
    for m in meshes.values():
        k = max(1, int(round(n * float(m.area) / total)))
        pts, _ = trimesh.sample.sample_surface(m, k, seed=int(rng.integers(0, 2**31 - 1)))
        out.append(np.asarray(pts))
    return np.vstack(out)


def _stats(d: np.ndarray) -> dict[str, float]:
    return {"mean_m": float(d.mean()), "median_m": float(np.median(d)), "rmse_m": float(np.sqrt((d ** 2).mean())),
            "p95_m": float(np.percentile(d, 95)), "max_m": float(d.max())}


def compare_cloud(name: str, sample_pts: np.ndarray, point_count: int, scale: float, matrix, basis: str,
                  ifc_meshes: dict[str, trimesh.Trimesh], ifc_bounds: list[list[float]], params: dict[str, Any]) -> dict[str, Any]:
    """Metrics for one cloud already judged to be in (or registrable to) the IFC frame."""
    from scipy.spatial import cKDTree
    buf = float(params.get("match_radius_m", 1.0))
    tol = float(params.get("coverage_tolerance_m", 0.10))
    p = apply_registration(sample_pts, scale, matrix)
    ilo, ihi = np.array(ifc_bounds[0]), np.array(ifc_bounds[1])
    inside = np.all((p >= ilo - buf) & (p <= ihi + buf), axis=1)
    res: dict[str, Any] = {
        "file": name, "status": "computed", "alignment_basis": basis, "unit_scale_to_m": scale,
        "sampled_points_used": int(len(p)), "source_point_count": point_count,
        "overlap": {"fraction_of_cloud_sample_within_ifc_bbox_plus_%sm" % buf: float(inside.mean())},
        "vertical": {"cloud_z_range_m": [float(p[:, 2].min()), float(p[:, 2].max())],
                     "ifc_z_range_m": [float(ilo[2]), float(ihi[2])],
                     "cloud_z_p05_p95_m": [float(np.percentile(p[:, 2], 5)), float(np.percentile(p[:, 2], 95))]},
    }
    cl_lo, cl_hi = p.min(0), p.max(0)
    inter = np.maximum(0, np.minimum(ihi, cl_hi) - np.maximum(ilo, cl_lo))
    res["overlap"]["bbox_intersection_volume_over_ifc_bbox_volume"] = float(np.prod(inter) / max(np.prod(ihi - ilo), 1e-12))
    if inside.sum() < 100:
        res["status"] = "insufficient_overlap"
        res["note"] = "fewer than 100 sampled cloud points fall near the IFC bounding box; distances not computed"
        return res
    surf = surface_samples(ifc_meshes, float(params.get("surface_sample_spacing_m", 0.05)),
                           int(params.get("max_surface_samples", 1_500_000)))
    tree = cKDTree(surf)
    d, _ = tree.query(p[inside], k=1)
    res["point_to_surface"] = {**_stats(d), "points_considered": int(inside.sum()),
                               "fraction_within_%gm" % tol: float((d <= tol).mean()),
                               "reference": "nearest-sample distance to sampled IfcSpace surfaces (spacing %.3f m; "
                                            "distances are upper-biased by up to ~spacing/2)" % float(params.get("surface_sample_spacing_m", 0.05))}
    ctree = cKDTree(p[inside])
    dc, _ = ctree.query(surf, k=1)
    res["coverage"] = {"fraction_of_ifc_surface_samples_with_cloud_point_within_%gm" % tol: float((dc <= tol).mean()),
                       "ifc_surface_samples": int(len(surf)),
                       "note": "cloud is a subsample, so coverage is a lower bound"}
    return res
