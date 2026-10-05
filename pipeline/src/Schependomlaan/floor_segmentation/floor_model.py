"""Storey segmentation: building -> storeys with elevation and (measured) vertical extent."""
from __future__ import annotations

from typing import Any


def build_floor_records(graph: dict[str, Any], classification: dict[str, Any],
                        space_geom: dict[str, Any] | None) -> dict[str, Any]:
    geom = {r["space_global_id"]: r for r in (space_geom or {}).get("spaces", [])
            if r["geometry_status"] != "unavailable"}
    cls = {c["space_global_id"]: c for c in classification["spaces"]}
    storeys = sorted(graph["storeys"], key=lambda s: (s["elevation_m"] is None, s["elevation_m"] or 0.0))
    records = []
    for i, st in enumerate(storeys):
        members = [s for s in graph["spaces"] if s["storey_id"] == st["global_id"]]
        measured = [geom[m["global_id"]] for m in members if m["global_id"] in geom]
        elev = st["elevation_m"]
        nxt = next((s["elevation_m"] for s in storeys[i + 1:] if s["elevation_m"] is not None), None)
        nominal_h = (nxt - elev) if (nxt is not None and elev is not None) else None
        warnings: list[str] = []
        if measured:
            zmin = min(r["z_min"] for r in measured)
            zmax = max(r["z_max"] for r in measured)
            z_source = "measured_space_geometry"
            if elev is not None and abs(zmin - elev) > 0.5:
                warnings.append(f"measured z_min {zmin:.3f} m differs from IFC storey elevation {elev:.3f} m "
                                "(possible different datum/placement; both retained)")
        else:
            zmin = elev
            zmax = nxt
            z_source = "nominal_ifc_elevation"
            if members:
                warnings.append("storey has spaces but none with geometry; z-extent is nominal")
        func = sorted({cls[m["global_id"]]["classification"] for m in members if m["global_id"] in cls})
        records.append({
            "storey_id": st["global_id"], "name": st["name"], "building_id": st["building_id"],
            "order_index": i, "elevation_m": elev,
            "z_min": zmin, "z_max": zmax,
            "height_m": (zmax - zmin) if (zmin is not None and zmax is not None) else None,
            "nominal_height_m": nominal_h, "z_source": z_source,
            "space_count": len(members), "space_ids": [m["global_id"] for m in members],
            "space_classes": func, "measured_space_count": len(measured),
            "vertical_reference": "IFC local datum (not verified against NAP)",
            "warnings": warnings,
        })
    return {"source_mode": graph["source_mode"], "method": "ifc_spatial_structure+geometry",
            "storey_count": len(records), "storeys": records}
