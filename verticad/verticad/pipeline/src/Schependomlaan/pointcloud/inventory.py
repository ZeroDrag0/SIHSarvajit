"""Point-cloud inventory, coverage and alignment metrics (PLY / LAS / LAZ / ASCII).

Acquisition method is NOT assumed: a cloud is only called LiDAR if documentation says so.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np

PLY_DTYPES = {"char": "i1", "uchar": "u1", "short": "i2", "ushort": "u2", "int": "i4", "uint": "u4",
              "float": "f4", "float32": "f4", "double": "f8", "float64": "f8", "int8": "i1", "uint8": "u1",
              "int16": "i2", "uint16": "u2", "int32": "i4", "uint32": "u4"}
ASCII_EXT = {".txt", ".xyz", ".pts", ".csv", ".asc"}
EXTS = {".ply", ".las", ".laz"} | ASCII_EXT
MARKERS = {"lidar": r"lidar|laser scan", "uav_drone": r"drone|uav|unmanned", "photogrammetry_sfm":
           r"photogrammetr|structure[- ]from[- ]motion|\bsfm\b", "terrestrial_scanner": r"terrestrial|tls|faro|leica"}


def lfs_pointer(path: Path) -> dict[str, Any] | None:
    """Return {oid, size} when the file is a Git-LFS pointer stub (content never downloaded), else None."""
    try:
        if path.stat().st_size > 1024:
            return None
        txt = path.read_text(errors="ignore")
    except OSError:
        return None
    if not txt.startswith("version https://git-lfs.github.com/spec"):
        return None
    oid = re.search(r"oid sha256:([0-9a-f]{64})", txt)
    size = re.search(r"size (\d+)", txt)
    return {"oid_sha256": oid.group(1) if oid else None, "expected_size_bytes": int(size.group(1)) if size else None}


def read_ply_header(path: Path) -> dict[str, Any]:
    with open(path, "rb") as f:
        lines, n = [], 0
        while True:
            ln = f.readline()
            n += len(ln)
            s = ln.decode("ascii", "replace").strip()
            lines.append(s)
            if s == "end_header" or not ln or len(lines) > 500:
                break
    fmt, count, props, comments, elem = None, 0, [], [], None
    for s in lines:
        t = s.split()
        if s.startswith("format"):
            fmt = t[1]
        elif s.startswith("comment") or s.startswith("obj_info"):
            comments.append(s)
        elif s.startswith("element"):
            elem = t[1]
            if elem == "vertex":
                count = int(t[2])
        elif s.startswith("property") and elem == "vertex":
            props.append((t[-1], t[1]))
    return {"format": fmt, "vertex_count": count, "properties": props, "comments": comments, "header_bytes": n}


def _ply_stats(path: Path, hdr: dict, sample_n: int) -> dict[str, Any]:
    names = [p[0] for p in hdr["properties"]]
    out: dict[str, Any] = {"point_count": hdr["vertex_count"], "properties": names, "ply_format": hdr["format"],
                           "header_comments": hdr["comments"]}
    if hdr["format"] == "ascii" and {"x", "y", "z"} <= set(names):
        import pandas as pd
        ix = [names.index(c) for c in ("x", "y", "z")]
        df = pd.read_csv(path, sep=r"\s+", header=None, skiprows=hdr["header_bytes"] and _line_count(path, hdr["header_bytes"]),
                         nrows=hdr["vertex_count"], usecols=ix, engine="c")
        xyz = df.to_numpy(float)
        out["bounds"] = [xyz.min(0).tolist(), xyz.max(0).tolist()]
        out["bounds_exact"] = True
        step = max(1, len(xyz) // sample_n)
        out["_sample"] = xyz[::step]
        out["has_rgb"] = {"red", "green", "blue"} <= set(names)
        out["has_normals"] = {"nx", "ny", "nz"} <= set(names)
    elif hdr["format"] in ("binary_little_endian", "binary_big_endian") and all(p[1] in PLY_DTYPES for p in hdr["properties"]):
        end = "<" if hdr["format"] == "binary_little_endian" else ">"
        dt = np.dtype([(n, end + PLY_DTYPES[t]) for n, t in hdr["properties"]])
        mm = np.memmap(path, dtype=dt, mode="r", offset=hdr["header_bytes"], shape=(hdr["vertex_count"],))
        xyz = np.stack([mm["x"], mm["y"], mm["z"]], 1)
        out["bounds"] = [xyz.min(0).astype(float).tolist(), xyz.max(0).astype(float).tolist()]
        out["bounds_exact"] = True
        step = max(1, hdr["vertex_count"] // sample_n)
        out["_sample"] = np.asarray(xyz[::step], dtype=float)
        out["has_rgb"] = {"red", "green", "blue"} <= set(names)
        out["has_normals"] = {"nx", "ny", "nz"} <= set(names)
        out["has_intensity"] = any(n in names for n in ("intensity", "scalar_intensity"))
    else:
        out["bounds"] = None
        out["note"] = f"PLY format {hdr['format']} not memory-mapped; bounds not computed"
    return out


def _line_count(path: Path, header_bytes: int) -> int:
    """Number of header lines occupying the first `header_bytes` bytes of an ASCII PLY."""
    with open(path, "rb") as f:
        return f.read(header_bytes).count(b"\n")


def density_estimate(sample: np.ndarray | None, n_points: int, bounds) -> dict[str, Any]:
    """Coarse density/coverage numbers in the file's own units (no unit conversion is assumed)."""
    if not bounds or not n_points:
        return {"status": "not_calculable"}
    lo, hi = np.array(bounds[0]), np.array(bounds[1])
    ext = hi - lo
    area = float(ext[0] * ext[1])
    out: dict[str, Any] = {"horizontal_bbox_area_file_units2": area,
                           "points_per_bbox_area_file_units2": float(n_points / area) if area > 0 else None}
    if sample is not None and len(sample) > 1000:
        from scipy.spatial import cKDTree
        d, _ = cKDTree(sample).query(sample, k=2)
        out["median_nn_spacing_in_subsample_file_units"] = float(np.median(d[:, 1]))
        # occupied-cell fraction on a 100x100 horizontal grid = crude horizontal coverage of the bbox
        gx = np.clip(((sample[:, 0] - lo[0]) / max(ext[0], 1e-12) * 100).astype(int), 0, 99)
        gy = np.clip(((sample[:, 1] - lo[1]) / max(ext[1], 1e-12) * 100).astype(int), 0, 99)
        out["occupied_cell_fraction_100x100"] = float(len(set(zip(gx.tolist(), gy.tolist()))) / 10000)
        out["note"] = "computed on a uniform subsample; units are the file's own (unscaled)"
    return out


def _ascii_stats(path: Path, sample_n: int) -> dict[str, Any]:
    import pandas as pd
    with open(path, "r", errors="replace") as f:
        first = [f.readline() for _ in range(3)]
    sep = "," if first[0].count(",") >= 2 else (";" if first[0].count(";") >= 2 else r"\s+")
    skip = 0
    while skip < 2 and not re.match(r"^\s*[-+0-9.]", first[skip]):
        skip += 1
    mn = np.full(3, np.inf)
    mx = np.full(3, -np.inf)
    n, ncols, samples = 0, None, []
    rgb_range = None
    for chunk in pd.read_csv(path, sep=sep, header=None, skiprows=skip, chunksize=2_000_000, engine="c" if sep != r"\s+" else "c",
                             on_bad_lines="skip"):
        a = chunk.iloc[:, :3].apply(pd.to_numeric, errors="coerce").to_numpy(float)
        ok = ~np.isnan(a).any(1)
        a = a[ok]
        ncols = chunk.shape[1]
        if len(a):
            mn, mx = np.minimum(mn, a.min(0)), np.maximum(mx, a.max(0))
            samples.append(a[:: max(1, len(a) // max(1, sample_n // 8))])
        n += int(ok.sum())
        if ncols >= 6 and rgb_range is None:
            c = chunk.iloc[:, 3:6].apply(pd.to_numeric, errors="coerce")
            rgb_range = [float(c.min().min()), float(c.max().max())]
    return {"point_count": n, "column_count": ncols, "delimiter": "whitespace" if sep == r"\s+" else sep,
            "bounds": [mn.tolist(), mx.tolist()] if n else None, "bounds_exact": True,
            "colour_columns_value_range_first_chunk": rgb_range, "_sample": np.vstack(samples) if samples else np.empty((0, 3))}


def _las_stats(path: Path, sample_n: int) -> dict[str, Any]:
    import laspy
    with laspy.open(str(path)) as r:
        h = r.header
        crs = None
        try:
            c = h.parse_crs()
            crs = c.to_string() if c else None
        except Exception:  # noqa: BLE001
            pass
        out = {"point_count": int(h.point_count), "las_version": str(h.version), "point_format": h.point_format.id,
               "bounds": [list(map(float, h.mins)), list(map(float, h.maxs))], "bounds_exact": True,
               "crs_from_file": crs, "generating_software": h.generating_software, "scales": list(h.scales)}
        pts = []
        step = max(1, int(h.point_count) // sample_n)
        for chunk in r.chunk_iterator(1_000_000):
            pts.append(np.c_[chunk.x, chunk.y, chunk.z][::step])
        out["_sample"] = np.vstack(pts) if pts else np.empty((0, 3))
        return out


def documentation_findings(doc_dirs: list[Path]) -> dict[str, Any]:
    found: dict[str, list[dict]] = {k: [] for k in MARKERS}
    scanned = []
    for d in doc_dirs:
        if not d or not d.is_dir():
            continue
        for p in d.rglob("*"):
            if p.suffix.lower() in {".md", ".txt", ".html", ".htm", ".yaml", ".yml", ".json"} and p.stat().st_size < 2_000_000:
                scanned.append(str(p))
                txt = p.read_text(errors="ignore")
                for k, rx in MARKERS.items():
                    m = re.search(rx, txt, re.I)
                    if m:
                        found[k].append({"file": str(p), "context": txt[max(0, m.start() - 60): m.end() + 60].replace("\n", " ")})
    return {"files_scanned": scanned, "mentions": {k: v for k, v in found.items() if v}}


def inventory(pc_dir: Path | None, doc_dirs: list[Path], sample_n: int = 200_000) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    samples: dict[str, np.ndarray] = {}
    docs = documentation_findings(doc_dirs)
    if pc_dir is None or not pc_dir.is_dir():
        return ({"status": "no_pointcloud_directory_found", "files": [], "format_summary": {}, "total_detected": 0,
                 "documentation": docs, "acquisition_statement": _statement(docs, False)}, samples)
    files = []
    for p in sorted(pc_dir.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in EXTS:
            continue
        ext = p.suffix.lower()
        rec: dict[str, Any] = {"path": str(p), "name": p.name, "format": ext.lstrip("."), "size_bytes": p.stat().st_size,
                               "crs_known": False, "crs_statement": "no CRS in file/metadata; coordinates treated as local/unverified"}
        ptr = lfs_pointer(p)
        if ptr:
            rec.update(parse_status="git_lfs_pointer_not_downloaded", lfs_pointer=ptr,
                       note="file is a Git-LFS pointer stub, not point data; run `git lfs pull` (or download the "
                            "dataset release zip) and re-run the pipeline",
                       point_count=None, bounds=None)
            files.append(rec)
            continue
        try:
            if ext == ".ply":
                st = _ply_stats(p, read_ply_header(p), sample_n)
            elif ext in (".las", ".laz"):
                st = _las_stats(p, sample_n)
            else:
                st = _ascii_stats(p, sample_n)
            s = st.pop("_sample", None)
            if s is not None and len(s):
                samples[str(p)] = s
            rec.update(st)
            if st.get("crs_from_file"):
                rec["crs_known"], rec["crs_statement"] = True, f"CRS declared in file: {st['crs_from_file']} (not independently verified)"
            if st.get("bounds"):
                lo, hi = np.array(st["bounds"][0]), np.array(st["bounds"][1])
                rec["extent"] = (hi - lo).tolist()
                rec["z_range"] = [float(lo[2]), float(hi[2])]
            rec["density"] = density_estimate(s, int(rec.get("point_count") or 0), rec.get("bounds"))
            rec["parse_status"] = "ok"
        except Exception as exc:  # noqa: BLE001
            rec["parse_status"] = f"error: {type(exc).__name__}: {exc}"
        files.append(rec)
    fmt: dict[str, int] = {}
    for f in files:
        k = "ascii_text" if f"." + f["format"] in ASCII_EXT else f["format"]
        fmt[k] = fmt.get(k, 0) + 1
    n_ok = sum(1 for f in files if f.get("parse_status") == "ok")
    n_lfs = sum(1 for f in files if f.get("parse_status") == "git_lfs_pointer_not_downloaded")
    status = ("no_supported_files" if not files else "ok" if n_ok == len(files) else
              "git_lfs_pointers_only" if n_lfs == len(files) else "partial")
    return ({"status": status, "source_root": str(pc_dir), "files": files, "files_processed": n_ok,
             "files_git_lfs_pointer": n_lfs,
             "format_summary": fmt, "total_detected": len(files), "documentation": docs,
             "acquisition_statement": _statement(docs, bool(files))}, samples)


def _statement(docs: dict, have_files: bool) -> str:
    m = docs["mentions"]
    base = "Acquisition method is not asserted: files are treated as generic point-cloud data."
    if "lidar" in m:
        base += " Documentation mentions laser/LiDAR scanning (see documentation.mentions); not independently verified."
    if "photogrammetry_sfm" in m or "uav_drone" in m:
        base += " Documentation mentions photogrammetry/UAV; original drone imagery is not part of this dataset and was not used."
    if not m:
        base += " No documentation about acquisition was found in the scanned folders."
    return base


# ---------------------------------------------------------------------------
def coverage_and_alignment(inv: dict[str, Any], samples: dict[str, np.ndarray], ifc_bounds: list[list[float]] | None,
                           storeys: list[dict] | None, rules: dict) -> tuple[dict[str, Any], dict[str, Any]]:
    buf = rules["pointcloud"]["inside_building_buffer_m"]
    cov: dict[str, Any] = {"status": "ok", "files": []}
    ali: dict[str, Any] = {"status": "ok", "ifc_bounds_m": ifc_bounds, "files": [],
                           "method": "extent_and_bbox_comparison (no registration / ICP performed)"}
    if not ifc_bounds:
        ali["status"] = cov["status"] = "ifc_geometry_unavailable"
        ali["note"] = "IFC space geometry was not available, so no point-cloud/IFC comparison was possible"
    for f in inv.get("files", []):
        if f.get("parse_status") != "ok" or not f.get("bounds"):
            continue
        lo, hi = np.array(f["bounds"][0]), np.array(f["bounds"][1])
        c = {"file": f["name"], "point_count": f["point_count"], "bounds": f["bounds"], "z_range": f.get("z_range"),
             "extent": f.get("extent")}
        a = {"file": f["name"], "crs_known": f["crs_known"], "candidates": []}
        if ifc_bounds:
            ilo, ihi = np.array(ifc_bounds[0]), np.array(ifc_bounds[1])
            iext = ihi - ilo
            smp = samples.get(f["path"])
            best = None
            for scale, label in ((1.0, "metres"), (0.001, "millimetres"), (0.01, "centimetres")):
                ext = (hi - lo) * scale
                ratio = float(np.max(ext[:2]) / max(np.max(iext[:2]), 1e-9))
                cand: dict[str, Any] = {"assumed_unit": label, "scale_to_m": scale, "extent_m": ext.tolist(),
                                        "horizontal_extent_ratio_vs_ifc": ratio}
                if smp is not None and len(smp):
                    s = smp * scale
                    inside = np.all((s >= ilo - buf) & (s <= ihi + buf), axis=1)
                    cand["fraction_sample_inside_ifc_bbox_in_local_frames"] = float(inside.mean())
                    cand["centre_offset_m"] = (((lo + hi) / 2) * scale - (ilo + ihi) / 2).tolist()
                a["candidates"].append(cand)
                if 1 / rules["pointcloud"]["max_plausible_extent_ratio"] < ratio < rules["pointcloud"]["max_plausible_extent_ratio"]:
                    if best is None or abs(np.log(ratio)) < abs(np.log(best["horizontal_extent_ratio_vs_ifc"])):
                        best = cand
            if best is None:
                a["status"] = "no_plausible_unit_scale"
            else:
                a["best_scale_candidate"] = best["assumed_unit"]
                off = np.linalg.norm(np.array(best["centre_offset_m"][:2])) if "centre_offset_m" in best else None
                frac = best.get("fraction_sample_inside_ifc_bbox_in_local_frames")
                a["status"] = ("plausibly_co-registered" if (off is not None and off < 3.0 and frac and frac > 0.5)
                               else "size_compatible_but_unregistered")
                a["note"] = ("Extents are comparable but the point cloud and IFC are in different local frames; "
                             "registration (ICP / control points) is required before volumetric comparison."
                             if a["status"] != "plausibly_co-registered" else "Frames appear co-registered (unverified).")
                c["fraction_sample_inside_ifc_bbox"] = frac
        cov["files"].append(c)
        ali["files"].append(a)
    return cov, ali
