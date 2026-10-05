import copy
import json
import struct

import numpy as np
import pytest

from conftest import load
from Schependomlaan import extraction as ex
from Schependomlaan.apartment_generation.property_units import derive_property_units
from Schependomlaan.cadastral import adapter as cad
from Schependomlaan.classification import classify_spaces, parse_space_name
from Schependomlaan.config import load_rules, make_settings
from Schependomlaan.crs.handling import crs_record, fit_helmert_2d_z
from Schependomlaan.pointcloud.inventory import inventory
from Schependomlaan.preprocessing.ifc_graph import graph_from_legacy_inspection
from Schependomlaan.run_pipeline import Pipeline
from Schependomlaan.ulpin.prototype import encode, generate_prototype_ulpins, geometry_version
from Schependomlaan.underground.model import load_underground
from Schependomlaan.validation.topology import validate_topology

RULES = load_rules()


# ------------------------------------------------------------------ IFC inspection / relationships
def test_ifc_inspection_counts_and_units(pipe):
    s = load(pipe, "structure")
    assert s["source_mode"] == "live_ifc" and s["schema"] == "IFC2X3"
    assert s["entity_counts"]["IfcBuilding"] == 1 and s["entity_counts"]["IfcBuildingStorey"] == 3
    assert s["entity_counts"]["IfcSpace"] == 14
    assert s["units"]["length_scale_to_metre"] == pytest.approx(0.001)


def test_relationship_discovery_does_not_assume_containment(pipe):
    s = load(pipe, "structure")
    assert s["relationship_counts"]["IfcRelContainedInSpatialStructure"] == 0
    assert s["space_storey_resolution"] == {"aggregates": 14}
    rel = load(pipe, "relationships")["relationships"]
    assert len(rel) == 14
    for r in rel:  # Building -> Storey -> candidate group -> IfcSpace traceable for every space
        assert r["building"] and r["storey"] and r["candidate_property_group"]
        assert r["storey_resolved_via"] == "aggregates"


# ------------------------------------------------------------------ classification
def test_name_parsing():
    pat = RULES["space_name"]["pattern"]
    assert parse_space_name("A0.01", pat)["group_key"] == "A0"
    assert parse_space_name("10.08", pat)["group_key"] == "10"
    assert parse_space_name("kitchen", pat) is None


def test_classification_scope_from_composition_not_names(pipe):
    c = load(pipe, "classification")
    by = {(x["space_name"], x["long_name"]): x for x in c["spaces"]}
    assert by[("1.00", "entree")]["classification"] == "private_apartment_space"   # hall inside a dwelling
    assert by[("A0.00", "entree")]["classification"] == "entrance"                  # shared entrance
    assert by[("A0.02", "berging")]["classification"] == "storage"
    assert by[("A1.01", "overloop")]["classification"] == "common_circulation"
    assert c["method"] == "rule_based" and c["model_status"] == "not_trained"


def test_classification_rules_are_configurable():
    rules = copy.deepcopy(RULES)
    rules["lexicon"]["dwelling_signature"] = ["xyz"]            # nothing looks like a dwelling any more
    g = _graph([("1.01", "keuken", "S0"), ("1.02", "woonkamer", "S0")])
    assert classify_spaces(g, rules)["class_counts"].get("private_apartment_space", 0) == 0
    assert classify_spaces(g, RULES)["class_counts"]["private_apartment_space"] == 2


# ------------------------------------------------------------------ apartment grouping
def test_grouping_is_not_one_unit_per_space(pipe):
    c = load(pipe, "candidates")
    assert c["summary"]["ifc_space_count"] == 14
    assert c["summary"]["inferred_property_unit_count"] == 3 < 14
    for u in c["candidates"]:
        assert u["status"] == "inferred" and u["classification"] == "derived/inferred prototype property unit"
        assert u["legal_status"] == "not_a_legal_cadastral_unit"
        assert len(u["source_space_ids"]) >= 3
    assert c["declared_count_check"]["agrees"] is True


def test_unit_count_follows_evidence_not_a_constant():
    for n in (2, 4, 7):
        rows = [(f"{k}.0{j}", r, "S0") for k in range(1, n + 1) for j, r in enumerate(["entree", "keuken", "woonkamer"])]
        g = _graph(rows)
        u = derive_property_units(g, classify_spaces(g, RULES), RULES)
        assert u["summary"]["inferred_property_unit_count"] == n
        assert u["declared_count_check"]["declared_in_ifc_project_name"] is None


def test_duplicate_space_resolved_by_geometry_and_reported(pipe):
    c = load(pipe, "candidates")
    pu2 = next(u for u in c["candidates"] if u["candidate_id"] == "PU-02")
    assert any(e["signal"] == "geometry_reassignment" for e in pu2["grouping_evidence"])
    assert sum(1 for s in pu2["spaces"] if s["name"] == "1.02") == 1
    pu1 = next(u for u in c["candidates"] if u["candidate_id"] == "PU-01")
    assert [s["name"] for s in pu1["spaces"]].count("1.02") == 1
    assert c["summary"]["reassigned_by_geometry"] == 1


def test_duplicate_without_geometry_is_flagged_with_hint():
    rows = [(f"{k}.0{j}", r, "S0") for k in (1, 3) for j, r in enumerate(["entree", "toilet", "keuken", "woonkamer"])]
    rows += [("2.00", "entree", "S0"), ("2.02", "keuken", "S0"), ("2.03", "woonkamer", "S0"), ("1.01", "toilet", "S0")]
    g = _graph(rows)
    u = derive_property_units(g, classify_spaces(g, RULES), RULES)
    pu1 = next(x for x in u["candidates"] if x["candidate_id"] == "PU-01")
    assert any("ambiguous membership" in w for w in pu1["warnings"])
    assert any(e["signal"] == "sequence_gap_hint" for e in pu1["grouping_evidence"])
    assert pu1["confidence"] <= RULES["grouping"]["max_confidence_without_geometry"]


# ------------------------------------------------------------------ floors
def test_floor_mapping_measured_vs_nominal(pipe):
    f = {s["name"]: s for s in load(pipe, "floors")["storeys"]}
    g, one, roof = f["00 begane grond"], f["01 eerste verdieping"], f["04 dak"]
    assert g["z_source"] == "measured_space_geometry" and g["z_min"] == pytest.approx(0) and g["z_max"] == pytest.approx(2.6)
    assert one["z_min"] == pytest.approx(3.0) and one["height_m"] == pytest.approx(2.6)
    assert g["nominal_height_m"] == pytest.approx(3.0)
    assert roof["z_source"] == "nominal_ifc_elevation" and roof["space_count"] == 0
    u3 = next(u for u in load(pipe, "candidates")["candidates"] if u["candidate_id"] == "PU-03")
    assert u3["storey_names"] == ["01 eerste verdieping"]


# ------------------------------------------------------------------ geometry
def test_space_geometry_methods_and_placement(pipe):
    sg = {(s["space_name"], tuple(np.round(s.get("bounds", [[0] * 3])[0], 2))): s for s in load(pipe, "space_geometry")["spaces"]}
    body = sg[("1.00", (0.0, 0.0, 0.0))]
    assert body["method"] == "ifc_body_mesh" and body["geometry_status"] == "valid"
    fb = sg[("2.00", (10.0, 0.0, 0.0))]                         # fallback must honour ObjectPlacement (x = 10 m)
    assert fb["method"] == "footprint_box_extrusion" and fb["geometry_status"] == "fallback"
    assert fb["volume_m3"] == pytest.approx(31.2)
    assert any(s["geometry_status"] == "unavailable" and s["space_name"] == "A0.02" for s in load(pipe, "space_geometry")["spaces"])
    assert load(pipe, "space_geometry")["summary"]["success_rate"] == pytest.approx(13 / 14, abs=1e-3)


def test_unit_geometry_is_real_3d_not_bbox(pipe):
    units = {u["candidate_id"]: u for u in load(pipe, "units")["units"]}
    g = units["PU-01"]["geometry"]
    assert g["representation"] == "boolean_union" and g["geometry_status"] == "valid"
    assert g["volume_m3"] == pytest.approx(4 * 31.2, rel=1e-3)
    assert g["z_min"] == pytest.approx(0) and g["z_max"] == pytest.approx(2.6)
    assert g["footprint"]["type"] in ("MultiPolygon", "Polygon") and g["footprint_area_m2"] == pytest.approx(48.0, rel=1e-3)
    assert units["PU-02"]["geometry"]["geometry_status"] == "fallback"           # marked, not hidden
    assert pipe.path("glb").exists() and pipe.path("geojson").exists()
    assert load(pipe, "units")["summary"]["geometry_success_rate"] == 1.0


# ------------------------------------------------------------------ topology validation
def test_topology_valid_on_clean_fixture(pipe):
    v = load(pipe, "validation")
    assert set(v) >= {"valid", "errors", "warnings", "checks", "metrics"}
    assert v["valid"] is True and v["errors"] == []
    for name in ("duplicate_units", "invalid_geometry", "self_intersections", "zero_negative_volume", "volumetric_overlap",
                 "building_containment", "storey_unit_consistency", "z_order_consistency", "vertical_overlap"):
        assert v["checks"][name]["status"] == "passed", name
    assert v["checks"]["parcel_building_consistency"]["status"] == "not_applicable"


def _units(pipe):
    return copy.deepcopy(load(pipe, "units")["units"])


def _validate(pipe, units, meshes=None, spaces=None):
    sg = spaces or load(pipe, "space_geometry")
    cands = load(pipe, "candidates")
    return validate_topology(units, sg, pipe.meshes() if meshes is None else meshes, load(pipe, "floors"),
                             [s["global_id"] for s in cands["common_service_spaces"]], None, "not_available", None, RULES)


def test_topology_detects_overlap_between_units(pipe):
    sg = copy.deepcopy(load(pipe, "space_geometry"))
    meshes = pipe.meshes()
    units = _units(pipe)
    # move one room of PU-03 (storey 1) down into storey 0 so it intersects a room of PU-01
    gid = units[2]["source_space_ids"][0]
    m = meshes[gid].copy()
    m.apply_translation([1.0, 0.5, -3.0])
    rec = next(r for r in sg["spaces"] if r["space_global_id"] == gid)
    rec["bounds"] = m.bounds.tolist(); rec["z_min"], rec["z_max"] = float(m.bounds[0][2]), float(m.bounds[1][2])
    meshes = {**meshes, gid: m}
    v = _validate(pipe, units, meshes, sg)
    assert v["valid"] is False and v["checks"]["volumetric_overlap"]["status"] == "failed"
    assert v["checks"]["volumetric_overlap"]["items"][0]["method"] == "exact_boolean"


def test_topology_detects_duplicates_and_bad_storey(pipe):
    units = _units(pipe)
    units.append(copy.deepcopy(units[0]) | {"candidate_id": "PU-DUP"})
    assert _validate(pipe, units)["checks"]["duplicate_units"]["status"] == "failed"
    units = _units(pipe)
    units[0]["source_storey_ids"] = ["nonexistent"]
    v = _validate(pipe, units)
    assert v["checks"]["storey_unit_consistency"]["status"] == "failed" and not v["valid"]


def test_topology_detects_zero_volume_and_z_order(pipe):
    units = _units(pipe)
    units[0]["geometry"]["volume_m3"] = 0.0
    assert _validate(pipe, units)["checks"]["zero_negative_volume"]["status"] == "failed"
    units = _units(pipe)
    units[2]["geometry"]["centroid"][2] = -50.0         # upper-storey unit below ground-floor units
    assert _validate(pipe, units)["checks"]["z_order_consistency"]["status"] == "failed"


def test_validity_never_true_when_geometry_missing(pipe):
    units = _units(pipe)
    units[1]["geometry"] = {"geometry_status": "unavailable", "representation": None}
    v = _validate(pipe, units)
    assert v["valid"] is False and v["checks"]["invalid_geometry"]["status"] == "incomplete"
    assert any("required_check_not_run" in e for e in v["errors"])


# ------------------------------------------------------------------ ULPIN, provenance
def test_ulpin_deterministic_and_structured(pipe):
    a, b = load(pipe, "ulpin"), pipe.stage_ulpin()
    assert [r["prototype_ulpin"] for r in a["records"]] == [r["prototype_ulpin"] for r in b["records"]]
    assert len({r["prototype_ulpin"] for r in a["records"]}) == a["count"] == 3
    r = a["records"][0]
    assert r["prototype_ulpin"].startswith("P3D-") and r["identity"]["parcel_id"] is None
    assert r["legal_status"] == "not_official_prototype_identifier" and "NOT an official" in a["disclaimer"]
    assert encode(r["identity"]) == r["prototype_ulpin"]
    assert r["crs"]["coordinate_status"] == "local/unverified"
    assert r["validation_status"] == "validated"


def test_ulpin_changes_with_geometry_version(pipe):
    units = _units(pipe)
    idn = {"scheme": "x", "geometry_version": geometry_version(units[0])}
    units[0]["geometry"]["z_max"] += 0.5
    assert geometry_version(units[0]) != idn["geometry_version"]


def test_provenance_everywhere(pipe):
    m = load(pipe, "model")
    for u in m["property_units"]:
        p = u["provenance"]
        assert p["data_status"] == "inferred" and p["source_ifc_global_ids"] and p["derivation_method"]
        assert p["coordinate_reference"]["coordinate_status"] == "local/unverified"
        assert u["ownership_status"] == "unknown_not_provided"
    assert m["parcels"][0]["provenance"]["data_status"] == "unavailable"


def test_cadastral_model_matches_schema_and_hierarchy(pipe):
    import jsonschema
    m, s = load(pipe, "model"), load(pipe, "schema")
    jsonschema.validate(m, s)
    assert m["hierarchy_order"] == ["Parcel", "Building", "Storey", "VerticalPropertyUnit", "IfcSpace"]
    assert m["hierarchy"][0]["parcel"] is None
    leaf = m["hierarchy"][0]["buildings"][0]["storeys"][0]["units"][0]
    assert leaf["prototype_ulpin"].startswith("P3D-") and leaf["ifc_spaces"]


# ------------------------------------------------------------------ optional datasets / CRS / cadastral
def test_missing_optional_datasets_are_not_fatal(pipe):
    r = load(pipe, "report")
    assert r["cadastral_status"] == "not_available" and r["terrain_status"] == "not_available"
    assert r["underground_status"] == "data_not_available" and r["drone_imagery"] == "not_available_and_not_used"
    assert load(pipe, "cadastral")["parcel_id"] is None
    assert load(pipe, "underground")["entities"] == []
    assert load(pipe, "pc_alignment")["status"] == "no_pointcloud_files_accessible"


def test_crs_never_invented(pipe):
    c = load(pipe, "crs")
    assert c["coordinate_status"] == "local/unverified" and c["transformation_status"] == "not_performed"
    assert c["gnss_cors_control"] == "not_available" and c["target_crs"] is None


def test_helmert_fit_recovers_known_transform():
    rot, sc, tx, ty = 0.3, 1.0, 155000.0, 463000.0
    pts = []
    for x, y in [(0, 0), (10, 0), (0, 8), (12, 9)]:
        pts.append({"local_x": x, "local_y": y, "local_z": 0.0, "nap_z": 1.5,
                    "rd_x": tx + sc * (np.cos(rot) * x - np.sin(rot) * y), "rd_y": ty + sc * (np.sin(rot) * x + np.cos(rot) * y)})
    fit = fit_helmert_2d_z(pts)
    assert fit["status"] == "fitted" and fit["rmse_m"] < 1e-6 and fit["rotation_rad"] == pytest.approx(rot) and fit["dz"] == 1.5
    assert fit_helmert_2d_z(pts[:1])["status"] == "insufficient_control_points"
    assert crs_record(control_points=pts)["transformation_status"] == "not_performed"


def _parcel_geojson(path):
    path.write_text(json.dumps({"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "EPSG:28992"}}, "features": [
        {"type": "Feature", "properties": {"kadastraleAanduiding": "NMG00 A 1234"},
         "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [30, 0], [30, 20], [0, 20], [0, 0]]]}}]}))


def test_cadastral_adapter(tmp_path):
    d = tmp_path / "cadastral"; d.mkdir()
    absent = cad.load_cadastral([d])
    assert absent["cadastral_status"] == "not_available" and cad.associate(absent, {"global_id": "B"})["parcel_id"] is None
    _parcel_geojson(d / "brk.geojson")
    loaded = cad.load_cadastral([d])
    assert loaded["parcel_count"] == 1
    unlinked = cad.associate(loaded, {"global_id": "B"})
    assert unlinked["parcel_id"] is None and unlinked["cadastral_status"] == "supplied_not_linked"       # no invention
    (d / "building_parcel_link.json").write_text(json.dumps({"building_global_id": "B", "parcel_id": "NMG00 A 1234", "bag_id": "0123"}))
    linked = cad.associate(cad.load_cadastral([d]), {"global_id": "B"})
    assert linked["parcel_id"] == "NMG00 A 1234" and linked["link_basis"] == "explicit_link_file"
    from shapely.geometry import box
    (d / "building_parcel_link.json").unlink()
    geo = cad.associate(cad.load_cadastral([d]), {"global_id": "B"}, box(5, 5, 15, 12), "EPSG:28992")
    assert geo["parcel_id"] == "NMG00 A 1234" and geo["link_basis"] == "geometric_intersection"
    assert geo["parcel_building_intersection"]["overlap_fraction_of_building"] == pytest.approx(1.0)


def test_cadastral_flows_into_ulpin_and_model(tmp_path, fixture_ifc):
    ds = tmp_path / "ds"; (ds / "external" / "cadastral").mkdir(parents=True)
    _parcel_geojson(ds / "external" / "cadastral" / "brk.geojson")
    gid = None
    p = Pipeline(make_settings(ds, fixture_ifc)); g = p.stage_inspect(); gid = g["buildings"][0]["global_id"]
    (ds / "external" / "cadastral" / "building_parcel_link.json").write_text(json.dumps({"building_global_id": gid, "parcel_id": "NMG00 A 1234"}))
    p.run("all")
    m = load(p, "model")
    assert m["parcels"][0]["parcel_id"] == "NMG00 A 1234" and m["property_units"][0]["parcel_ref"] == "NMG00 A 1234"
    assert load(p, "ulpin")["records"][0]["identity"]["parcel_id"] == "NMG00 A 1234"


def test_underground_adapter(tmp_path):
    d = tmp_path / "ug"; d.mkdir()
    assert load_underground([d])["underground_status"] == "data_not_available"
    (d / "u.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {
        "entity_id": "U1", "type": "utility", "z_min": -3.0, "z_max": -1.0},
        "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}}]}))
    r = load_underground([d])
    e = r["entities"][0]
    assert e["entity_id"] == "U1" and e["ownership_status"] == "unknown_not_provided" and e["provenance"]["data_status"] == "unverified"
    assert {"geometry", "z_min", "z_max", "type", "source", "confidence", "legal_status", "ownership_status", "provenance"} <= set(e)


# ------------------------------------------------------------------ extraction architecture
def test_extraction_interfaces_never_fabricate_ml():
    for task in ex.REGISTRY:
        t = ex.get(task, "trained_model")
        assert t.model_status == "not_trained"
        with pytest.raises(ex.ModelNotAvailable):
            t.run()
    assert {x.method for x in ex.REGISTRY["vertical_property_delineation"].values()} >= {"rule_based", "ml_model"}
    assert ex.get("building_extraction", "ifc_space_envelope").method == "geometry_based"


# ------------------------------------------------------------------ point clouds
def _write_ply(p, pts):
    hdr = ("ply\nformat binary_little_endian 1.0\ncomment synthetic test\n" f"element vertex {len(pts)}\n"
           "property float x\nproperty float y\nproperty float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n")
    with open(p, "wb") as f:
        f.write(hdr.encode())
        for x, y, z in pts:
            f.write(struct.pack("<fffBBB", x, y, z, 1, 2, 3))


def test_pointcloud_inventory_formats(tmp_path):
    import laspy
    d = tmp_path / "pc"; d.mkdir()
    rng = np.random.default_rng(0)
    pts = rng.uniform([0, 0, 0], [20, 10, 12], (500, 3))
    _write_ply(d / "a.ply", pts.tolist())
    np.savetxt(d / "b.txt", np.c_[pts, np.full((500, 3), 100)], fmt="%.6f")
    las = laspy.create(point_format=3, file_version="1.4"); las.x, las.y, las.z = pts[:, 0], pts[:, 1], pts[:, 2]; las.write(str(d / "c.las"))
    inv, samples = inventory(d, [], 100)
    assert inv["total_detected"] == 3 and inv["format_summary"] == {"ply": 1, "ascii_text": 1, "las": 1}
    for f in inv["files"]:
        assert f["parse_status"] == "ok" and f["point_count"] == 500 and f["crs_known"] is False
        assert f["z_range"][1] == pytest.approx(pts[:, 2].max(), abs=1e-2)
        assert f["bounds_exact"] is True
    assert "not asserted" in inv["acquisition_statement"]
    assert "lidar" not in inv["acquisition_statement"].lower()          # no documentation => no LiDAR claim
    assert "lidar" not in inv["documentation"]["mentions"]


def test_pointcloud_lidar_only_if_documented(tmp_path):
    d = tmp_path / "pc"; d.mkdir(); _write_ply(d / "a.ply", [(0, 0, 0), (1, 1, 1)])
    doc = tmp_path / "doc"; doc.mkdir(); (doc / "README.md").write_text("Point clouds captured by drone photogrammetry (SfM).")
    inv, _ = inventory(d, [doc], 10)
    assert "photogrammetry_sfm" in inv["documentation"]["mentions"] and "lidar" not in inv["documentation"]["mentions"]
    assert "LiDAR" not in inv["acquisition_statement"]


def test_pointcloud_alignment_units_and_registration(tmp_path):
    from Schependomlaan.pointcloud.inventory import coverage_and_alignment
    d = tmp_path / "pc"; d.mkdir()
    rng = np.random.default_rng(1)
    mm = rng.uniform([8000, -6000, 0], [28000, 4000, 12000], (400, 3))          # a scan in mm, other frame
    _write_ply(d / "mm.ply", mm.tolist())
    inv, smp = inventory(d, [], 400)
    cov, ali = coverage_and_alignment(inv, smp, [[0, 0, 0], [18.1, 6.1, 5.6]], None, RULES)
    assert ali["files"][0]["best_scale_candidate"] == "millimetres"
    assert ali["files"][0]["status"] == "size_compatible_but_unregistered"
    assert "no registration" in ali["method"] and "registration" in ali["files"][0]["note"]


# ------------------------------------------------------------------ cached (no IFC) mode
def _legacy():
    sp = [{"ifc_global_id": f"G{k}{j}", "name": f"{k}.0{j}", "long_name": r, "parent_storey": "S0", "geometry": {"extracted": False}}
          for k in (1, 2) for j, r in enumerate(["entree", "keuken", "woonkamer"])]
    sp.append({"ifc_global_id": "GA", "name": "A0.00", "long_name": "entree", "parent_storey": "S0", "geometry": {"extracted": True, "volume_m3": 5.0, "bounds": None}})
    return {"source_ifc": "x.ifc", "schema": "IFC2X3", "project_name": "2 Appartementen", "building_count": 1, "storey_count": 1, "space_count": 7,
            "buildings": [{"ifc_global_id": "B", "name": "Building"}], "storeys": [{"ifc_global_id": "S0", "name": "00", "elevation": 0.0}],
            "spaces": sp, "ifc_units": [{"units": [{"unit_type": "LENGTHUNIT", "prefix": "MILLI"}]}]}


def test_cached_mode_runs_but_never_claims_valid(tmp_path):
    ds = tmp_path / "ds"; (ds / "processed" / "ifc").mkdir(parents=True)
    (ds / "processed" / "ifc" / "schependomlaan_inspection.json").write_text(json.dumps(_legacy()))
    p = Pipeline(make_settings(ds, tmp_path / "does_not_exist.ifc"))
    p.st.resolve_ifc = lambda: None
    rep = p.run("all")
    assert p.mem["graph"]["source_mode"] == "cached_legacy_inspection"
    assert rep["inferred_property_units"] == 2 and rep["unit_geometry"]["geometry_success_rate"] == 0.0
    assert rep["topology_valid"] is False
    v = load(p, "validation")
    assert any("required_check_not_run" in e for e in v["errors"])
    assert all(r["validation_status"] == "not_validated" for r in load(p, "ulpin")["records"])
    assert not p.path("glb").exists()


# ------------------------------------------------------------------ independent stages
@pytest.mark.parametrize("stage", ["inspect", "preprocess", "classify", "floors", "units", "geometry", "pointcloud", "cadastral",
                                   "terrain", "validate", "ulpin", "export"])
def test_each_stage_runs_independently(tmp_path, fixture_ifc, stage):
    p = Pipeline(make_settings(tmp_path / "ds", fixture_ifc))
    p.run(stage)
    assert p.path({"inspect": "graph", "preprocess": "space_geometry", "classify": "classification", "floors": "floors",
                   "units": "candidates", "geometry": "units", "pointcloud": "pc_inventory", "cadastral": "cadastral",
                   "terrain": "terrain", "validate": "validation", "ulpin": "ulpin", "export": "model"}[stage]).exists()


# ------------------------------------------------------------------ helpers
def _graph(rows):
    sp = [{"global_id": f"G{i}", "name": n, "long_name": r, "storey_id": s, "building_id": "B", "zones": [], "psets": {}, "boundaries": [],
           "description": None} for i, (n, r, s) in enumerate(rows)]
    return {"source_mode": "test", "project": {"name": "t"}, "storeys": [{"global_id": "S0", "name": "00", "elevation_m": 0.0, "building_id": "B"}],
            "buildings": [{"global_id": "B", "name": "b"}], "spaces": sp, "zones": []}
