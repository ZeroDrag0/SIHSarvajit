"""Schependomlaan 3D cadastre demonstrator pipeline.

    python -m Schependomlaan.run_pipeline --stage all [--ifc PATH] [--pointcloud-dir DIR] [--dataset-root DIR]

Every stage is independently executable: it loads its inputs from processed/ (running the producing stage
if the artefact is missing).  Optional data (cadastral, terrain, underground, GNSS) is picked up from
external/ when present and reported as "not_available" otherwise.  Nothing is downloaded.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import platform
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Schependomlaan import extraction as ex  # noqa: E402
from Schependomlaan.cadastral import adapter as cad_adapter  # noqa: E402
from Schependomlaan.cadastre.model import build_model, build_schema  # noqa: E402
from Schependomlaan.classification import classify_spaces  # noqa: E402
from Schependomlaan.config.settings import PipelineSettings, make_settings  # noqa: E402
from Schependomlaan.crs.handling import crs_record, fit_helmert_2d_z, load_control_points  # noqa: E402
from Schependomlaan.geometry import exporters  # noqa: E402
from Schependomlaan.geometry.space_geometry import extract_all_space_geometry, load_meshes, save_meshes  # noqa: E402
from Schependomlaan.geometry.unit_geometry import build_unit_geometry  # noqa: E402
from Schependomlaan.pointcloud import compare as pc_compare  # noqa: E402
from Schependomlaan.pointcloud.inventory import coverage_and_alignment, inventory  # noqa: E402
from Schependomlaan.preprocessing import ifc_graph  # noqa: E402
from Schependomlaan.terrain.adapter import EXTS as TERRAIN_EXTS, derive_building_terrain, load_terrain  # noqa: E402
from Schependomlaan.ulpin.prototype import generate_prototype_ulpins  # noqa: E402
from Schependomlaan.underground.model import load_underground  # noqa: E402
from Schependomlaan.utils.json_io import read_json, write_json  # noqa: E402
from Schependomlaan.validation.topology import validate_topology  # noqa: E402

STAGES = ["inspect", "preprocess", "classify", "floors", "units", "geometry", "pointcloud", "cadastral",
          "terrain", "validate", "ulpin", "export"]

FILES = {
    "graph": "ifc/schependomlaan_ifc_graph.json",
    "structure": "ifc/schependomlaan_ifc_structure.json",
    "relationships": "ifc/schependomlaan_space_relationships.json",
    "space_geometry": "geometry/space_geometry.json",
    "space_meshes": "geometry/space_meshes.npz",
    "building": "ifc/building_extraction.json",
    "classification": "ifc/space_classification.json",
    "floors": "floors/schependomlaan_floors.json",
    "candidates": "apartments/candidate_property_units.json",
    "units": "geometry/property_units.json",
    "geojson": "geometry/property_units.geojson",
    "glb": "geometry/property_units.glb",
    "ply": "geometry/property_units.ply",
    "pc_comparison": "pointcloud/ifc_comparison_metrics.json",
    "model_geojson": "cadastre/3d_cadastral_model.geojson",
    "provenance_doc": "cadastre/provenance.json",
    "pc_inventory": "pointcloud/inventory.json",
    "pc_coverage": "pointcloud/coverage_metrics.json",
    "pc_alignment": "pointcloud/alignment_metrics.json",
    "cadastral": "cadastral/cadastral_summary.json",
    "terrain": "geometry/terrain_summary.json",
    "validation": "validation/topology_validation.json",
    "ulpin": "ulpin/prototype_ulpins.json",
    "crs": "cadastre/crs_status.json",
    "underground": "cadastre/underground_entities.json",
    "model": "cadastre/3d_cadastral_model.json",
    "schema": "cadastre/3d_cadastral_schema.json",
    "report": "cadastre/pipeline_report.json",
    "viewer": "cadastre/viewer_manifest.json",
}
# flat, user-facing copies written directly under processed/ by stage_publish
FLAT = {"building": "building.json", "floors": "floors.json", "units": "property_units.json",
        "classification": "space_classification.json", "pointcloud": "pointcloud_inventory.json",
        "validation": "topology_validation.json", "model": "3d_cadastral_model.json", "ulpin": "ulpins.json",
        "provenance": "provenance.json", "report": "pipeline_report.json"}
LEGACY_CACHE = "ifc/schependomlaan_inspection.json"
LEGACY_PC = "pointcloud/schependomlaan_pointcloud_inventory.json"


class Pipeline:
    def __init__(self, st: PipelineSettings):
        self.st = st
        self.mem: dict[str, Any] = {}
        st.ensure_directories()

    # ---------- artefact access --------------------------------------------------
    def path(self, key: str) -> Path:
        return self.st.out(*FILES[key].split("/"))

    def save(self, key: str, data: Any) -> Any:
        write_json(self.path(key), data)
        self.mem[key] = data
        return data

    def need(self, key: str, producer: str) -> Any:
        if key in self.mem:
            return self.mem[key]
        if self.path(key).exists():
            self.mem[key] = read_json(self.path(key))
            return self.mem[key]
        getattr(self, f"stage_{producer}")()
        return self.mem[key]

    # ---------- stages ------------------------------------------------------------------
    def stage_inspect(self) -> dict:
        ifc = self.st.resolve_ifc()
        if ifc:
            graph = ifc_graph.build_ifc_graph(ifc)
        else:
            cache = self.st.out(*LEGACY_CACHE.split("/"))
            if not cache.exists():
                raise SystemExit("No IFC found (use --ifc / SCHEP_IFC / raw/ifc/) and no cached inspection available.")
            graph = ifc_graph.graph_from_legacy_inspection(read_json(cache), str(cache))
            print("WARNING: source IFC not found; using cached earlier inspection (limited evidence, no geometry).", file=sys.stderr)
        graph["entity_counts"] = dict(graph["entity_counts"])
        self.save("graph", graph)
        self.save("structure", ifc_graph.structure_document(graph))
        self.save("relationships", ifc_graph.relationships_document(graph, self.st.rules))
        return graph

    def stage_preprocess(self) -> dict:
        graph = self.need("graph", "inspect")
        ifc = self.st.resolve_ifc()
        if ifc and graph["source_mode"] == "live_ifc":
            doc, meshes = extract_all_space_geometry(ifc)
            save_meshes(meshes, self.path("space_meshes"))
        else:
            doc = {"source_file": graph["source_file"], "coordinate_frame": "unavailable",
                   "summary": {"space_count": len(graph["spaces"]), "geometry_extracted": 0, "success_rate": 0.0,
                               "by_status": {"unavailable": len(graph["spaces"])}, "by_method": {"None": len(graph["spaces"])}},
                   "reason": "source IFC not accessible in this run; geometry cannot be recomputed",
                   "legacy_cache_note": "an earlier run on the project machine reported body-mesh extraction for 6 of 100 spaces "
                                        "(bounds/volume only, no meshes retained): " + json.dumps(
                                            [{"name": s["name"], **s["cached_geometry_summary"]} for s in graph["spaces"]
                                             if s.get("cached_geometry_summary", {}).get("extracted")]),
                   "spaces": [{"space_global_id": s["global_id"], "space_name": s["name"], "geometry_status": "unavailable",
                               "method": None, "notes": ["source IFC not accessible"]} for s in graph["spaces"]]}
            self.path("space_meshes").unlink(missing_ok=True)
        self.save("space_geometry", doc)
        self.mem["meshes"] = load_meshes(self.path("space_meshes"))
        be = ex.get("building_extraction", "ifc_space_envelope").run(graph=graph, space_geom=doc)
        be.update({"method": "geometry_based", "model_status": "not_trained"})
        self.save("building", be)
        return doc

    def meshes(self) -> dict:
        if "meshes" not in self.mem:
            self.mem["meshes"] = load_meshes(self.path("space_meshes"))
        return self.mem["meshes"]

    def stage_classify(self) -> dict:
        graph = self.need("graph", "inspect")
        return self.save("classification", classify_spaces(graph, self.st.rules))

    def stage_floors(self) -> dict:
        graph = self.need("graph", "inspect")
        cls = self.need("classification", "classify")
        sg = self.need("space_geometry", "preprocess")
        res = ex.get("floor_segmentation", "ifc_storey_structure").run(graph=graph, classification=cls, space_geom=sg)
        res.update({"method_type": "rule_based", "model_status": "not_trained"})
        return self.save("floors", res)

    def stage_units(self) -> dict:
        graph = self.need("graph", "inspect")
        cls = self.need("classification", "classify")
        sg = self.need("space_geometry", "preprocess")
        res = ex.get("vertical_property_delineation", "prefix_composition_rules").run(
            graph=graph, classification=cls, rules=self.st.rules, space_geom=sg)
        return self.save("candidates", res)

    def stage_geometry(self) -> dict:
        graph = self.need("graph", "inspect")
        cands = self.need("candidates", "units")
        sg = self.need("space_geometry", "preprocess")
        crs = self.crs()
        sgd = {r["space_global_id"]: r for r in sg["spaces"]}
        meshes = self.meshes()
        units, named = [], {}
        for c in cands["candidates"]:
            g, mesh = build_unit_geometry(c, sgd, meshes)
            u = {**c, "geometry": g, "coordinate_reference": crs}
            units.append(u)
            if mesh is not None:
                named[c["candidate_id"]] = mesh
        n = len(units)
        ok = sum(1 for u in units if u["geometry"]["geometry_status"] != "unavailable")
        valid = sum(1 for u in units if u["geometry"]["geometry_status"] == "valid")
        from collections import Counter
        doc = {"source_mode": graph["source_mode"], "coordinate_reference": crs,
               "summary": {"unit_count": n, "units_with_geometry": ok, "geometry_success_rate": round(ok / n, 4) if n else None,
                           "units_geometry_valid": valid, "by_geometry_status": dict(Counter(u["geometry"]["geometry_status"] for u in units)),
                           "by_representation": dict(Counter(str(u["geometry"].get("representation")) for u in units))},
               "units": units}
        self.save("units", doc)
        write_json(self.path("geojson"), exporters.units_geojson(units, crs))
        if named:
            exporters.export_glb(named, self.path("glb"))
            exporters.export_ply(named, self.path("ply"))
        else:
            self.path("glb").unlink(missing_ok=True)
            self.path("ply").unlink(missing_ok=True)
            doc["summary"]["glb"] = "not_written: no unit geometry available"
            self.save("units", doc)
        return doc

    def stage_pointcloud(self) -> dict:
        pcdir = self.st.resolve_pointcloud_dir()
        docs = [self.st.raw_dir / "documentation", self.st.dataset_root.parent / "Archive-DataSetSchependomlaan"]
        inv, samples = inventory(pcdir, [d for d in docs if d.is_dir()], self.st.rules["pointcloud"]["ascii_sample_rows"])
        legacy = self.st.out(*LEGACY_PC.split("/"))
        if not inv["files"] and legacy.exists():
            old = read_json(legacy)
            inv["legacy_cached_inventory"] = {
                "note": "point-cloud directory not accessible in this run; entries below come from an earlier inventory run on the project machine",
                "total_detected": old.get("total_detected"), "format_summary": old.get("pointcloud_format_summary"),
                "files": [{k: f.get(k) for k in ("name", "format", "size_bytes", "point_count", "crs_known")} for f in old.get("files", [])]}
        self.save("pc_inventory", inv)
        sg = self.need("space_geometry", "preprocess")
        ifc_bounds = None
        recs = [r for r in sg["spaces"] if r["geometry_status"] != "unavailable"]
        if recs:
            lo = [min(r["bounds"][0][i] for r in recs) for i in range(3)]
            hi = [max(r["bounds"][1][i] for r in recs) for i in range(3)]
            ifc_bounds = [lo, hi]
        cov, ali = coverage_and_alignment(inv, samples, ifc_bounds, None, self.st.rules)
        if not inv["files"]:
            cov["status"] = ali["status"] = "no_pointcloud_files_accessible"
        elif not inv.get("files_processed"):
            cov["status"] = ali["status"] = "no_pointcloud_files_processed"
        self.save("pc_coverage", cov)
        self.save("pc_alignment", ali)
        self.save("pc_comparison", self._compare_pointclouds(inv, samples, ali, ifc_bounds, pcdir))
        return inv

    def _compare_pointclouds(self, inv: dict, samples: dict, ali: dict, ifc_bounds, pcdir) -> dict:
        """Real overlap / distance / coverage metrics - only for clouds with a declared or plausible registration."""
        P = self.st.rules["pointcloud"]
        regs = pc_compare.load_registrations([d for d in (self.st.external_dir / "pointcloud", self.st.raw_dir / "pointcloud", pcdir) if d])
        out = {"status": "ok", "method": "KD-tree nearest distance to sampled IfcSpace surfaces; no ICP/registration estimated",
               "registration_files_found": bool(regs), "files": []}
        meshes = self.meshes()
        if not inv.get("files"):
            out["status"] = "no_pointcloud_files_accessible"
            return out
        if not any(f.get("parse_status") == "ok" for f in inv["files"]):
            out["status"] = "no_pointcloud_files_processed"
            out["reason"] = ("all discovered files are Git-LFS pointer stubs (content not downloaded)"
                             if inv.get("files_git_lfs_pointer") == len(inv["files"]) else "no file could be parsed")
            out["files"] = [{"file": f["name"], "status": f"not_computed_{f.get('parse_status')}"} for f in inv["files"]]
            return out
        if not meshes or not ifc_bounds:
            out["status"] = "ifc_geometry_unavailable"
            return out
        amap = {a["file"]: a for a in ali.get("files", [])}
        for f in inv["files"]:
            rec = {"file": f["name"], "path": f["path"]}
            if f.get("parse_status") != "ok":
                rec.update(status=f"not_computed_{f.get('parse_status')}")
                out["files"].append(rec)
                continue
            smp = samples.get(f["path"])
            reg = pc_compare.registration_for(f["name"], regs)
            a = amap.get(f["name"], {})
            if smp is None or not len(smp):
                rec["status"] = "not_computed_no_sample"
            elif reg:
                rec = pc_compare.compare_cloud(f["name"], smp, f["point_count"], float(reg.get("unit_scale_to_m", 1.0)),
                                               reg.get("matrix_4x4"), f"user_supplied_registration ({reg.get('source', reg['_file'])})",
                                               meshes, ifc_bounds, P)
            elif a.get("status") == "plausibly_co-registered":
                best = next(c for c in a["candidates"] if c["assumed_unit"] == a["best_scale_candidate"])
                rec = pc_compare.compare_cloud(f["name"], smp, f["point_count"], best["scale_to_m"], None,
                                               "heuristic_plausibly_co-registered (unverified)", meshes, ifc_bounds, P)
            else:
                rec.update(status="not_computed_registration_unverified",
                           alignment_status=a.get("status"),
                           crs_known=f.get("crs_known"),
                           note="no registration file and the frames are not demonstrably co-registered; "
                                "no alignment was invented. Supply external/pointcloud/registration.json to enable metrics.")
            out["files"].append(rec)
        out["files_with_metrics"] = sum(1 for r in out["files"] if r.get("status") == "computed")
        return out

    # ---------- helpers: control-point transform + local building footprint ---------------------------
    def helmert(self) -> dict | None:
        pts = load_control_points(self.st.external_dir / "gnss" / "control_points.csv")
        return fit_helmert_2d_z(pts) if len(pts) >= 2 else None

    def building_footprint_local(self):
        """Closed union of IfcSpace footprints (local IFC metres); None when no space geometry exists."""
        from shapely.geometry import shape as _shape
        from shapely.ops import unary_union
        sg = self.need("space_geometry", "preprocess")
        fps = [_shape(r["footprint"]) for r in sg["spaces"] if r.get("footprint")]
        if not fps:
            return None
        return unary_union(fps).buffer(0.3).buffer(-0.3)   # close internal wall gaps (net rooms -> gross outline)

    def building_footprint_rd(self):
        h = self.helmert()
        fp = self.building_footprint_local()
        if h is None or h.get("status") != "fitted" or fp is None:
            return None
        import numpy as np
        from shapely import affinity
        a, b = h["scale"] * np.cos(h["rotation_rad"]), h["scale"] * np.sin(h["rotation_rad"])
        return affinity.affine_transform(fp, [a, -b, b, a, h["tx"], h["ty"]])

    def stage_cadastral(self) -> dict:
        graph = self.need("graph", "inspect")
        cad = cad_adapter.load_cadastral([self.st.external_dir / "cadastral", self.st.external_dir / "bag"])
        b = graph["buildings"][0]
        fp_rd = self.building_footprint_rd()
        link = cad_adapter.associate(cad, b, fp_rd, "EPSG:28992" if fp_rd is not None else None)
        summary = {k: v for k, v in cad.items() if not k.startswith("_")}
        summary.update({"building_link": link, "parcel_id": link["parcel_id"], "hierarchy": "Parcel > Building > Storey > Vertical Property Unit",
                        "association_policy": "explicit link file, or intersection in a shared verified CRS; otherwise null"})
        return self.save("cadastral", summary)

    def stage_terrain(self) -> dict:
        tdir = self.st.external_dir / "terrain"
        terr = load_terrain([tdir])
        files = [p for p in sorted(tdir.rglob("*")) if p.suffix.lower() in TERRAIN_EXTS] if tdir.is_dir() else []
        if files:
            fp = self.building_footprint_local()
            sg = self.need("space_geometry", "preprocess")
            recs = [r for r in sg["spaces"] if r["geometry_status"] != "unavailable"]
            if fp is not None and recs:
                bt = derive_building_terrain(files, fp, self.helmert(), min(r["z_min"] for r in recs), max(r["z_max"] for r in recs))
                terr["building_terrain"] = bt
                if bt["status"] == "derived":
                    terr["terrain_status"] = "derived"
        return self.save("terrain", terr)

    def crs(self) -> dict:
        graph = self.need("graph", "inspect")
        pts = load_control_points(self.st.external_dir / "gnss" / "control_points.csv")
        return crs_record(graph=graph, control_points=pts)

    def stage_validate(self) -> dict:
        floors = self.need("floors", "floors")
        udoc = self.need("units", "geometry")
        cands = self.need("candidates", "units")
        sg = self.need("space_geometry", "preprocess")
        cad = self.need("cadastral", "cadastral")
        terr = self.need("terrain", "terrain")
        res = validate_topology(udoc["units"], sg, self.meshes(), floors, [s["global_id"] for s in cands["common_service_spaces"]],
                                cad.get("building_link"), cad["cadastral_status"], terr, self.st.rules)
        return self.save("validation", res)

    def stage_ulpin(self) -> dict:
        graph = self.need("graph", "inspect")
        udoc = self.need("units", "geometry")
        val = self.need("validation", "validate")
        cad = self.need("cadastral", "cadastral")
        floors = self.need("floors", "floors")
        res = generate_prototype_ulpins(udoc["units"], graph["buildings"][0]["global_id"], cad["parcel_id"],
                                        cad["cadastral_status"], self.crs(), val, {s["storey_id"]: s for s in floors["storeys"]})
        return self.save("ulpin", res)

    def stage_export(self) -> dict:
        graph = self.need("graph", "inspect")
        cands = self.need("candidates", "units")
        udoc = self.need("units", "geometry")
        floors = self.need("floors", "floors")
        val = self.need("validation", "validate")
        ul = self.need("ulpin", "ulpin")
        cad = self.need("cadastral", "cadastral")
        terr = self.need("terrain", "terrain")
        be = self.need("building", "preprocess")
        crs = self.crs()
        self.save("crs", crs)
        und = self.save("underground", load_underground([self.st.external_dir / "underground"]))
        model = build_model(graph=graph, floors=floors, units_doc=cands, units=udoc["units"], common_spaces=cands["common_service_spaces"],
                            ulpins=ul, validation=val, cad_link=cad["building_link"], cad_summary=cad, building_extr=be,
                            underground=und, crs=crs, terrain=terr)
        self.save("model", model)
        self.save("schema", build_schema())
        self.save("viewer", {"note": "viewer/API-ready output manifest (existing viewer/backend untouched)",
                             "model": FILES["model"], "units_geojson": FILES["geojson"],
                             "units_glb": FILES["glb"] if self.path("glb").exists() else None,
                             "ulpins": FILES["ulpin"], "validation": FILES["validation"], "coordinate_reference": crs,
                             "glb_up_axis": "Y (converted from IFC Z-up)"})
        report = self.build_report(graph, cands, udoc, val, ul, cad, terr, und, crs)
        self.save("report", report)
        self.stage_publish()
        return report

    # ---------- flat user-facing outputs + aggregate provenance ----------------------------------
    def stage_publish(self) -> dict:
        """Write processed/*.json (flat), 3d_cadastral_model.geojson and provenance.json from the computed artefacts."""
        graph = self.need("graph", "inspect")
        cands = self.need("candidates", "units")
        udoc = self.need("units", "geometry")
        floors = self.need("floors", "floors")
        val = self.need("validation", "validate")
        ul = self.need("ulpin", "ulpin")
        model = self.need("model", "export")
        be = self.need("building", "preprocess")
        cls = self.need("classification", "classify")
        sg = self.need("space_geometry", "preprocess")
        report = self.need("report", "export")
        inv = self.mem.get("pc_inventory") or (read_json(self.path("pc_inventory")) if self.path("pc_inventory").exists() else {})
        ali = self.mem.get("pc_alignment") or (read_json(self.path("pc_alignment")) if self.path("pc_alignment").exists() else {})
        cov = self.mem.get("pc_coverage") or (read_json(self.path("pc_coverage")) if self.path("pc_coverage").exists() else {})
        cmp_ = self.mem.get("pc_comparison") or (read_json(self.path("pc_comparison")) if self.path("pc_comparison").exists() else {})
        crs = self.crs()
        ulp = {r["property_unit_id"]: r for r in ul["records"]}
        recs = [r for r in sg["spaces"] if r["geometry_status"] != "unavailable"]
        zlo = min((r["z_min"] for r in recs), default=None)
        zhi = max((r["z_max"] for r in recs), default=None)
        lo = [min(r["bounds"][0][i] for r in recs) for i in range(3)] if recs else None
        hi = [max(r["bounds"][1][i] for r in recs) for i in range(3)] if recs else None
        b0 = graph["buildings"][0]
        building = {"building_id": b0["global_id"], "name": b0.get("name"), "storey_count": len(graph["storeys"]),
                    "storeys": [{"storey_id": s["storey_id"], "name": s["name"], "elevation_m": s["elevation_m"], "z_min": s["z_min"],
                                 "z_max": s["z_max"], "z_source": s["z_source"], "space_count": s["space_count"]} for s in floors["storeys"]],
                    "space_envelope_bounds_m": [lo, hi], "z_min": zlo, "z_max": zhi,
                    "height_m": (zhi - zlo) if recs else None, "coordinate_reference": crs,
                    "geometry_basis": "union envelope of IfcSpace geometry (net internal), IFC local metres",
                    "extraction": be, "method_type": "geometry_based", "model_status": "not_trained",
                    "terrain_status": report["terrain_status"], "parcel_id": self.mem.get("cadastral", {}).get("parcel_id"),
                    "parcel_status": "unresolved" if not self.mem.get("cadastral", {}).get("parcel_id") else "linked"}
        self._flat("building", building)
        self._flat("floors", floors)
        self._flat("classification", cls)
        units_flat = []
        for u in udoc["units"]:
            g = u["geometry"]
            units_flat.append({
                "property_unit_id": u["candidate_id"], "label": u["label"], "classification": u["classification"],
                "legal_status": u["legal_status"], "ownership_status": u["ownership_status"],
                "storey_names": u["storey_names"], "storey_ids": u["source_storey_ids"],
                "source_space_ids": u["source_space_ids"], "source_space_names": u["source_space_names"],
                "grouping_evidence": u.get("grouping_evidence"), "confidence_of_grouping": u.get("confidence"),
                "geometry": g, "prototype_ulpin": ulp[u["candidate_id"]]["prototype_ulpin"],
                "validation_state": ulp[u["candidate_id"]]["validation_state"],
                "provenance": {"derivation": "derived/inferred prototype property unit from IfcSpace grouping",
                               "method_type": "rule_based", "model_status": "not_trained",
                               "source_ifc": graph["source_file"], "source_ifc_global_ids": u["source_space_ids"]}})
        self._flat("units", {"classification": "derived/inferred prototype property units (NOT legal cadastral units)",
                             "summary": udoc["summary"], "coordinate_reference": crs, "units": units_flat})
        self._flat("pointcloud", {"inventory": inv, "coverage": cov, "alignment": ali, "ifc_comparison": cmp_})
        self._flat("validation", val)
        self._flat("model", model)
        self._flat("ulpin", ul)
        self._flat("report", report)
        write_json(self.path("model_geojson"), self._model_geojson(units_flat, ul, crs))
        prov = self._provenance(graph, sg, udoc, inv, cmp_, crs)
        self.save("provenance_doc", prov)
        self._flat("provenance", prov)
        return prov

    def _flat(self, key: str, data: Any) -> None:
        write_json(self.st.processed_dir / FLAT[key], data)

    def _model_geojson(self, units_flat: list, ul: dict, crs: dict) -> dict:
        feats = []
        for u in units_flat:
            g = u["geometry"]
            feats.append({"type": "Feature", "geometry": g.get("footprint"),
                          "properties": {"property_unit_id": u["property_unit_id"], "prototype_ulpin": u["prototype_ulpin"],
                                         "storeys": u["storey_names"], "z_min": g.get("z_min"), "z_max": g.get("z_max"),
                                         "height_m": g.get("height_m"), "volume_m3": g.get("volume_m3"),
                                         "geometry_status": g["geometry_status"], "is_fallback": g.get("is_fallback"),
                                         "geometry_confidence": g.get("confidence"), "validation_state": u["validation_state"],
                                         "source_ifc_global_ids": u["source_space_ids"],
                                         "legal_status": "not_legal_cadastral_unit", "ulpin_class": "prototype_not_official"}})
        return {"type": "FeatureCollection", "name": "schependomlaan_3d_cadastral_model_footprints",
                "crs_note": crs, "note": "2D footprints with 3D attributes (z range, volume); frame is IFC local metres, unverified",
                "features": feats}

    @staticmethod
    def _sha256(path: Path | None) -> str | None:
        if not path or not Path(path).is_file():
            return None
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for blk in iter(lambda: f.read(1 << 20), b""):
                h.update(blk)
        return h.hexdigest()

    def _provenance(self, graph, sg, udoc, inv, cmp_, crs) -> dict:
        import importlib.metadata as md
        def ver(n):
            try:
                return md.version(n)
            except Exception:  # noqa: BLE001
                return None
        ifc = self.st.resolve_ifc()
        return {
            "run_timestamp_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "note": "timestamp is informational only; no identifier depends on it",
            "environment": {"python": platform.python_version(), "platform": platform.platform(),
                            **{n: ver(n) for n in ("ifcopenshell", "trimesh", "numpy", "shapely", "scipy", "pyproj", "manifold3d")}},
            "inputs": {"ifc": {"path": str(ifc) if ifc else None, "sha256": self._sha256(ifc), "schema": graph.get("schema"),
                               "length_unit": graph.get("units"), "source_mode": graph["source_mode"]},
                       "pointclouds": [{"name": f["name"], "size_bytes": f["size_bytes"], "parse_status": f.get("parse_status")}
                                       for f in inv.get("files", [])]},
            "methods": {"space_classification": {"method_type": "rule_based", "model_status": "not_applicable"},
                        "building_extraction": {"method_type": "geometry_based", "model_status": "not_trained"},
                        "floor_segmentation": {"method_type": "rule_based", "model_status": "not_trained"},
                        "vertical_property_delineation": {"method_type": "rule_based", "model_status": "not_trained"},
                        "topology_validation": {"method_type": "rule_based"},
                        "ulpin": {"method_type": "deterministic_hash", "official": False},
                        "ml_model_trained": False},
            "geometry": {"space_summary": sg["summary"], "unit_summary": udoc["summary"]},
            "pointcloud_comparison_status": cmp_.get("status"),
            "coordinate_reference": crs,
            "data_availability": {"drone_imagery_available": False, "drone_imagery_used": False,
                                  "cadastral": self.mem.get("cadastral", {}).get("cadastral_status"),
                                  "terrain": self.mem.get("terrain", {}).get("terrain_status"),
                                  "underground": "data_not_available"},
            "legal_notice": "Property units are derived/inferred prototypes; ULPINs are prototype identifiers, not official.",
        }

    def build_report(self, graph, cands, udoc, val, ul, cad, terr, und, crs) -> dict:
        cls = self.need("classification", "classify")
        sg = self.need("space_geometry", "preprocess")
        inv = self.mem.get("pc_inventory") or (read_json(self.path("pc_inventory")) if self.path("pc_inventory").exists() else {})
        ali = self.mem.get("pc_alignment") or (read_json(self.path("pc_alignment")) if self.path("pc_alignment").exists() else {})
        documented = inv.get("documentation", {}).get("mentions", {})
        return {
            "source_mode": graph["source_mode"], "ifc_source": graph["source_file"],
            "buildings": len(graph["buildings"]), "ifc_storeys": len(graph["storeys"]), "ifc_spaces": len(graph["spaces"]),
            "classified_spaces": cls["space_count"], "class_counts": cls["class_counts"],
            "common_service_spaces": len(cands["common_service_spaces"]),
            "inferred_property_units": cands["summary"]["inferred_property_unit_count"],
            "declared_count_check": cands["declared_count_check"],
            "ambiguous_space_names": cands["summary"]["ambiguous_space_names"],
            "space_geometry": sg["summary"], "unit_geometry": udoc["summary"],
            "topology_valid": val["valid"], "topology_errors": val["errors"], "topology_check_status_counts": val["metrics"]["check_status_counts"],
            "pointcloud_files_detected": inv.get("total_detected") or inv.get("legacy_cached_inventory", {}).get("total_detected"),
            "pointcloud_files_processed": inv.get("files_processed", 0),
            "pointcloud_files_git_lfs_pointer": inv.get("files_git_lfs_pointer", 0),
            "pointcloud_status": {"inventory": inv.get("status"), "alignment": ali.get("status"),
                                  "ifc_comparison": (self.mem.get("pc_comparison") or {}).get("status")},
            "cadastral_status": cad["cadastral_status"], "terrain_status": terr["terrain_status"],
            "crs": {k: crs[k] for k in ("coordinate_status", "transformation_status", "vertical_reference", "gnss_cors_control")},
            "drone_imagery": "not_available_and_not_used", "underground_status": und["underground_status"],
            "prototype_3d_ulpins": ul["count"],
        }

    def run(self, stage: str) -> dict:
        if stage == "all":
            for s in STAGES:
                getattr(self, f"stage_{s}")()
            return self.mem["report"]
        return getattr(self, f"stage_{stage}")()


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Schependomlaan prototype 3D cadastre pipeline")
    ap.add_argument("--stage", required=True, choices=STAGES + ["all"])
    ap.add_argument("--ifc", help="path to IFC (default: raw/ifc, $SCHEP_IFC, archive)")
    ap.add_argument("--pointcloud-dir")
    ap.add_argument("--dataset-root")
    a = ap.parse_args(argv)
    p = Pipeline(make_settings(a.dataset_root, a.ifc, a.pointcloud_dir))
    res = p.run(a.stage)
    if a.stage == "all":
        print(json.dumps(res, indent=2, default=str))
    else:
        print(f"stage '{a.stage}' complete -> {p.st.processed_dir}")


if __name__ == "__main__":
    main()
