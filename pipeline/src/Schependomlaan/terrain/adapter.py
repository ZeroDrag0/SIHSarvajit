"""Optional terrain adapter (AHN DTM/DSM rasters; GeoTIFF or ESRI ASCII grid). Local files only."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

EXTS = {".tif", ".tiff", ".asc"}


def _read_asc_header(p: Path) -> dict[str, Any]:
    hdr = {}
    with open(p) as f:
        for _ in range(6):
            k, v = f.readline().split()
            hdr[k.lower()] = float(v)
    return hdr


def describe_raster(p: Path) -> dict[str, Any]:
    rec: dict[str, Any] = {"file": p.name, "kind": "dsm" if "dsm" in p.name.lower() else ("dtm" if "dtm" in p.name.lower() else "unknown")}
    if p.suffix.lower() == ".asc":
        h = _read_asc_header(p)
        cs = h.get("cellsize", 0)
        rec.update(crs=None, resolution=cs, width=int(h["ncols"]), height=int(h["nrows"]),
                   bounds=[h["xllcorner"], h["yllcorner"], h["xllcorner"] + cs * h["ncols"], h["yllcorner"] + cs * h["nrows"]],
                   nodata=h.get("nodata_value"))
    else:
        import rasterio
        with rasterio.open(p) as r:
            rec.update(crs=str(r.crs) if r.crs else None, resolution=r.res[0], width=r.width, height=r.height,
                       bounds=list(r.bounds), nodata=r.nodata)
    rec["vertical_datum"] = "not stated in file; verify with publisher (AHN heights are normally NAP)"
    return rec


def sample_raster(p: Path, xs: list[float], ys: list[float]) -> list[float | None]:
    if p.suffix.lower() == ".asc":
        h = _read_asc_header(p)
        a = np.loadtxt(p, skiprows=6)
        out = []
        for x, y in zip(xs, ys):
            c = int((x - h["xllcorner"]) // h["cellsize"])
            r = int(h["nrows"] - 1 - (y - h["yllcorner"]) // h["cellsize"])
            v = a[r, c] if 0 <= r < a.shape[0] and 0 <= c < a.shape[1] else None
            out.append(None if v is None or v == h.get("nodata_value") else float(v))
        return out
    import rasterio
    with rasterio.open(p) as r:
        return [None if (v[0] == r.nodata or np.isnan(v[0])) else float(v[0]) for v in r.sample(list(zip(xs, ys)))]


def derive_building_terrain(rasters: list[Path], footprint, helmert: dict[str, Any] | None, building_z_min_local: float | None,
                            building_z_max_local: float | None, target_epsg: str = "EPSG:28992", grid_m: float = 1.0) -> dict[str, Any]:
    """Ground / roof elevation and relative height from DTM/DSM rasters.

    Requires a verified local->raster-CRS transformation (control-point Helmert fit, see crs.fit_helmert_2d_z) and a
    raster declared in `target_epsg`; otherwise returns an explicit not_derived status (no assumed alignment).
    """
    if helmert is None or helmert.get("status") != "fitted":
        return {"status": "not_derived", "reason": "no verified local->raster transformation (need >=2 control points)"}
    import numpy as np
    from shapely.geometry import Point
    minx, miny, maxx, maxy = footprint.bounds
    xs, ys = np.meshgrid(np.arange(minx, maxx + grid_m, grid_m), np.arange(miny, maxy + grid_m, grid_m))
    pts = [(float(x), float(y)) for x, y in zip(xs.ravel(), ys.ravel()) if footprint.contains(Point(x, y))]
    if not pts:
        return {"status": "not_derived", "reason": "footprint contains no sample points"}
    a, b = helmert["scale"] * np.cos(helmert["rotation_rad"]), helmert["scale"] * np.sin(helmert["rotation_rad"])
    rd = [(a * x - b * y + helmert["tx"], b * x + a * y + helmert["ty"]) for x, y in pts]
    out: dict[str, Any] = {"status": "derived", "transformation": {k: helmert[k] for k in ("scale", "rotation_rad", "tx", "ty", "dz", "rmse_m", "n")},
                           "sample_points": len(pts), "rasters": []}
    ground = roof = None
    for r in rasters:
        rec = describe_raster(r)
        if rec["crs"] is None or target_epsg.split(":")[-1] not in str(rec["crs"]):
            out["rasters"].append({"file": r.name, "status": "skipped_crs_mismatch_or_unknown", "raster_crs": rec["crs"]})
            continue
        vals = [v for v in sample_raster(r, [p[0] for p in rd], [p[1] for p in rd]) if v is not None]
        if not vals:
            out["rasters"].append({"file": r.name, "status": "no_valid_samples_under_footprint"})
            continue
        v = np.array(vals)
        kind = rec["kind"]
        entry = {"file": r.name, "kind": kind, "status": "sampled", "valid_samples": len(v), "min": float(v.min()),
                 "median": float(np.median(v)), "p95": float(np.percentile(v, 95)), "max": float(v.max())}
        out["rasters"].append(entry)
        if kind == "dtm":
            ground = float(np.median(v))
        elif kind == "dsm":
            roof = float(np.percentile(v, 95))
    out["terrain_elevation_m"] = ground
    out["roof_elevation_dsm_m"] = roof
    out["relative_building_height_dsm_minus_dtm_m"] = (roof - ground) if (roof is not None and ground is not None) else None
    if helmert.get("dz") is not None and building_z_min_local is not None and building_z_max_local is not None:
        out["building_base_elevation_m"] = building_z_min_local + helmert["dz"]
        out["building_top_elevation_from_ifc_m"] = building_z_max_local + helmert["dz"]
        if ground is not None:
            out["building_base_minus_terrain_m"] = out["building_base_elevation_m"] - ground
    if ground is None and roof is None:
        out["status"] = "not_derived"
        out["reason"] = "no usable DTM/DSM raster (kind inferred from file name: 'dtm'/'dsm')"
    return out


def load_terrain(dirs: list[Path]) -> dict[str, Any]:
    files = [p for d in dirs if d.is_dir() for p in sorted(d.rglob("*")) if p.suffix.lower() in EXTS]
    if not files:
        return {"terrain_status": "not_available", "rasters": [], "building_terrain": None,
                "notes": ["no DTM/DSM supplied; ground/roof elevation and height-above-terrain not derived"]}
    recs, errs = [], []
    for p in files:
        try:
            recs.append(describe_raster(p))
        except Exception as exc:  # noqa: BLE001
            errs.append(f"{p.name}: {type(exc).__name__}: {exc}")
    return {"terrain_status": "supplied_not_registered", "rasters": recs, "errors": errs, "building_terrain": None,
            "notes": ["terrain supplied, but the IFC is in an unverified local frame; ground/roof elevations are only "
                      "derived once a transformation to the raster CRS exists (see crs.fit_helmert_2d_z)"]}
