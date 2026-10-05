"""Per-IfcSpace 3D geometry extraction.

Order of attempts (the method used is always recorded):
 1. ifcopenshell triangulation of the Body representation, in world coordinates (method=ifc_body_mesh)
 2. FootPrint curve + Box height, placed with the real ObjectPlacement (method=footprint_box_extrusion,
    status=fallback)
 3. nothing -> status=unavailable (no invented geometry)
No mesh repair beyond vertex merging is performed; non-watertight meshes are reported as such.

Every record carries `geometry_source`, `is_fallback`, `confidence` (rule-based heuristic score in [0,1], NOT a
statistical probability) and `boundary_corroboration`: an independent comparison against the IFC 2nd-level
IfcRelSpaceBoundary surfaces of the same space (bbox / z-range / floor area).  The boundary shells are used only as
evidence - they are not watertight and are never substituted for the space volume.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import trimesh
from shapely.geometry import MultiPolygon, Polygon, mapping
from shapely.ops import unary_union

TOL = 1e-6


def _world_settings():
    import ifcopenshell.geom as g
    s = g.settings()
    for key in ("use-world-coords", "USE_WORLD_COORDS"):
        try:
            s.set(key, True)
            return s
        except Exception:
            try:
                s.set(getattr(s, key), True)
                return s
            except Exception:
                continue
    return s


def mesh_footprint(mesh: trimesh.Trimesh) -> Polygon | MultiPolygon:
    tris = mesh.vertices[mesh.faces]
    nz = np.abs(mesh.face_normals[:, 2])
    polys = []
    for t, n in zip(tris, nz):
        if n < 0.5:
            continue
        p = Polygon(t[:, :2])
        if p.area > 1e-9:
            polys.append(p if p.is_valid else p.buffer(0))
    if not polys:
        return Polygon()
    return unary_union(polys)


def _curve_points(curve, scale: float) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    if curve.is_a("IfcPolyline"):
        pts = [(float(p.Coordinates[0]) * scale, float(p.Coordinates[1]) * scale) for p in curve.Points]
    elif curve.is_a("IfcIndexedPolyCurve"):
        coords = curve.Points.CoordList
        pts = [(float(c[0]) * scale, float(c[1]) * scale) for c in coords]
    return pts


def _footprint_polygon(space, scale: float) -> Polygon | None:
    rep = getattr(space, "Representation", None)
    if rep is None:
        return None
    for r in rep.Representations or []:
        if r.RepresentationIdentifier != "FootPrint" and r.RepresentationType not in ("FootPrint", "Curve2D"):
            continue
        for item in r.Items or []:
            curves = list(item.Elements) if item.is_a("IfcGeometricCurveSet") else [item]
            for c in curves:
                pts = _curve_points(c, scale) if hasattr(c, "is_a") else []
                if len(pts) >= 3:
                    poly = Polygon(pts)
                    return poly if poly.is_valid else None
    return None


def _box_extent(space, scale: float) -> tuple[float, float] | None:
    """Return (z_offset, height) in metres from an IfcBoundingBox representation."""
    rep = getattr(space, "Representation", None)
    if rep is None:
        return None
    for r in rep.Representations or []:
        if r.RepresentationIdentifier == "Box" or r.RepresentationType == "BoundingBox":
            for it in r.Items or []:
                if it.is_a("IfcBoundingBox"):
                    corner_z = float(it.Corner.Coordinates[2]) * scale if len(it.Corner.Coordinates) > 2 else 0.0
                    return corner_z, float(it.ZDim) * scale
    return None


def _placement_matrix(space, scale: float) -> np.ndarray:
    import ifcopenshell.util.placement as pl
    m = np.array(pl.get_local_placement(space.ObjectPlacement), dtype=float)
    m[:3, 3] *= scale
    return m


def _record_from_mesh(mesh: trimesh.Trimesh, status_hint: str | None) -> dict[str, Any]:
    mesh.merge_vertices()
    mesh.remove_unreferenced_vertices()
    notes: list[str] = []
    wt = bool(mesh.is_watertight)
    consistent = bool(mesh.is_winding_consistent)
    vol = float(mesh.volume) if wt else 0.0
    if len(mesh.faces) == 0:
        status = "invalid"
    elif wt and consistent and vol > TOL:
        status = "valid"
    elif wt and vol <= TOL:
        status = "invalid"
        notes.append("zero or negative volume (possible inverted normals)")
    else:
        status = "non_watertight"
    if status_hint == "fallback" and status == "valid":
        status = "fallback"
    b = mesh.bounds
    fp = mesh_footprint(mesh)
    return {
        "geometry_status": status, "vertex_count": int(len(mesh.vertices)), "face_count": int(len(mesh.faces)),
        "watertight": wt, "winding_consistent": consistent,
        "volume_m3": vol, "surface_area_m2": float(mesh.area),
        "z_min": float(b[0][2]), "z_max": float(b[1][2]), "height_m": float(b[1][2] - b[0][2]),
        "bounds": b.tolist(), "centroid": mesh.centroid.tolist(),
        "footprint_area_m2": float(fp.area), "footprint": mapping(fp) if not fp.is_empty else None,
        "notes": notes,
    }


XY_TOL_M = 0.05      # bbox agreement tolerance used for corroboration
Z_TOL_M = 0.05


def build_boundary_index(model) -> dict[str, list]:
    """IfcRelSpaceBoundary entities grouped by RelatingSpace GlobalId (empty when the model has none)."""
    by: dict[str, list] = defaultdict(list)
    for r in model.by_type("IfcRelSpaceBoundary"):
        sp = getattr(r, "RelatingSpace", None)
        if sp is not None and sp.is_a("IfcSpace"):
            by[sp.GlobalId].append(r)
    return by


def boundary_shell(space, rels, scale: float) -> tuple[trimesh.Trimesh | None, dict[str, Any]]:
    """Triangulate the planar space-boundary surfaces of one space into world metres.

    IfcOpenShell triangulates an IfcCurveBoundedPlane in the plane's local frame, so the plane Position and
    the space ObjectPlacement are applied explicitly here.
    """
    import ifcopenshell.geom as g
    import ifcopenshell.util.placement as pl
    st = g.settings()
    M = np.array(pl.get_local_placement(space.ObjectPlacement), dtype=float)
    V, F, off, skipped = [], [], 0, 0
    for r in rels:
        try:
            surf = r.ConnectionGeometry.SurfaceOnRelatingElement
            if not surf.is_a("IfcCurveBoundedPlane"):
                skipped += 1
                continue
            sh = g.create_shape(st, surf)
            v = np.asarray(sh.geometry.verts if hasattr(sh, "geometry") else sh.verts, dtype=float).reshape(-1, 3)
            f = np.asarray(sh.geometry.faces if hasattr(sh, "geometry") else sh.faces, dtype=int).reshape(-1, 3)
            P = np.array(pl.get_axis2placement(surf.BasisSurface.Position), dtype=float)
            v = (P[:3, :3] @ v.T).T + P[:3, 3]
            v = (M[:3, :3] @ v.T).T + M[:3, 3]
            V.append(v * scale)
            F.append(f + off)
            off += len(v)
        except Exception:  # noqa: BLE001
            skipped += 1
    info = {"boundary_count": len(rels), "surfaces_used": len(V), "surfaces_skipped": skipped}
    if not V:
        return None, info
    return trimesh.Trimesh(np.vstack(V), np.vstack(F), process=False), info


def corroborate(rec: dict[str, Any], shell: trimesh.Trimesh | None, info: dict[str, Any]) -> dict[str, Any]:
    """Compare a space geometry record with its own boundary shell (independent IFC evidence)."""
    if shell is None or "bounds" not in rec:
        return {"status": "no_boundaries", **info}
    b = shell.bounds
    fb = np.asarray(rec["bounds"], dtype=float)
    dxy = float(max(np.abs(b[0][:2] - fb[0][:2]).max(), np.abs(b[1][:2] - fb[1][:2]).max()))
    dzmin, dzmax = float(b[0][2] - fb[0][2]), float(b[1][2] - fb[1][2])
    with np.errstate(all="ignore"):
        nz = shell.face_normals[:, 2]
        cz = shell.vertices[shell.faces][:, :, 2].mean(1)
        areas = shell.area_faces
    floor = (np.abs(nz) > 0.95) & (cz < b[0][2] + Z_TOL_M)
    floor_area = float(np.nansum(areas[floor]))
    fp_area = rec.get("footprint_area_m2")
    xy_ok = dxy <= XY_TOL_M
    z_ok = abs(dzmin) <= Z_TOL_M and abs(dzmax) <= Z_TOL_M
    status = "corroborated" if (xy_ok and z_ok) else ("partially_corroborated" if xy_ok else "deviates")
    return {"status": status, **info, "shell_bounds": b.tolist(), "xy_bbox_max_deviation_m": round(dxy, 4),
            "z_min_deviation_m": round(dzmin, 4), "z_max_deviation_m": round(dzmax, 4),
            "floor_boundary_area_m2": round(floor_area, 4),
            "floor_area_ratio_vs_footprint": round(floor_area / fp_area, 4) if fp_area else None,
            "tolerances_m": {"xy": XY_TOL_M, "z": Z_TOL_M}}


def _confidence(method: str | None, geo_status: str, corr: dict[str, Any]) -> tuple[float, str]:
    c = corr.get("status")
    if method == "ifc_body_mesh":
        if geo_status != "valid":
            return 0.5, "IFC Body triangulated but mesh is not a valid closed solid"
        return ((0.95, "IFC Body solid; corroborated by space boundaries") if c == "corroborated" else
                (0.85, "IFC Body solid; no/partial boundary corroboration"))
    if method == "footprint_box_extrusion":
        return {"corroborated": (0.85, "IFC FootPrint+Box extrusion; bbox and z agree with space boundaries"),
                "partially_corroborated": (0.7, "IFC FootPrint+Box extrusion; xy agrees with space boundaries, z differs"),
                "deviates": (0.45, "IFC FootPrint+Box extrusion; disagrees with space boundaries"),
                }.get(c, (0.5, "IFC FootPrint+Box extrusion; no space boundaries to corroborate"))
    return 0.0, "no geometry"


def _storey_of(space) -> tuple[str | None, str | None]:
    for rel in getattr(space, "Decomposes", None) or []:
        o = getattr(rel, "RelatingObject", None)
        if o is not None and o.is_a("IfcBuildingStorey"):
            return o.GlobalId, o.Name
    for rel in getattr(space, "ContainedInStructure", None) or []:
        o = getattr(rel, "RelatingStructure", None)
        if o is not None and o.is_a("IfcBuildingStorey"):
            return o.GlobalId, o.Name
    return None, None


def _annotate(rec: dict[str, Any], space, method: str, rels) -> None:
    """Add provenance, storey, boundary corroboration and confidence to a geometry record."""
    shell, info = (boundary_shell(space, rels, rec.get("_scale", 1.0)) if rels else (None, {"boundary_count": 0}))
    corr = corroborate(rec, shell, info)
    conf, basis = _confidence(method, rec["geometry_status"], corr)
    reps = [(r.RepresentationIdentifier, r.RepresentationType) for r in (space.Representation.Representations if space.Representation else [])]
    sid, sname = _storey_of(space)
    rec.update({
        "geometry_source": ("IfcSpace.Body (SweptSolid) triangulated by IfcOpenShell" if method == "ifc_body_mesh"
                            else "IfcSpace.FootPrint curve extruded by IfcSpace.Box height, placed with ObjectPlacement"),
        "is_fallback": method != "ifc_body_mesh",
        "confidence": conf, "confidence_basis": basis,
        "confidence_note": "rule-based heuristic score, not a statistical probability",
        "boundary_corroboration": corr, "ifc_representations": reps,
        "storey_global_id": sid, "storey_name": sname,
    })
    rec.pop("_scale", None)


def extract_space_geometry(space, scale: float, settings=None, boundary_rels=None) -> tuple[dict[str, Any], trimesh.Trimesh | None]:
    import ifcopenshell.geom as g
    base = {"space_global_id": space.GlobalId, "space_name": space.Name}
    body_error = None
    try:
        settings = settings or _world_settings()
        shape = g.create_shape(settings, space)
        geo = shape.geometry
        v = np.asarray(geo.verts, dtype=float).reshape(-1, 3)
        f = np.asarray(geo.faces, dtype=int).reshape(-1, 3)
        if len(v) and len(f):
            mesh = trimesh.Trimesh(vertices=v, faces=f, process=False)
            rec = _record_from_mesh(mesh, None)
            rec.update(base, method="ifc_body_mesh", coordinate_frame="ifc_world_metres", _scale=scale)
            _annotate(rec, space, "ifc_body_mesh", boundary_rels)
            return rec, mesh
        body_error = "empty triangulation"
    except Exception as exc:  # noqa: BLE001
        body_error = f"{type(exc).__name__}: {exc}"

    # --- fallback: footprint + bounding box height, correctly placed -------
    try:
        poly = _footprint_polygon(space, scale)
        box = _box_extent(space, scale)
        if poly is not None and box is not None and box[1] > TOL:
            mesh = trimesh.creation.extrude_polygon(poly, height=box[1])
            mesh.apply_translation([0, 0, box[0]])
            mesh.apply_transform(_placement_matrix(space, scale))
            rec = _record_from_mesh(mesh, "fallback")
            rec.update(base, method="footprint_box_extrusion", coordinate_frame="ifc_world_metres",
                       body_error=body_error, _scale=scale)
            _annotate(rec, space, "footprint_box_extrusion", boundary_rels)
            rec["notes"].append("fallback: IfcSpace has no usable Body; extruded from its FootPrint curve and "
                                "Box height, placed with ObjectPlacement")
            return rec, mesh
        reason = "no FootPrint curve" if poly is None else "no Box height"
    except Exception as exc:  # noqa: BLE001
        reason = f"fallback failed: {type(exc).__name__}: {exc}"
    return ({**base, "geometry_status": "unavailable", "method": None, "body_error": body_error,
             "fallback_error": reason, "geometry_source": None, "is_fallback": None, "confidence": 0.0,
             "notes": ["no geometry could be derived; nothing was invented"]}, None)


def extract_all_space_geometry(ifc_path: str | Path) -> tuple[dict[str, Any], dict[str, trimesh.Trimesh]]:
    import ifcopenshell
    model = ifcopenshell.open(str(ifc_path))
    from Schependomlaan.preprocessing.ifc_graph import _scale_to_metres
    scale = _scale_to_metres(model)
    settings = _world_settings()
    records, meshes = [], {}
    bidx = build_boundary_index(model)
    for sp in model.by_type("IfcSpace"):
        rec, mesh = extract_space_geometry(sp, scale, settings, bidx.get(sp.GlobalId))
        records.append(rec)
        if mesh is not None:
            meshes[sp.GlobalId] = mesh
    n = len(records)
    ok = sum(1 for r in records if r["geometry_status"] != "unavailable")
    return ({
        "source_file": str(Path(ifc_path).resolve()), "length_scale_to_metre": scale,
        "coordinate_frame": "ifc_world_metres (local/unverified)",
        "summary": {"space_count": n, "geometry_extracted": ok,
                    "success_rate": round(ok / n, 4) if n else None,
                    "by_status": _count(r["geometry_status"] for r in records),
                    "by_method": _count(str(r.get("method")) for r in records),
                    "real_body_geometry": sum(1 for r in records if r.get("is_fallback") is False),
                    "fallback_geometry": sum(1 for r in records if r.get("is_fallback") is True),
                    "boundary_corroboration": _count(r.get("boundary_corroboration", {}).get("status", "n/a") for r in records),
                    "mean_confidence": round(sum(r.get("confidence", 0) for r in records) / n, 4) if n else None,
                    "space_boundaries_in_model": sum(len(v) for v in bidx.values())},
        "spaces": records,
    }, meshes)


def _count(it) -> dict[str, int]:
    out: dict[str, int] = {}
    for x in it:
        out[x] = out.get(x, 0) + 1
    return out


def save_meshes(meshes: dict[str, trimesh.Trimesh], path: str | Path) -> None:
    arrs = {}
    for gid, m in meshes.items():
        arrs[f"v::{gid}"] = np.asarray(m.vertices)
        arrs[f"f::{gid}"] = np.asarray(m.faces)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **arrs)


def load_meshes(path: str | Path) -> dict[str, trimesh.Trimesh]:
    p = Path(path)
    if not p.exists():
        return {}
    z = np.load(p, allow_pickle=False)
    out = {}
    for k in z.files:
        if k.startswith("v::"):
            gid = k[3:]
            out[gid] = trimesh.Trimesh(vertices=z[k], faces=z[f"f::{gid}"], process=False)
    return out
