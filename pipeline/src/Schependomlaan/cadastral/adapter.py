"""Optional cadastral (BRK) / BAG adapter. Local files only; never downloads; never invents IDs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from shapely.geometry import shape

ID_FIELDS = ["kadastraleAanduiding", "kadastrale_aanduiding", "parcel_id", "perceel_id", "identificatie",
             "lokaalID", "localId", "id", "ID"]
BAG_FIELDS = ["pandidentificatie", "bag_id", "identificatie", "pand_id", "id"]
EXTS = {".geojson", ".json", ".gpkg", ".gml"}


def _read_features(path: Path) -> tuple[list[dict[str, Any]], str | None]:
    ext = path.suffix.lower()
    if ext in (".geojson", ".json"):
        d = json.loads(path.read_text(encoding="utf-8"))
        crs = None
        c = d.get("crs") or {}
        if isinstance(c, dict):
            crs = (c.get("properties") or {}).get("name")
        feats = d["features"] if d.get("type") == "FeatureCollection" else ([d] if d.get("type") == "Feature" else [])
        return [{"props": f.get("properties") or {}, "geom": shape(f["geometry"]) if f.get("geometry") else None} for f in feats], crs
    import pyogrio
    from shapely import from_wkb
    try:
        layers = [str(l[0]) for l in pyogrio.list_layers(str(path))]
    except Exception:  # noqa: BLE001
        layers = [None]
    out, crs = [], None
    for layer in layers or [None]:                      # GPKG may hold several layers; read all of them
        meta, _fids, geoms, fields = pyogrio.raw.read(str(path), layer=layer)
        names = list(meta["fields"])
        crs = crs or meta.get("crs")
        for i in range(len(geoms)):
            out.append({"props": {n: (fields[j][i].item() if hasattr(fields[j][i], "item") else fields[j][i]) for j, n in enumerate(names)},
                        "geom": from_wkb(geoms[i]) if geoms[i] is not None else None})
    return out, crs


def _http_get_json(url: str, headers: dict[str, str] | None = None, timeout: float = 30.0) -> dict[str, Any]:
    import urllib.request
    req = urllib.request.Request(url, headers={"Accept": "application/geo+json, application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (explicit opt-in via config file)
        return json.loads(r.read().decode("utf-8"))


def read_ogc_api(cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    """Page through an OGC API - Features `items` endpoint declared in external/<dir>/ogc_api.json.

    cfg: {"items_url": ".../collections/<id>/items", "bbox": [minx,miny,maxx,maxy] (optional), "bbox_crs": "EPSG:28992",
          "crs": "EPSG:28992", "kind": "parcel"|"bag", "limit": 1000, "max_pages": 5, "headers": {}}
    Network access happens only when this config file exists (never implicitly).
    """
    from urllib.parse import urlencode
    url = cfg["items_url"]
    q: dict[str, Any] = {"f": "json", "limit": cfg.get("limit", 1000)}
    if cfg.get("bbox"):
        q["bbox"] = ",".join(str(v) for v in cfg["bbox"])
        if cfg.get("bbox_crs"):
            q["bbox-crs"] = cfg["bbox_crs"]
    if cfg.get("crs"):
        q["crs"] = cfg["crs"]
    url = url + ("&" if "?" in url else "?") + urlencode(q)
    feats: list[dict[str, Any]] = []
    for _ in range(int(cfg.get("max_pages", 5))):
        d = _http_get_json(url, cfg.get("headers"))
        for f in d.get("features", []):
            feats.append({"props": f.get("properties") or {}, "geom": shape(f["geometry"]) if f.get("geometry") else None})
        nxt = next((l["href"] for l in d.get("links", []) if l.get("rel") == "next"), None)
        if not nxt:
            break
        url = nxt
    return feats, cfg.get("crs")


def _pick(props: dict, keys: list[str]) -> str | None:
    for k in keys:
        if k in props and props[k] not in (None, ""):
            return str(props[k])
    return None


def load_cadastral(dirs: list[Path]) -> dict[str, Any]:
    files = [p for d in dirs if d.is_dir() for p in sorted(d.rglob("*")) if p.is_file() and p.suffix.lower() in EXTS
             and p.name not in ("building_parcel_link.json", "ogc_api.json")]
    link_file = next((d / "building_parcel_link.json" for d in dirs if (d / "building_parcel_link.json").is_file()), None)
    ogc_cfgs = [(d / "ogc_api.json") for d in dirs if (d / "ogc_api.json").is_file()]
    if not files and not ogc_cfgs:
        return {"cadastral_status": "not_available", "parcel_id": None, "parcel_count": 0, "files": [],
                "link": None, "notes": ["no local cadastral/BAG file supplied; no parcel identifiers are invented"]}
    parcels, bag, filerecs, errors = [], [], [], []
    for p in files:
        try:
            feats, crs = _read_features(p)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{p.name}: {type(exc).__name__}: {exc}")
            continue
        is_bag = "bag" in p.parent.name.lower() or "bag" in p.name.lower()
        for f in feats:
            if f["geom"] is None:
                continue
            rec = {"id": _pick(f["props"], BAG_FIELDS if is_bag else ID_FIELDS), "geometry": f["geom"],
                   "source_file": p.name, "properties": f["props"], "crs": crs}
            (bag if is_bag else parcels).append(rec)
        filerecs.append({"file": p.name, "features": len(feats), "crs": crs, "kind": "bag" if is_bag else "parcel"})
    for cf in ogc_cfgs:
        try:
            cfg = json.loads(cf.read_text(encoding="utf-8"))
            feats, crs = read_ogc_api(cfg)
            is_bag = str(cfg.get("kind", "parcel")).lower() == "bag"
            for f in feats:
                if f["geom"] is None:
                    continue
                rec = {"id": _pick(f["props"], BAG_FIELDS if is_bag else ID_FIELDS), "geometry": f["geom"],
                       "source_file": cfg["items_url"], "properties": f["props"], "crs": crs}
                (bag if is_bag else parcels).append(rec)
            filerecs.append({"file": cfg["items_url"], "features": len(feats), "crs": crs, "kind": "bag" if is_bag else "parcel",
                             "source": "ogc_api_features"})
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{cf.name}: {type(exc).__name__}: {exc}")
    link = json.loads(link_file.read_text()) if link_file else None
    return {"cadastral_status": "supplied" if (parcels or bag) else "supplied_unreadable", "files": filerecs,
            "parcel_count": len(parcels), "bag_building_count": len(bag), "errors": errors, "link": link,
            "_parcels": parcels, "_bag": bag}


def associate(cad: dict[str, Any], building: dict[str, Any], building_footprint=None, footprint_crs: str | None = None) -> dict[str, Any]:
    """Link a building to a parcel.

    Allowed bases (in order): explicit link file; geometric intersection ONLY when the building
    footprint is supplied in the same CRS as the parcel file.  Otherwise parcel_id stays null.
    """
    out = {"building_id": building["global_id"], "parcel_id": None, "bag_id": None, "link_basis": None,
           "cadastral_status": cad["cadastral_status"], "parcel_building_intersection": "not_evaluated"}
    if cad["cadastral_status"] == "not_available":
        return out
    link = cad.get("link") or {}
    if link.get("building_global_id") in (None, building["global_id"]) and link.get("parcel_id"):
        out.update(parcel_id=str(link["parcel_id"]), bag_id=link.get("bag_id"), link_basis="explicit_link_file",
                   cadastral_status="linked")
    parcels = cad.get("_parcels", [])
    if building_footprint is not None and footprint_crs and parcels:
        same = [p for p in parcels if p["crs"] and footprint_crs.split(":")[-1] in str(p["crs"])]
        hits = [p for p in same if p["geometry"].intersects(building_footprint)]
        if hits:
            best = max(hits, key=lambda p: p["geometry"].intersection(building_footprint).area)
            frac = best["geometry"].intersection(building_footprint).area / max(building_footprint.area, 1e-9)
            out["parcel_building_intersection"] = {"overlap_fraction_of_building": frac}
            if out["parcel_id"] is None:
                out.update(parcel_id=best["id"], link_basis="geometric_intersection", cadastral_status="linked")
        else:
            out["parcel_building_intersection"] = "no_intersection_in_shared_crs"
    elif out["parcel_id"] is None:
        out["cadastral_status"] = "supplied_not_linked"
        out["note"] = ("parcels supplied but the IFC is in an unverified local frame and no link file was given; "
                       "building->parcel association cannot be established without inventing it")
    return out
