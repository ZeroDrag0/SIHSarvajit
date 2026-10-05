"""Deterministic PROTOTYPE 3D ULPIN generation. Not an official ULPIN."""
from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

SCHEME = "SIH-P3D-ULPIN/v1"
DISCLAIMER = "Prototype 3D cadastral identifier for demonstration only; NOT an official government ULPIN."


def canonical(identity: dict[str, Any]) -> str:
    return json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def encode(identity: dict[str, Any]) -> str:
    digest = hashlib.sha256(canonical(identity).encode()).digest()
    body = base64.b32encode(digest).decode().rstrip("=")[:16]
    chk = base64.b32encode(hashlib.sha256(body.encode()).digest()).decode()[:2]
    return "P3D-" + "-".join(body[i:i + 4] for i in range(0, 16, 4)) + "-" + chk


def geometry_version(unit: dict[str, Any]) -> str:
    g = unit["geometry"]
    if g["geometry_status"] == "unavailable" or not g.get("footprint"):
        basis = {"status": "unavailable", "source_ids": sorted(unit["source_space_ids"])}
    else:
        def r(x): return round(float(x), 3)
        def rr(o): return [rr(i) for i in o] if isinstance(o, (list, tuple)) else r(o)
        basis = {"z": [r(g["z_min"]), r(g["z_max"])], "vol": r(g["volume_m3"]), "fp": rr(g["footprint"]["coordinates"]),
                 "rep": g["representation"]}
    return "g1-" + hashlib.sha256(canonical(basis).encode()).hexdigest()[:12]


def generate_prototype_ulpins(units: list[dict[str, Any]], building_id: str | None, parcel_id: str | None,
                              cadastral_status: str, crs: dict[str, Any], validation: dict[str, Any],
                              storeys: dict[str, dict]) -> dict[str, Any]:
    records = []
    unit_ok = _unit_validation(validation)
    for u in units:
        st = u["source_storey_ids"]
        z = [None, None] if u["geometry"]["geometry_status"] == "unavailable" else [round(u["geometry"]["z_min"], 3), round(u["geometry"]["z_max"], 3)]
        identity = {
            "scheme": SCHEME, "dataset": "Schependomlaan", "parcel_id": parcel_id, "building_id": building_id,
            "property_unit_id": u["candidate_id"], "storey_ids": sorted(st), "vertical_extent_m": z,
            "geometry_version": geometry_version(u), "source_ids": sorted(u["source_space_ids"]),
        }
        records.append({
            "prototype_ulpin": encode(identity), "identity": identity,
            "parcel_id": parcel_id, "building_id": building_id, "property_unit_id": u["candidate_id"],
            "storey_ids": st, "storey_names": [storeys[s]["name"] for s in st if s in storeys],
            "geometry_version": identity["geometry_version"], "source_ids": identity["source_ids"],
            "identifier_class": "prototype_3d_ulpin", "is_official_ulpin": False,
            "issuer": "none (demonstrator-generated; not issued by any government authority)",
            "geometry": _geometry_block(u["geometry"]),
            "crs": {k: crs[k] for k in ("source_crs", "target_crs", "vertical_reference", "transformation_status", "coordinate_status")},
            "validation_status": unit_ok[u["candidate_id"]], "validation_state": unit_ok[u["candidate_id"]],
            "legal_status": "not_official_prototype_identifier", "ownership_status": "unknown_not_provided",
            "cadastral_status": cadastral_status, "data_status": "prototype",
            "provenance": {"source_dataset": "Schependomlaan", "derivation_method": "sha256(canonical identity JSON) -> base32",
                           "unit_status": u["status"], "unit_confidence": u["confidence"], "disclaimer": DISCLAIMER},
        })
    return {"scheme": SCHEME, "disclaimer": DISCLAIMER, "count": len(records), "records": records}


def _geometry_block(g: dict[str, Any]) -> dict[str, Any]:
    """Real geometry values carried by the identifier record (null + status when geometry is unavailable)."""
    if g["geometry_status"] == "unavailable":
        return {"geometry_status": "unavailable", "z_min": None, "z_max": None, "volume_m3": None,
                "footprint_area_m2": None, "centroid": None}
    return {"geometry_status": g["geometry_status"], "z_min": round(g["z_min"], 3), "z_max": round(g["z_max"], 3),
            "height_m": round(g["height_m"], 3), "volume_m3": round(g["volume_m3"], 3),
            "footprint_area_m2": round(g["footprint_area_m2"], 3) if g.get("footprint_area_m2") is not None else None,
            "centroid": [round(c, 3) for c in g["centroid"]], "geometry_source": g.get("geometry_source"),
            "is_fallback": g.get("is_fallback"), "geometry_confidence": g.get("confidence")}


def _unit_validation(v: dict[str, Any]) -> dict[str, str]:
    """Per-unit status derived from topology checks: a unit is 'validated' only if the whole run was valid
    and the unit appears in no failure item; 'not_validated' if required checks did not run for it."""
    out: dict[str, str] = {}
    skipped = set(v["metrics"].get("units_without_geometry", []))
    failed: set[str] = set()
    for c in v["checks"].values():
        if c["status"] != "failed":
            continue
        for it in c.get("items", []):
            if isinstance(it, dict):
                if "unit" in it:
                    failed.add(it["unit"])
                for o in it.get("owners", []):
                    failed.add(o)
                for o in it.get("units", []):
                    failed.add(o)
            elif isinstance(it, list):
                failed.update(str(x) for x in it if isinstance(x, str) and x.startswith("PU-"))
        for d in c.get("duplicates", []):
            failed.update(x for x in d[:2])
    for cid in v["metrics"].get("unit_ids", []):
        out[cid] = "not_validated" if cid in skipped else ("failed" if cid in failed else ("validated" if v["valid"] else "partially_validated"))
    return out
