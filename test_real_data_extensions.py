"""Tests for the real-data extensions: point-cloud robustness/metrics, boundary corroboration, terrain, OGC API,
flat outputs.  Point-cloud test data here is SYNTHETIC test input only (generated from known geometry); no result
in processed/ is ever derived from it."""
import json
import os
import struct
from pathlib import Path

import numpy as np
import pytest
import trimesh

from Schependomlaan.config import make_settings
from Schependomlaan.pointcloud import compare as pcc
from Schependomlaan.pointcloud import inventory as inv
from Schependomlaan.run_pipeline import Pipeline

REAL_IFC = next((p for p in (os.environ.get("SCHEP_IFC"),
                             str(Path(__file__).resolve().parents[3] / "Archive-DataSetSchependomlaan" / "Design model IFC" / "IFC Schependomlaan.ifc"))
                 if p and Path(p).is_file()), None)


# ----------------------------------------------------------------------------- point-cloud inventory
def _write_ply(path, pts, fmt="binary_little_endian"):
    hdr = f"ply\nformat {fmt} 1.0\nelement vertex {len(pts)}\nproperty float x\nproperty float y\nproperty float z\nend_header\n"
    with open(path, "wb") as f:
        f.write(hdr.encode())
        if fmt == "ascii":
            for p in pts:
                f.write(("%f %f %f\n" % tuple(p)).encode())
        else:
            e = "<" if fmt == "binary_little_endian" else ">"
            f.write(np.asarray(pts, dtype=e + "f4").tobytes())


@pytest.mark.parametrize("fmt", ["binary_little_endian", "binary_big_endian", "ascii"])
def test_ply_formats_inventory(tmp_path, fmt):
    pts = np.random.default_rng(1).uniform([0, 0, 0], [10, 20, 5], (5000, 3))
    _write_ply(tmp_path / "a.ply", pts, fmt)
    d, s = inv.inventory(tmp_path, [])
    f = d["files"][0]
    assert f["parse_status"] == "ok" and f["point_count"] == 5000
    assert np.allclose(f["bounds"], [pts.min(0), pts.max(0)], atol=1e-3)
    assert f["density"]["occupied_cell_fraction_100x100"] > 0 and d["files_processed"] == 1


def test_ascii_xyz_with_extra_columns(tmp_path):
    pts = np.random.default_rng(2).uniform(0, 10, (3000, 3))
    rows = np.c_[pts, np.full((3000, 3), 0.5)]
    np.savetxt(tmp_path / "c.txt", rows, fmt="%.6f")
    d, _ = inv.inventory(tmp_path, [])
    f = d["files"][0]
    assert f["point_count"] == 3000 and f["column_count"] == 6 and f["crs_known"] is False


def test_git_lfs_pointer_is_reported_not_parsed(tmp_path):
    (tmp_path / "big.ply").write_text("version https://git-lfs.github.com/spec/v1\noid sha256:" + "ab" * 32 + "\nsize 205962475\n")
    d, _ = inv.inventory(tmp_path, [])
    f = d["files"][0]
    assert f["parse_status"] == "git_lfs_pointer_not_downloaded" and f["lfs_pointer"]["expected_size_bytes"] == 205962475
    assert d["status"] == "git_lfs_pointers_only" and d["files_processed"] == 0 and f["point_count"] is None


# ----------------------------------------------------------------------------- comparison metrics
def _box_meshes():
    return {"room": trimesh.creation.box(extents=[6, 4, 2.6], transform=trimesh.transformations.translation_matrix([3, 2, 1.3]))}


def test_compare_cloud_known_registration_metrics():
    meshes = _box_meshes()
    rng = np.random.default_rng(3)
    surf, _ = trimesh.sample.sample_surface(meshes["room"], 60000, seed=1)
    cloud_m = surf + rng.normal(0, 0.01, surf.shape)                       # 1 cm noise
    # cloud stored in millimetres with a shift: cloud = (ifc + shift) * 1000
    shift = np.array([100.0, -50.0, 3.0])
    cloud_file = (cloud_m + shift) * 1000.0
    M = np.eye(4); M[:3, 3] = -shift          # cloud(m) -> ifc
    b = meshes["room"].bounds
    res = pcc.compare_cloud("synthetic.ply", cloud_file, len(cloud_file), 0.001, M.tolist(), "test_registration", meshes, b.tolist(),
                            {"match_radius_m": 1.0, "coverage_tolerance_m": 0.10, "surface_sample_spacing_m": 0.05})
    d = res["point_to_surface"]
    assert res["status"] == "computed"
    assert d["mean_m"] < 0.03 and d["rmse_m"] < 0.04 and d["p95_m"] < 0.08 and d["median_m"] < 0.03
    assert res["coverage"]["fraction_of_ifc_surface_samples_with_cloud_point_within_0.1m"] > 0.9
    assert res["vertical"]["cloud_z_range_m"][0] == pytest.approx(0, abs=0.1)


def test_compare_cloud_wrong_alignment_reports_poor_metrics_not_good():
    meshes = _box_meshes()
    surf, _ = trimesh.sample.sample_surface(meshes["room"], 30000, seed=2)
    res = pcc.compare_cloud("shifted.ply", surf + [0.0, 0.0, 0.4], len(surf), 1.0, None, "test", meshes, meshes["room"].bounds.tolist(),
                            {"match_radius_m": 1.0, "coverage_tolerance_m": 0.05, "surface_sample_spacing_m": 0.05})
    assert res["point_to_surface"]["mean_m"] > 0.08       # a 0.4 m offset must not look aligned


def test_pipeline_does_not_fabricate_alignment_for_unregistered_cloud(tmp_path, fixture_ifc):
    pcdir = tmp_path / "pc"; pcdir.mkdir()
    pts = np.random.default_rng(4).uniform([5000, -7000, 400], [30000, 9000, 14000], (4000, 3))   # arbitrary scanner frame
    _write_ply(pcdir / "scan.ply", pts)
    p = Pipeline(make_settings(tmp_path / "ds", fixture_ifc, pcdir))
    p.run("all")
    c = json.loads(p.path("pc_comparison").read_text())
    assert c["files"][0]["status"] == "not_computed_registration_unverified" and "point_to_surface" not in c["files"][0]
    assert json.loads(p.path("pc_inventory").read_text())["files"][0]["crs_known"] is False


def test_pipeline_uses_user_supplied_registration_file(tmp_path, fixture_ifc):
    ds = tmp_path / "ds"
    p0 = Pipeline(make_settings(ds, fixture_ifc)); p0.run("preprocess")
    meshes = p0.meshes()
    pcdir = ds / "external" / "pointcloud"; pcdir.mkdir(parents=True)
    surf = np.vstack([trimesh.sample.sample_surface(m, 4000, seed=5)[0] for m in meshes.values()])
    _write_ply(pcdir / "scan.ply", surf * 1000.0)                                   # millimetres, same origin
    (pcdir / "registration.json").write_text(json.dumps({"registrations": [{"file_name_contains": "scan", "unit_scale_to_m": 0.001,
                                                                           "matrix_4x4": np.eye(4).tolist(), "source": "unit-test"}]}))
    p = Pipeline(make_settings(ds, fixture_ifc, pcdir)); p.run("pointcloud")
    r = json.loads(p.path("pc_comparison").read_text())["files"][0]
    assert r["status"] == "computed" and r["alignment_basis"].startswith("user_supplied_registration")
    assert r["point_to_surface"]["rmse_m"] < 0.1


# ----------------------------------------------------------------------------- terrain
def test_terrain_derivation_with_control_points(tmp_path):
    import rasterio
    from rasterio.transform import from_origin
    from shapely.geometry import box
    from Schependomlaan.terrain.adapter import derive_building_terrain
    from Schependomlaan.crs.handling import fit_helmert_2d_z
    for name, val in (("site_dtm.tif", 1.5), ("site_dsm.tif", 11.9)):
        with rasterio.open(tmp_path / name, "w", driver="GTiff", height=200, width=200, count=1, dtype="float32",
                           crs="EPSG:28992", transform=from_origin(100000, 400200, 1.0, 1.0), nodata=-9999) as dst:
            dst.write(np.full((1, 200, 200), val, dtype="float32"))
    pts = [dict(local_x=0, local_y=0, local_z=0, rd_x=100050, rd_y=400050, nap_z=1.5),
           dict(local_x=10, local_y=0, local_z=0, rd_x=100060, rd_y=400050, nap_z=1.5)]
    h = fit_helmert_2d_z(pts)
    res = derive_building_terrain(sorted(tmp_path.glob("*.tif")), box(2, 2, 8, 8), h, 0.0, 11.62)
    assert res["status"] == "derived"
    assert res["terrain_elevation_m"] == pytest.approx(1.5) and res["roof_elevation_dsm_m"] == pytest.approx(11.9, abs=1e-4)
    assert res["relative_building_height_dsm_minus_dtm_m"] == pytest.approx(10.4, abs=1e-3)
    assert res["building_base_minus_terrain_m"] == pytest.approx(0.0, abs=1e-6)


def test_terrain_not_derived_without_transformation(tmp_path):
    from shapely.geometry import box
    from Schependomlaan.terrain.adapter import derive_building_terrain
    r = derive_building_terrain([], box(0, 0, 5, 5), None, 0, 3)
    assert r["status"] == "not_derived"


# ----------------------------------------------------------------------------- cadastral formats
def test_ogc_api_features_paging(monkeypatch, tmp_path):
    from Schependomlaan.cadastral import adapter as ca
    d = tmp_path / "cadastral"; d.mkdir()
    (d / "ogc_api.json").write_text(json.dumps({"items_url": "https://example.test/collections/perceel/items", "crs": "EPSG:28992", "kind": "parcel"}))
    pages = [{"features": [{"type": "Feature", "properties": {"identificatie": "P1"}, "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]}}],
              "links": [{"rel": "next", "href": "https://example.test/next"}]},
             {"features": [{"type": "Feature", "properties": {"identificatie": "P2"}, "geometry": {"type": "Polygon", "coordinates": [[[20, 0], [30, 0], [30, 10], [20, 10], [20, 0]]]}}], "links": []}]
    monkeypatch.setattr(ca, "_http_get_json", lambda url, headers=None, timeout=30.0: pages.pop(0))
    cad = ca.load_cadastral([d])
    assert cad["parcel_count"] == 2 and cad["files"][0]["source"] == "ogc_api_features"


def test_gpkg_and_gml_are_readable(tmp_path):
    pyogrio = pytest.importorskip("pyogrio")
    import shapely
    from Schependomlaan.cadastral import adapter as ca
    geoms = np.array([shapely.box(0, 0, 5, 5)], dtype=object)
    for ext, drv in ((".gpkg", "GPKG"), (".gml", "GML")):
        try:
            pyogrio.raw.write(str(tmp_path / f"perceel{ext}"), geometry=shapely.to_wkb(geoms), field_data=[np.array(["P-1"])],
                              fields=["identificatie"], geometry_type="Polygon", crs="EPSG:28992", driver=drv)
        except Exception as exc:  # driver unavailable in this GDAL build
            pytest.skip(f"{drv} writer unavailable: {exc}")
        feats, crs = ca._read_features(tmp_path / f"perceel{ext}")
        assert len(feats) == 1 and feats[0]["geom"].area == pytest.approx(25.0)


def test_building_not_associated_with_parcel_without_evidence(pipe):
    link = json.loads(pipe.path("cadastral").read_text())
    assert link["parcel_id"] is None


# ----------------------------------------------------------------------------- outputs
def test_flat_outputs_and_prototype_markers(pipe):
    root = pipe.st.processed_dir
    for name in ("building", "floors", "property_units", "space_classification", "pointcloud_inventory", "topology_validation",
                 "3d_cadastral_model", "ulpins", "provenance", "pipeline_report"):
        assert (root / f"{name}.json").is_file(), name
    assert (root / "cadastre" / "3d_cadastral_model.geojson").is_file()
    ul = json.loads((root / "ulpins.json").read_text())
    for r in ul["records"]:
        assert r["is_official_ulpin"] is False and r["identifier_class"] == "prototype_3d_ulpin"
        g = r["geometry"]
        assert g["z_min"] is not None and g["volume_m3"] > 0 and g["geometry_confidence"] is not None
    prov = json.loads((root / "provenance.json").read_text())
    assert prov["data_availability"]["drone_imagery_available"] is False and prov["data_availability"]["drone_imagery_used"] is False
    assert prov["methods"]["ml_model_trained"] is False and prov["inputs"]["ifc"]["sha256"]
    pu = json.loads((root / "property_units.json").read_text())
    assert "NOT legal" in pu["classification"] and all(u["prototype_ulpin"] for u in pu["units"])


def test_ply_export_roundtrip(pipe):
    m = trimesh.load(str(pipe.path("ply")))
    assert len(m.vertices) > 0 and m.bounds[1][2] > m.bounds[0][2]


def test_space_records_carry_source_and_confidence(pipe):
    sg = json.loads(pipe.path("space_geometry").read_text())
    for r in sg["spaces"]:
        if r["geometry_status"] != "unavailable":
            assert r["geometry_source"] and r["confidence"] > 0 and "boundary_corroboration" in r and r["is_fallback"] in (True, False)


# ----------------------------------------------------------------------------- REAL IFC (skipped when the archive is absent)
@pytest.mark.skipif(REAL_IFC is None, reason="real Schependomlaan IFC not found (set SCHEP_IFC)")
def test_real_ifc_geometry_and_boundary_corroboration(tmp_path):
    p = Pipeline(make_settings(tmp_path / "ds", REAL_IFC))
    p.run("all")
    sg = json.loads(p.path("space_geometry").read_text())["summary"]
    assert sg["space_count"] == 100 and sg["geometry_extracted"] == 100
    assert sg["real_body_geometry"] == 6 and sg["fallback_geometry"] == 94
    assert sg["boundary_corroboration"].get("corroborated", 0) >= 90
    units = json.loads(p.path("units").read_text())["units"]
    assert len(units) == 10 and all(u["geometry"]["volume_m3"] > 100 for u in units)
    fl = json.loads(p.path("floors").read_text())["storeys"]
    assert [s["name"] for s in fl] == ["-1 fundering", "00 begane grond", "01 eerste verdieping", "02 tweede verdieping", "03 derde verdieping", "04 dak"]
    assert max(s["z_max"] or 0 for s in fl) < 20          # real elevations, not the old Kingfisher 120 m
    val = json.loads(p.path("validation").read_text())
    assert val["errors"] == [] and val["checks"]["geometry_provenance"]["status"] == "warning"
