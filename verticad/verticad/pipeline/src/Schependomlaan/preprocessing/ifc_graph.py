"""IFC inspection: discovers the *actual* relationship graph of the file.

Nothing is assumed about IfcSpace.ContainedInStructure; every relationship type that can
place a space in the spatial hierarchy is collected and the parent is resolved from
whichever one is populated (reported per space, with all candidates).
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from Schependomlaan.classification.space_classifier import parse_space_name

REL_TYPES = [
    "IfcRelAggregates", "IfcRelContainedInSpatialStructure", "IfcRelSpaceBoundary",
    "IfcRelDefinesByProperties", "IfcRelDefinesByType", "IfcRelAssignsToGroup",
    "IfcRelReferencedInSpatialStructure", "IfcRelNests", "IfcRelVoidsElement",
]


def _scale_to_metres(model) -> float:
    try:
        import ifcopenshell.util.unit as u
        return float(u.calculate_unit_scale(model))
    except Exception:
        return 1.0


def _rep_summary(entity) -> list[dict[str, Any]]:
    out = []
    rep = getattr(entity, "Representation", None)
    if rep is None:
        return out
    for r in rep.Representations or []:
        out.append({
            "identifier": getattr(r, "RepresentationIdentifier", None),
            "type": getattr(r, "RepresentationType", None),
            "item_types": sorted({i.is_a() for i in (r.Items or [])}),
        })
    return out


def _placement_origin(entity, scale: float) -> list[float] | None:
    try:
        import ifcopenshell.util.placement as pl
        m = pl.get_local_placement(entity.ObjectPlacement)
        return [round(float(m[0][3]) * scale, 6), round(float(m[1][3]) * scale, 6), round(float(m[2][3]) * scale, 6)]
    except Exception:
        return None


def _flat_psets(entity) -> dict[str, dict[str, Any]]:
    try:
        import ifcopenshell.util.element as el
        psets = el.get_psets(entity)
    except Exception:
        return {}
    clean = {}
    for name, props in psets.items():
        clean[name] = {k: (v if isinstance(v, (str, int, float, bool, type(None))) else str(v))
                       for k, v in props.items() if k != "id"}
    return clean


def _georeferencing(model, scale: float) -> dict[str, Any]:
    info: dict[str, Any] = {"ifc_map_conversion": None, "ifc_projected_crs": None,
                            "site_reference": [], "contexts": []}
    for t, key in (("IfcMapConversion", "ifc_map_conversion"), ("IfcProjectedCRS", "ifc_projected_crs")):
        try:
            ents = model.by_type(t)
            if ents:
                e = ents[0]
                info[key] = {a: (v if isinstance(v, (str, int, float, bool, type(None))) else str(v))
                             for a, v in e.get_info(recursive=False).items() if a not in ("id", "type")}
        except RuntimeError:
            pass  # entity not in this schema (IFC2X3)
    for site in model.by_type("IfcSite"):
        info["site_reference"].append({
            "global_id": site.GlobalId, "name": site.Name,
            "ref_latitude": list(site.RefLatitude) if site.RefLatitude else None,
            "ref_longitude": list(site.RefLongitude) if site.RefLongitude else None,
            "ref_elevation": site.RefElevation,
            "placement_origin_m": _placement_origin(site, scale),
        })
    for ctx in model.by_type("IfcGeometricRepresentationContext"):
        if ctx.is_a("IfcGeometricRepresentationSubContext"):
            continue
        wcs = ctx.WorldCoordinateSystem
        info["contexts"].append({
            "context_type": ctx.ContextType,
            "world_origin": list(wcs.Location.Coordinates) if wcs is not None and wcs.Location else None,
            "true_north": list(ctx.TrueNorth.DirectionRatios) if ctx.TrueNorth else None,
        })
    verified = bool(info["ifc_map_conversion"] and info["ifc_projected_crs"])
    info["coordinate_status"] = "declared_in_ifc_unverified" if verified else "local/unverified"
    return info


def build_ifc_graph(ifc_path: str | Path) -> dict[str, Any]:
    import ifcopenshell
    path = Path(ifc_path).resolve()
    model = ifcopenshell.open(str(path))
    scale = _scale_to_metres(model)

    rel_counts = {t: len(model.by_type(t)) for t in REL_TYPES if _has(model, t)}

    # --- parent discovery (single pass per relationship type) -------------
    agg_parent: dict[str, list[str]] = defaultdict(list)
    cont_parent: dict[str, list[str]] = defaultdict(list)
    ref_parent: dict[str, list[str]] = defaultdict(list)
    for rel in model.by_type("IfcRelAggregates"):
        for child in rel.RelatedObjects:
            agg_parent[child.GlobalId].append(rel.RelatingObject.GlobalId)
    for rel in model.by_type("IfcRelContainedInSpatialStructure"):
        for child in rel.RelatedElements:
            cont_parent[child.GlobalId].append(rel.RelatingStructure.GlobalId)
    if _has(model, "IfcRelReferencedInSpatialStructure"):
        for rel in model.by_type("IfcRelReferencedInSpatialStructure"):
            for child in rel.RelatedElements:
                ref_parent[child.GlobalId].append(rel.RelatingStructure.GlobalId)

    by_gid = {e.GlobalId: e for t in ("IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace", "IfcZone")
              for e in model.by_type(t)}

    def kind(gid: str) -> str:
        return by_gid[gid].is_a() if gid in by_gid else "other"

    projects = model.by_type("IfcProject")
    buildings = []
    for b in model.by_type("IfcBuilding"):
        buildings.append({"global_id": b.GlobalId, "name": b.Name, "long_name": getattr(b, "LongName", None),
                          "parent": agg_parent.get(b.GlobalId, []),
                          "placement_origin_m": _placement_origin(b, scale)})
    storeys = []
    for s in model.by_type("IfcBuildingStorey"):
        parents = [p for p in agg_parent.get(s.GlobalId, []) if kind(p) == "IfcBuilding"]
        elev = getattr(s, "Elevation", None)
        storeys.append({
            "global_id": s.GlobalId, "name": s.Name, "long_name": getattr(s, "LongName", None),
            "elevation_m": None if elev is None else float(elev) * scale,
            "building_id": parents[0] if parents else (buildings[0]["global_id"] if buildings else None),
            "placement_origin_m": _placement_origin(s, scale),
        })
    storey_ids = {s["global_id"] for s in storeys}

    # --- space boundaries / zones / types --------------------------------
    boundaries: dict[str, list[dict]] = defaultdict(list)
    if _has(model, "IfcRelSpaceBoundary"):
        for rel in model.by_type("IfcRelSpaceBoundary"):
            sp = rel.RelatingSpace
            if sp is not None and sp.is_a("IfcSpace"):
                el = rel.RelatedBuildingElement
                boundaries[sp.GlobalId].append({
                    "element": el.GlobalId if el is not None else None,
                    "element_type": el.is_a() if el is not None else None,
                    "physical_or_virtual": rel.PhysicalOrVirtualBoundary,
                    "internal_or_external": rel.InternalOrExternalBoundary})
    zones = []
    zone_of: dict[str, list[str]] = defaultdict(list)
    if _has(model, "IfcRelAssignsToGroup"):
        for rel in model.by_type("IfcRelAssignsToGroup"):
            grp = rel.RelatingGroup
            if grp is not None and grp.is_a("IfcZone"):
                members = [o.GlobalId for o in rel.RelatedObjects if o.is_a("IfcSpace")]
                zones.append({"global_id": grp.GlobalId, "name": grp.Name, "space_ids": members})
                for m in members:
                    zone_of[m].append(grp.GlobalId)
    type_of: dict[str, str] = {}
    if _has(model, "IfcRelDefinesByType"):
        for rel in model.by_type("IfcRelDefinesByType"):
            for o in rel.RelatedObjects:
                type_of[o.GlobalId] = rel.RelatingType.Name or rel.RelatingType.is_a()

    # --- spaces -----------------------------------------------------------
    spaces = []
    for sp in model.by_type("IfcSpace"):
        gid = sp.GlobalId
        cands = {"aggregates": agg_parent.get(gid, []), "contained_in_spatial_structure": cont_parent.get(gid, []),
                 "referenced_in_spatial_structure": ref_parent.get(gid, [])}
        storey = None
        via = None
        for how in ("aggregates", "contained_in_spatial_structure", "referenced_in_spatial_structure"):
            for p in cands[how]:
                if p in storey_ids:
                    storey, via = p, how
                    break
            if storey:
                break
        parent_space = next((p for p in cands["aggregates"] if kind(p) == "IfcSpace"), None)
        spaces.append({
            "global_id": gid, "name": sp.Name, "long_name": getattr(sp, "LongName", None),
            "description": sp.Description, "object_type": sp.ObjectType,
            "predefined_type": getattr(sp, "PredefinedType", None),
            "interior_or_exterior": getattr(sp, "InteriorOrExteriorSpace", None),
            "storey_id": storey, "storey_resolved_via": via, "parent_candidates": cands,
            "parent_space": parent_space,
            "building_id": next((s["building_id"] for s in storeys if s["global_id"] == storey), None),
            "zones": zone_of.get(gid, []), "ifc_type_name": type_of.get(gid),
            "psets": _flat_psets(sp), "boundaries": boundaries.get(gid, []),
            "representations": _rep_summary(sp),
            "placement_origin_m": _placement_origin(sp, scale),
        })

    unit_info = {"length_scale_to_metre": scale}
    return {
        "source_mode": "live_ifc",
        "source_file": str(path),
        "schema": model.schema,
        "project": {"global_id": projects[0].GlobalId if projects else None,
                    "name": projects[0].Name if projects else None,
                    "description": projects[0].Description if projects else None},
        "units": unit_info,
        "relationship_counts": rel_counts,
        "entity_counts": Counter({t: len(model.by_type(t)) for t in
                                  ("IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace", "IfcZone",
                                   "IfcWall", "IfcSlab", "IfcDoor", "IfcWindow")}),
        "buildings": buildings, "storeys": storeys, "spaces": spaces, "zones": zones,
        "georeferencing": _georeferencing(model, scale),
    }


def _has(model, t: str) -> bool:
    try:
        model.by_type(t)
        return True
    except RuntimeError:
        return False


# ----------------------------------------------------------------------------
# Cached fallback: the earlier REAL inspection output (produced on the project machine)
# ----------------------------------------------------------------------------
def graph_from_legacy_inspection(legacy: dict[str, Any], source_path: str | None = None) -> dict[str, Any]:
    """Rebuild a *limited* graph from the previous inspect output.

    Only IfcRelAggregates parentage, names and nominal elevations survive in that file, so
    containment, zones, property sets, boundaries and geometry are reported as unavailable.
    """
    scale = 1.0
    for ua in legacy.get("ifc_units", []):
        for u in ua.get("units", []):
            if u.get("unit_type") == "LENGTHUNIT":
                scale = {"MILLI": 0.001, "CENTI": 0.01, None: 1.0}.get(u.get("prefix"), 1.0)
    b_id = legacy["buildings"][0]["ifc_global_id"] if legacy.get("buildings") else None
    return {
        "source_mode": "cached_legacy_inspection",
        "source_file": legacy.get("source_ifc"),
        "cache_file": source_path,
        "schema": legacy.get("schema"),
        "project": {"global_id": None, "name": legacy.get("project_name"), "description": None},
        "units": {"length_scale_to_metre": scale},
        "relationship_counts": {"IfcRelAggregates": "partial (cached)"},
        "entity_counts": {"IfcBuilding": legacy.get("building_count"), "IfcBuildingStorey": legacy.get("storey_count"),
                          "IfcSpace": legacy.get("space_count")},
        "buildings": [{"global_id": b["ifc_global_id"], "name": b["name"], "long_name": None, "parent": [],
                       "placement_origin_m": None} for b in legacy.get("buildings", [])],
        "storeys": [{"global_id": s["ifc_global_id"], "name": s["name"], "long_name": s.get("long_name"),
                     "elevation_m": None if s.get("elevation") is None else s["elevation"] * scale,
                     "building_id": b_id, "placement_origin_m": None} for s in legacy.get("storeys", [])],
        "spaces": [{"global_id": s["ifc_global_id"], "name": s["name"], "long_name": s.get("long_name"),
                    "description": None, "object_type": None, "predefined_type": None, "interior_or_exterior": None,
                    "storey_id": s.get("parent_storey"), "storey_resolved_via": "aggregates" if s.get("parent_storey") else None,
                    "parent_candidates": {"aggregates": [s["parent_storey"]] if s.get("parent_storey") else [],
                                          "contained_in_spatial_structure": "not_available_in_cache",
                                          "referenced_in_spatial_structure": "not_available_in_cache"},
                    "parent_space": None,
                    "building_id": b_id, "zones": [], "ifc_type_name": None, "psets": {}, "boundaries": [],
                    "representations": [{"identifier": s.get("representation_type"), "type": None, "item_types": []}],
                    "placement_origin_m": None,
                    "cached_geometry_summary": {k: s["geometry"].get(k) for k in ("extracted", "volume_m3", "bounds")}}
                   for s in legacy.get("spaces", [])],
        "zones": [],
        "georeferencing": {"coordinate_status": "local/unverified", "ifc_map_conversion": None,
                           "ifc_projected_crs": None, "site_reference": [], "contexts": []},
        "limitations": ["Built from a cached earlier inspection: containment, zones, property sets, space boundaries "
                        "and geometry were not recorded in that file. Re-run with the real IFC for full evidence."],
    }


# ----------------------------------------------------------------------------
# Output documents
# ----------------------------------------------------------------------------
def structure_document(graph: dict[str, Any]) -> dict[str, Any]:
    by_storey: dict[str | None, list[dict]] = defaultdict(list)
    for sp in graph["spaces"]:
        by_storey[sp["storey_id"]].append(sp)
    tree = []
    for b in graph["buildings"]:
        tree.append({
            "building": {"global_id": b["global_id"], "name": b["name"]},
            "storeys": [{
                "global_id": s["global_id"], "name": s["name"], "elevation_m": s["elevation_m"],
                "space_count": len(by_storey.get(s["global_id"], [])),
            } for s in graph["storeys"] if s["building_id"] == b["global_id"]],
        })
    res_via = Counter(sp["storey_resolved_via"] or "unresolved" for sp in graph["spaces"])
    return {
        "source_mode": graph["source_mode"], "source_file": graph["source_file"], "schema": graph["schema"],
        "project": graph["project"], "units": graph["units"],
        "entity_counts": dict(graph["entity_counts"]), "relationship_counts": graph["relationship_counts"],
        "spatial_tree": tree,
        "spaces_without_storey": len(by_storey.get(None, [])),
        "space_storey_resolution": dict(res_via),
        "zones": [{"name": z["name"], "space_count": len(z["space_ids"])} for z in graph["zones"]],
        "spaces_with_psets": sum(1 for s in graph["spaces"] if s["psets"]),
        "spaces_with_boundaries": sum(1 for s in graph["spaces"] if s["boundaries"]),
        "spaces_with_zones": sum(1 for s in graph["spaces"] if s["zones"]),
        "representation_types": dict(Counter(r["identifier"] for s in graph["spaces"] for r in s["representations"])),
        "georeferencing": graph["georeferencing"],
        "limitations": graph.get("limitations", []),
    }


def relationships_document(graph: dict[str, Any], rules: dict) -> dict[str, Any]:
    stor = {s["global_id"]: s for s in graph["storeys"]}
    bld = {b["global_id"]: b for b in graph["buildings"]}
    pat = rules["space_name"]["pattern"]
    rows = []
    for sp in graph["spaces"]:
        parsed = parse_space_name(sp["name"], pat)
        s = stor.get(sp["storey_id"])
        b = bld.get(sp["building_id"])
        rows.append({
            "space_global_id": sp["global_id"], "space_name": sp["name"], "long_name": sp["long_name"],
            "building": {"global_id": b["global_id"], "name": b["name"]} if b else None,
            "storey": {"global_id": s["global_id"], "name": s["name"], "elevation_m": s["elevation_m"]} if s else None,
            "candidate_property_group": parsed["group_key"] if parsed else None,
            "candidate_group_basis": "space_name_pattern" if parsed else "none",
            "storey_resolved_via": sp["storey_resolved_via"], "parent_candidates": sp["parent_candidates"],
            "zones": sp["zones"], "boundary_count": len(sp["boundaries"]), "pset_names": sorted(sp["psets"]),
        })
    return {"source_mode": graph["source_mode"], "space_count": len(rows), "relationships": rows}
