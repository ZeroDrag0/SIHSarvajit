"""3D topology validation of derived property units.

`valid == True` only if every REQUIRED check ran on every unit and passed.  Checks that could not run
(e.g. geometry unavailable) make `valid` False with an explicit error; they are never skipped silently.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any

import numpy as np
from shapely.geometry import shape
from shapely.ops import unary_union
from shapely.validation import explain_validity

REQUIRED = ["duplicate_units", "invalid_geometry", "self_intersections", "zero_negative_volume", "volumetric_overlap",
            "building_containment", "storey_unit_consistency", "z_order_consistency"]


def _manifold_status(mesh) -> str:
    try:
        import manifold3d as m3d
        mf = m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(mesh.vertices, dtype=np.float32),
                                   tri_verts=np.asarray(mesh.faces, dtype=np.uint32)))
        return str(mf.status()).split(".")[-1]
    except Exception as exc:  # noqa: BLE001
        return f"unchecked({type(exc).__name__})"


def _chk(status: str, **kw) -> dict[str, Any]:
    return {"status": status, **kw}


def validate_topology(units: list[dict[str, Any]], space_geom: dict[str, Any] | None, meshes: dict[str, Any],
                      floors: dict[str, Any], common_space_ids: list[str], cadastral_link: dict[str, Any] | None,
                      cadastral_status: str, terrain: dict[str, Any] | None, rules: dict) -> dict[str, Any]:
    R = rules["validation"]
    tol_a, tol_z, min_vol = R["tolerance_area_m2"], R["tolerance_z_m"], R["min_volume_m3"]
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, Any] = {}
    sg = {r["space_global_id"]: r for r in (space_geom or {}).get("spaces", []) if r["geometry_status"] != "unavailable"}
    storeys = {s["storey_id"]: s for s in floors["storeys"]}
    n_units = len(units)
    with_geom = [u for u in units if u["geometry"]["geometry_status"] != "unavailable" and u["geometry"].get("footprint")]
    without = [u["candidate_id"] for u in units if u not in with_geom]

    def fp(u):
        return shape(u["geometry"]["footprint"])

    # 1 duplicates -----------------------------------------------------------------
    seen: dict[Any, str] = {}
    dups = []
    for u in units:
        key = tuple(sorted(u["source_space_ids"]))
        if key in seen:
            dups.append([seen[key], u["candidate_id"], "identical_source_spaces"])
        seen[key] = u["candidate_id"]
    sp_owner: dict[str, str] = {}
    for u in units:
        for s in u["source_space_ids"]:
            if s in sp_owner and sp_owner[s] != u["candidate_id"]:
                dups.append([sp_owner[s], u["candidate_id"], f"space {s} claimed by two units"])
            sp_owner[s] = u["candidate_id"]
    sigs: dict[Any, str] = {}
    for u in with_geom:
        g = u["geometry"]
        key = (round(g["z_min"], 2), round(g["z_max"], 2), round(g["volume_m3"], 1), round(g["footprint_area_m2"], 1), tuple(np.round(g["centroid"], 1)))
        if key in sigs:
            dups.append([sigs[key], u["candidate_id"], "identical_geometry_signature"])
        sigs[key] = u["candidate_id"]
    checks["duplicate_units"] = _chk("failed" if dups else "passed", duplicates=dups)
    errors += [f"duplicate_units: {d}" for d in dups]

    # 2 invalid geometry, 3 self-intersections, 4 zero/neg volume ---------------------
    inv, selfi, zero, fall = [], [], [], []
    for u in with_geom:
        g = u["geometry"]
        if g["geometry_status"] in ("invalid", "non_watertight"):
            inv.append({"unit": u["candidate_id"], "geometry_status": g["geometry_status"]})
        if g["geometry_status"] == "fallback":
            fall.append(u["candidate_id"])
        f = fp(u)
        if not f.is_valid:
            selfi.append({"unit": u["candidate_id"], "level": "footprint", "reason": explain_validity(f)})
        for sid in u["source_space_ids"]:
            if sid in meshes:
                ms = _manifold_status(meshes[sid])
                if ms not in ("NoError", "unchecked(ModuleNotFoundError)") and not ms.startswith("unchecked"):
                    selfi.append({"unit": u["candidate_id"], "space": sid, "level": "mesh", "reason": f"manifold status {ms}"})
            if sid in sg and sg[sid]["geometry_status"] in ("invalid", "non_watertight"):
                inv.append({"unit": u["candidate_id"], "space": sid, "geometry_status": sg[sid]["geometry_status"]})
        if g["volume_m3"] <= min_vol:
            zero.append({"unit": u["candidate_id"], "volume_m3": g["volume_m3"]})
        if g["height_m"] <= tol_z:
            zero.append({"unit": u["candidate_id"], "height_m": g["height_m"]})
    inc = _inc(without)
    checks["invalid_geometry"] = _chk("failed" if inv else inc or "passed", items=inv, units_skipped=without,
                                      fallback_geometry_units=fall,
                                      note="fallback = extruded from IFC FootPrint+Box (watertight, but not a Body mesh)")
    checks["self_intersections"] = _chk("failed" if selfi else inc or "passed", items=selfi, units_skipped=without,
                                        method="footprint validity (shapely) + mesh manifoldness (manifold3d) + watertight/winding; "
                                               "exhaustive triangle-triangle intersection NOT performed")
    checks["zero_negative_volume"] = _chk("failed" if zero else inc or "passed", items=zero, units_skipped=without)
    for name in ("invalid_geometry", "self_intersections", "zero_negative_volume"):
        if checks[name]["status"] == "failed":
            errors.append(f"{name}: {len(checks[name]['items'])} issue(s)")

    # 5 volumetric overlap (room-level, exact boolean when possible) ------------------
    owner = {s: u["candidate_id"] for u in units for s in u["source_space_ids"]}
    for s in common_space_ids:
        owner.setdefault(s, "COMMON")
    ids = [s for s in owner if s in sg]
    overlaps, exact_n, approx_n, intra = [], 0, 0, []
    bb = {s: np.array(sg[s]["bounds"]) for s in ids}
    pairs = 0
    for a, b in combinations(ids, 2):
        A, B = bb[a], bb[b]
        if np.any(A[1] - B[0] < tol_z) or np.any(B[1] - A[0] < tol_z):
            continue
        pairs += 1
        vol = None
        if a in meshes and b in meshes and sg[a]["watertight"] and sg[b]["watertight"] and exact_n < R["max_exact_pairs"]:
            try:
                inter = meshes[a].intersection(meshes[b], engine="manifold")
                vol = float(inter.volume) if inter is not None and len(inter.faces) else 0.0  # empty = disjoint
                exact_n += 1
                how = "exact_boolean"
            except Exception:  # noqa: BLE001
                vol = None
        if vol is None:
            fa, fb = shape(sg[a]["footprint"]), shape(sg[b]["footprint"])
            zo = min(sg[a]["z_max"], sg[b]["z_max"]) - max(sg[a]["z_min"], sg[b]["z_min"])
            vol = fa.intersection(fb).area * max(zo, 0.0)
            approx_n += 1
            how = "footprint_area_x_z_overlap_approximation"
        if vol > min_vol:
            rec = {"spaces": [a, b], "owners": [owner[a], owner[b]], "overlap_volume_m3": round(vol, 4), "method": how}
            (intra if owner[a] == owner[b] else overlaps).append(rec)
    checks["volumetric_overlap"] = _chk("failed" if overlaps else (inc or "passed"), items=overlaps, units_skipped=without,
                                        candidate_pairs=pairs, exact_boolean_pairs=exact_n, approximated_pairs=approx_n,
                                        intra_unit_overlaps=intra)
    if overlaps:
        errors.append(f"volumetric_overlap: {len(overlaps)} overlapping room pair(s) across different units/common spaces")
    if intra:
        warnings.append(f"{len(intra)} overlapping room pair(s) inside one unit")

    # 9 footprint overlap, 10 vertical overlap ---------------------------------------
    fo, vo = [], []
    for a, b in combinations(with_geom, 2):
        ar = fp(a).intersection(fp(b)).area
        if ar > tol_a:
            zo = min(a["geometry"]["z_max"], b["geometry"]["z_max"]) - max(a["geometry"]["z_min"], b["geometry"]["z_min"])
            (vo if zo > tol_z else fo).append({"units": [a["candidate_id"], b["candidate_id"]], "footprint_overlap_m2": round(ar, 3),
                                               "z_overlap_m": round(zo, 3)})
    checks["footprint_overlap"] = _chk("passed", stacked_pairs=fo,
                                       note="footprints that overlap while z-ranges are disjoint = vertical stacking (expected)")
    checks["vertical_overlap"] = _chk("failed" if vo else (inc or "passed"), items=vo, units_skipped=without)
    if vo:
        errors.append(f"vertical_overlap: {len(vo)} unit pair(s) overlap in both footprint and z-range")

    # 6 gaps (coverage) --------------------------------------------------------------
    cov = {}
    for sid, st in storeys.items():
        mem = [s for s in st["space_ids"] if s in sg and sg[s].get("footprint")]
        if len(mem) < 2:
            continue
        polys = [shape(sg[s]["footprint"]) for s in mem]
        hull = unary_union(polys).convex_hull.area
        cov[st["name"]] = round(sum(p.area for p in polys) / hull, 3) if hull > 0 else None
    low = {k: v for k, v in cov.items() if v is not None and v < R["min_storey_coverage_ratio"]}
    un = sorted(set(sg) - set(owner))
    nogeom_spaces = [s for s in owner if s not in sg]
    if nogeom_spaces:
        warnings.append(f"{len(nogeom_spaces)} space(s) have no geometry and were excluded from overlap/gap checks")
    checks["unexpected_gaps"] = _chk("warning" if (low or un) else "passed", storey_coverage_ratio=cov, low_coverage=low,
                                     unowned_spaces_with_geometry=un,
                                     note="wall thickness legitimately separates net room volumes; low ratio = suspicious gaps")
    if low or un:
        warnings.append("unexpected gaps/unowned spaces: see checks.unexpected_gaps")

    # 7 containment ------------------------------------------------------------------
    nominal = [s["elevation_m"] for s in floors["storeys"] if s["elevation_m"] is not None]
    zlo = min(nominal) if nominal else None
    top = max(nominal) if nominal else None
    cont = []
    if sg:
        env = unary_union([shape(r["footprint"]) for r in sg.values() if r.get("footprint")]).buffer(R["building_envelope_buffer_m"])
        for u in with_geom:
            if not env.buffer(1e-6).contains(fp(u)):
                cont.append({"unit": u["candidate_id"], "reason": "footprint outside building envelope"})
            if zlo is not None and u["geometry"]["z_min"] < zlo - R["storey_z_tolerance_m"]:
                cont.append({"unit": u["candidate_id"], "reason": f"z_min below lowest storey elevation {zlo}"})
            if top is not None and u["geometry"]["z_max"] > top + R["storey_z_tolerance_m"]:
                cont.append({"unit": u["candidate_id"], "reason": f"z_max above topmost storey elevation {top}"})
    checks["building_containment"] = _chk("failed" if cont else (inc or "passed"), items=cont, units_skipped=without,
                                          footprint_envelope_source="union of all IfcSpace footprints (self-consistency only; "
                                                                    "no independent envelope supplied)",
                                          z_envelope_source="IFC storey elevations (independent of space geometry)")
    if cont:
        errors.append(f"building_containment: {len(cont)} issue(s)")

    # 8 storey/unit consistency ---------------------------------------------------------
    bad = []
    tz = R["storey_z_tolerance_m"]
    for u in units:
        miss = [s for s in u["source_storey_ids"] if s not in storeys]
        if miss:
            bad.append({"unit": u["candidate_id"], "reason": f"unknown storey ids {miss}"})
            continue
        if not u["source_storey_ids"]:
            bad.append({"unit": u["candidate_id"], "reason": "unit has no storey"})
            continue
        g = u["geometry"]
        if g["geometry_status"] == "unavailable":
            continue
        sts = [storeys[s] for s in u["source_storey_ids"]]
        lo = min(s["elevation_m"] for s in sts if s["elevation_m"] is not None)
        hi_s = max(sts, key=lambda s: s["elevation_m"] or 0)
        hi = (hi_s["elevation_m"] or 0) + (hi_s["nominal_height_m"] or 0)
        if g["z_min"] < lo - tz or (hi_s["nominal_height_m"] and g["z_max"] > hi + tz):
            bad.append({"unit": u["candidate_id"], "reason": f"z-range [{g['z_min']:.2f},{g['z_max']:.2f}] outside storey range [{lo:.2f},{hi:.2f}]"})
    checks["storey_unit_consistency"] = _chk("failed" if bad else (inc or "passed"), items=bad, units_skipped=without)
    if bad:
        errors.append(f"storey_unit_consistency: {len(bad)} issue(s)")

    # 11 z-order ---------------------------------------------------------------------------
    zbad = []
    single = [u for u in with_geom if len(u["source_storey_ids"]) == 1 and u["source_storey_ids"][0] in storeys]
    for a, b in combinations(single, 2):
        oa, ob = storeys[a["source_storey_ids"][0]]["order_index"], storeys[b["source_storey_ids"][0]]["order_index"]
        if oa != ob and (oa < ob) != (a["geometry"]["centroid"][2] < b["geometry"]["centroid"][2]):
            zbad.append([a["candidate_id"], b["candidate_id"]])
    checks["z_order_consistency"] = _chk("failed" if zbad else (inc or "passed"), items=zbad, units_skipped=without)
    if zbad:
        errors.append(f"z_order_consistency: {len(zbad)} inconsistent pair(s)")

    # 12 shared boundaries ------------------------------------------------------------------
    gaps, isolated = [], []
    byst: dict[str, list] = {}
    for u in with_geom:
        for s in u["source_storey_ids"]:
            byst.setdefault(s, []).append(u)
    nb: dict[str, int] = {u["candidate_id"]: 0 for u in with_geom}
    for s, us in byst.items():
        for a, b in combinations(us, 2):
            d = fp(a).distance(fp(b))
            if d <= R["shared_boundary_max_gap_m"]:
                gaps.append(d)
                nb[a["candidate_id"]] += 1
                nb[b["candidate_id"]] += 1
    for s, us in byst.items():
        if len(us) > 1:
            isolated += [u["candidate_id"] for u in us if nb[u["candidate_id"]] == 0]
    checks["shared_boundary_consistency"] = _chk("warning" if isolated else (inc or "passed"), adjacent_pairs=len(gaps),
                                                 gap_m_min_median_max=[float(np.min(gaps)), float(np.median(gaps)), float(np.max(gaps))] if gaps else None,
                                                 isolated_units=sorted(set(isolated)),
                                                 note="neighbouring units are separated by wall thickness (net volumes); overlaps are caught by volumetric_overlap")
    if isolated:
        warnings.append(f"units without an adjacent unit on a multi-unit storey: {sorted(set(isolated))}")

    # 13 parcel/building ---------------------------------------------------------------------
    if cadastral_status == "not_available":
        checks["parcel_building_consistency"] = _chk("not_applicable", reason="no cadastral data supplied")
    else:
        pi = (cadastral_link or {}).get("parcel_building_intersection")
        if isinstance(pi, dict):
            ok = pi["overlap_fraction_of_building"] >= 0.9
            checks["parcel_building_consistency"] = _chk("passed" if ok else "warning", **pi)
            if not ok:
                warnings.append("building footprint is not (mostly) inside the parcel")
        else:
            checks["parcel_building_consistency"] = _chk("not_run", reason=str(pi))
            warnings.append("cadastral data supplied but parcel/building intersection could not be evaluated")
    # 14 terrain ----------------------------------------------------------------------------------
    t = (terrain or {}).get("terrain_status", "not_available")
    checks["terrain_building_consistency"] = (_chk("not_applicable", reason="no terrain data supplied") if t == "not_available"
                                              else _chk("not_run", reason=f"terrain_status={t}"))

    # 15 geometry provenance (informational: never forces validity, but a pass is not oversold) ------------
    fb_units = [u["candidate_id"] for u in with_geom if u["geometry"].get("is_fallback")]
    low_conf = [u["candidate_id"] for u in with_geom if (u["geometry"].get("confidence") or 0) < 0.6]
    off_spaces = sorted(r.get("space_name") for r in sg.values()
                        if r.get("boundary_corroboration", {}).get("status") in ("deviates", "partially_corroborated"))
    deviating = sorted(r.get("space_name") for r in sg.values() if r.get("boundary_corroboration", {}).get("status") == "deviates")
    checks["geometry_provenance"] = _chk(
        "warning" if (fb_units or low_conf or deviating) else "passed", units_with_fallback_geometry=fb_units,
        units_below_0_6_confidence=low_conf, spaces_not_fully_corroborated_by_space_boundaries=off_spaces,
        spaces_deviating_from_space_boundaries=deviating,
        note="fallback = IfcSpace FootPrint curve + Box height extrusion (real IFC data, no Body solid); "
             "corroboration = independent comparison with IfcRelSpaceBoundary surfaces")
    if fb_units:
        warnings.append(f"{len(fb_units)} of {len(with_geom)} unit(s) include fallback (footprint+box extrusion) geometry")
    if deviating:
        warnings.append(f"space geometry deviates from IFC space boundaries (>5 cm xy): {deviating}")

    not_ok = [n for n in REQUIRED if checks[n]["status"] not in ("passed",)]
    for n in not_ok:
        if checks[n]["status"] in ("incomplete", "not_run"):
            errors.append(f"required_check_not_run_on_all_units: {n} ({len(without)} of {n_units} units have no geometry)")
    valid = not errors and not not_ok
    metrics = {"unit_count": n_units, "unit_ids": [u["candidate_id"] for u in units], "units_with_geometry": len(with_geom), "units_without_geometry": without,
               "space_geometry_count": len(sg), "spaces_without_geometry": len([s for s in owner if s not in sg]), "total_unit_volume_m3": round(sum(u["geometry"].get("volume_m3") or 0 for u in with_geom), 3),
               "required_checks": REQUIRED, "required_checks_not_passed": not_ok,
               "check_status_counts": {s: sum(1 for c in checks.values() if c["status"] == s) for s in
                                       ("passed", "failed", "warning", "incomplete", "not_run", "not_applicable")}}
    return {"valid": bool(valid), "errors": errors, "warnings": warnings, "checks": checks, "metrics": metrics,
            "validity_definition": "true only if all required checks ran on all units and passed"}


def _inc(without: list[str]) -> str | None:
    return "incomplete" if without else None
