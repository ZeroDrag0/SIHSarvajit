"""Build 3D geometry for property units from constituent IfcSpace volumes."""
from __future__ import annotations

from typing import Any

import numpy as np
import trimesh
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

_RANK = {"valid": 0, "fallback": 1, "non_watertight": 2, "invalid": 3, "unavailable": 4}


def build_unit_geometry(unit: dict[str, Any], space_geom: dict[str, dict], meshes: dict[str, trimesh.Trimesh]) -> tuple[dict, trimesh.Trimesh | None]:
    ids = unit["source_space_ids"]
    recs = [space_geom[i] for i in ids if i in space_geom and space_geom[i]["geometry_status"] != "unavailable"]
    missing = [i for i in ids if i not in space_geom or space_geom[i]["geometry_status"] == "unavailable"]
    if not recs:
        return ({"geometry_status": "unavailable", "representation": None, "constituent_count": 0,
                 "missing_constituents": missing, "notes": ["no constituent geometry available"]}, None)

    status = max((r["geometry_status"] for r in recs), key=lambda s: _RANK[s])
    notes: list[str] = []
    if missing:
        notes.append(f"{len(missing)} constituent space(s) had no geometry; unit volume is a lower bound")
    parts = [meshes[r["space_global_id"]] for r in recs if r["space_global_id"] in meshes]
    fps = [shape(r["footprint"]) for r in recs if r.get("footprint")]
    footprint = unary_union(fps) if fps else None

    union_mesh = None
    union_status = "single_constituent" if len(parts) == 1 else "not_attempted"
    all_wt = all(p.is_watertight for p in parts)
    if len(parts) > 1 and all_wt:
        try:
            union_mesh = trimesh.boolean.union(parts, engine="manifold")
            union_status = "boolean_union_ok" if union_mesh is not None and len(union_mesh.faces) else "union_failed"
        except Exception as exc:  # noqa: BLE001
            union_status = f"union_failed: {type(exc).__name__}"
    elif len(parts) > 1:
        union_status = "union_skipped_non_watertight_constituent"
    if len(parts) == 1:
        union_mesh = parts[0]

    sum_vol = float(sum(r["volume_m3"] for r in recs))
    if union_mesh is not None and union_mesh.is_watertight:
        representation = "boolean_union" if len(parts) > 1 else "single_space_mesh"
        volume = float(union_mesh.volume)
        area = float(union_mesh.area)
        out_mesh = union_mesh
        if len(parts) > 1 and abs(volume - sum_vol) > 0.02 * max(sum_vol, 1e-9):
            notes.append(f"union volume {volume:.3f} differs from sum of rooms {sum_vol:.3f} (overlapping rooms?)")
    else:
        representation = "constituent_meshes"
        volume = sum_vol
        area = float(sum(r["surface_area_m2"] for r in recs))
        out_mesh = trimesh.util.concatenate(parts) if parts else None
        notes.append("union not available; constituent room meshes preserved (surface area includes shared faces)")

    # --- unit-level provenance / confidence (volume-weighted over constituent spaces) -------------
    vols = np.array([max(r["volume_m3"], 1e-9) for r in recs])
    confs = np.array([r.get("confidence") or 0.0 for r in recs])
    n_fb = sum(1 for r in recs if r.get("is_fallback"))
    n_body = sum(1 for r in recs if r.get("is_fallback") is False)
    conf = float(min((confs * vols).sum() / vols.sum(), 1.0))
    if missing:
        conf *= 1 - len(missing) / len(ids)
    if representation != "boolean_union" and representation != "single_space_mesh":
        conf *= 0.9
    corr_states = [r.get("boundary_corroboration", {}).get("status") for r in recs]
    zmin = min(r["z_min"] for r in recs)
    zmax = max(r["z_max"] for r in recs)
    wts = np.array([max(r["volume_m3"], 1e-9) for r in recs])
    cen = (np.array([r["centroid"] for r in recs]) * wts[:, None]).sum(0) / wts.sum()
    return ({
        "geometry_status": status, "representation": representation, "union_status": union_status,
        "constituent_count": len(recs), "missing_constituents": missing,
        "z_min": zmin, "z_max": zmax, "height_m": zmax - zmin, "vertical_extent_m": zmax - zmin,
        "volume_m3": volume, "surface_area_m2": area, "centroid": cen.tolist(),
        "footprint_area_m2": float(footprint.area) if footprint is not None else None,
        "footprint": mapping(footprint) if footprint is not None and not footprint.is_empty else None,
        "footprint_note": "union of net room footprints (internal wall thickness not filled)",
        "volume_note": "net internal volume of constituent IfcSpace volumes",
        "geometry_source": ("ifc_body_mesh only" if n_fb == 0 else
                            "mixed: %d IfcSpace Body solid(s) + %d IfcSpace FootPrint/Box extrusion(s)" % (n_body, n_fb)
                            if n_body else "IfcSpace FootPrint curve + Box height extrusions (no Body solids)"),
        "is_fallback": n_fb > 0,
        "fallback_space_count": n_fb, "body_space_count": n_body,
        "fallback_note": ("constituent spaces without an IFC Body were extruded from the IFC FootPrint curve and "
                          "Box height (real IFC data, placed with real ObjectPlacement; marked fallback)") if n_fb else None,
        "confidence": round(conf, 4),
        "confidence_note": "volume-weighted rule-based heuristic score, not a statistical probability",
        "boundary_corroboration_summary": {k: corr_states.count(k) for k in set(corr_states)},
        "watertight": bool(out_mesh.is_watertight) if out_mesh is not None else None,
        "mesh_vertex_count": int(len(out_mesh.vertices)) if out_mesh is not None else 0,
        "mesh_face_count": int(len(out_mesh.faces)) if out_mesh is not None else 0,
        "sum_of_room_volumes_m3": sum_vol,
        "notes": notes,
    }, out_mesh)
