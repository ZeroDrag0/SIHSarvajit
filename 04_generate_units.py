"""Generate deterministic demo unit volumes from prototype floor volumes."""

from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
import trimesh
from shapely.geometry import box
from shapely.ops import triangulate, unary_union
from shapely.geometry.polygon import orient

from kingfisher_geometry import footprint_for_floor, load_source_footprint

ROOT = Path(__file__).resolve().parents[1]
DATASETS = ROOT / "Datasets"
BASE_METADATA_PATH = DATASETS / "derived" / "3d" / "kingfisher_3d_metadata.json"
FLOOR_REPORT_PATH = DATASETS / "derived" / "floors" / "kingfisher_floors.json"
OUTPUT_DIR = DATASETS / "derived" / "units"
GLB_PATH = OUTPUT_DIR / "kingfisher_units.glb"
JSON_PATH = OUTPUT_DIR / "kingfisher_units.json"
TARGET_CRS = "EPSG:32643"
UNITS_PER_FLOOR = 4
CLASSIFICATION = "DERIVED_DEMO_UNIT_PARTITION"
TOLERANCE_M2 = 1e-7
TOLERANCE_M3 = 1e-5


def load_local_footprint(base_metadata, z_min):
    footprint_utm = footprint_for_floor(load_source_footprint(), z_min)
    origin_x = base_metadata["georeference"]["origin_x_m"]
    origin_y = base_metadata["georeference"]["origin_y_m"]
    ring = [(x - origin_x, y - origin_y) for x, y in footprint_utm.exterior.coords]
    from shapely.geometry import Polygon
    footprint_local = Polygon(ring)
    if not footprint_local.is_valid:
        raise ValueError("Local footprint is invalid")
    return footprint_local


def cumulative_area(footprint, y_value):
    min_x, min_y, max_x, _ = footprint.bounds
    return footprint.intersection(box(min_x - 1.0, min_y - 1.0, max_x + 1.0, y_value)).area


def area_quantile_cuts(footprint, count):
    min_x, min_y, max_x, max_y = footprint.bounds
    total_area = footprint.area
    cuts = []
    for part in range(1, count):
        target_area = total_area * part / count
        low = min_y
        high = max_y
        for _ in range(70):
            middle = (low + high) / 2.0
            if cumulative_area(footprint, middle) < target_area:
                low = middle
            else:
                high = middle
        cuts.append((low + high) / 2.0)
    return cuts


def partition_footprint(footprint, count):
    min_x, min_y, max_x, max_y = footprint.bounds
    cuts = area_quantile_cuts(footprint, count)
    boundaries = [min_y] + cuts + [max_y]
    regions = []
    for index in range(count):
        region = footprint.intersection(box(min_x - 1.0, boundaries[index], max_x + 1.0, boundaries[index + 1]))
        if region.geom_type != "Polygon" or not region.is_valid or region.area <= 0:
            raise ValueError(f"Partition region U{index + 1:02d} is not a valid Polygon")
        regions.append(orient(region, sign=1.0))
    return regions, cuts


def extrude_between(footprint, z_min, z_max):
    ring = np.asarray(footprint.exterior.coords[:-1], dtype=np.float64)
    triangles = [triangle for triangle in triangulate(footprint) if triangle.representative_point().within(footprint)]
    if not triangles:
        raise ValueError("Unit triangulation produced no interior triangles")
    vertices = []
    indices = {}

    def vertex_index(x, y, z):
        key = (round(x, 9), round(y, 9), round(z, 9))
        if key not in indices:
            indices[key] = len(vertices)
            vertices.append([x, y, z])
        return indices[key]

    faces = []
    for triangle in triangles:
        points = list(triangle.exterior.coords)[:3]
        bottom = [vertex_index(x, y, z_min) for x, y in points]
        top = [vertex_index(x, y, z_max) for x, y in points]
        faces.extend([list(reversed(bottom)), top])

    for index in range(len(ring)):
        next_index = (index + 1) % len(ring)
        bottom_a = vertex_index(ring[index, 0], ring[index, 1], z_min)
        bottom_b = vertex_index(ring[next_index, 0], ring[next_index, 1], z_min)
        top_a = vertex_index(ring[index, 0], ring[index, 1], z_max)
        top_b = vertex_index(ring[next_index, 0], ring[next_index, 1], z_max)
        faces.extend([[bottom_a, bottom_b, top_b], [bottom_a, top_b, top_a]])

    mesh = trimesh.Trimesh(vertices=np.asarray(vertices), faces=np.asarray(faces, dtype=np.int64), process=False)
    mesh.remove_unreferenced_vertices()
    return mesh


def validate_partition(footprint, regions):
    union = unary_union(regions)
    overlap_area = sum(regions[i].intersection(regions[j]).area for i in range(len(regions)) for j in range(i + 1, len(regions)))
    uncovered_area = footprint.difference(union).area
    area_sum = sum(region.area for region in regions)
    area_difference = area_sum - footprint.area
    valid = (
        all(region.is_valid and region.difference(footprint).area <= TOLERANCE_M2 for region in regions)
        and abs(area_difference) <= TOLERANCE_M2
        and overlap_area <= TOLERANCE_M2
        and uncovered_area <= TOLERANCE_M2
    )
    return {
        "footprint_area_m2": footprint.area,
        "unit_area_sum_m2": area_sum,
        "area_difference_m2": area_difference,
        "overlap_area_m2": overlap_area,
        "uncovered_area_m2": uncovered_area,
        "valid": valid,
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    base_metadata = json.loads(BASE_METADATA_PATH.read_text(encoding="utf-8"))
    floor_report = json.loads(FLOOR_REPORT_PATH.read_text(encoding="utf-8"))
    if floor_report["floor_count"]["value"] != 34:
        raise ValueError("Stage 4C floor count is not the expected 34-floor prototype")

    scene = trimesh.Scene()
    floors = []
    all_unit_volume = 0.0
    all_unit_watertight = True
    for floor in floor_report["floors"]:
        floor_id = floor["floor_id"]
        floor_number = floor["floor_number"]
        z_min = floor["z_min_local_m"]
        z_max = floor["z_max_local_m"]
        footprint = load_local_footprint(base_metadata, z_min)
        regions, cuts = partition_footprint(footprint, UNITS_PER_FLOOR)
        partition_validation = validate_partition(footprint, regions)
        if not partition_validation["valid"]:
            raise RuntimeError(f"Footprint partition failed topology validation for {floor_id}")
        units = []
        floor_volume = 0.0
        for unit_number, region in enumerate(regions, start=1):
            unit_id = f"{floor_id}-U{unit_number:02d}"
            mesh = extrude_between(region, z_min, z_max)
            if not mesh.is_watertight or not mesh.is_volume:
                raise RuntimeError(f"Unit {unit_id} failed watertight volume validation")
            scene.add_geometry(mesh, node_name=unit_id, geom_name=unit_id)
            volume = float(mesh.volume)
            floor_volume += volume
            all_unit_volume += volume
            units.append({
                "unit_id": unit_id,
                "floor_id": floor_id,
                "floor_number": floor_number,
                "unit_number": unit_number,
                "z_min_local_m": z_min,
                "z_max_local_m": z_max,
                "height_m": z_max - z_min,
                "area_m2": region.area,
                "volume_m3": volume,
                "watertight": bool(mesh.is_watertight),
                "classification": CLASSIFICATION,
            })
        floor_volume_difference = floor_volume - floor["volume_m3"]
        if abs(floor_volume_difference) > TOLERANCE_M3:
            raise RuntimeError(f"Floor {floor_id} unit volume does not match floor volume")
        floors.append({
            "floor_id": floor_id,
            "floor_number": floor_number,
            "partition_validation": dict(partition_validation),
            "partition_cut_positions_local_y_m": cuts,
            "unit_volume_sum_m3": floor_volume,
            "floor_volume_m3": floor["volume_m3"],
            "unit_volume_difference_m3": floor_volume_difference,
            "units": units,
        })

    scene.export(GLB_PATH, file_type="glb")
    reloaded = trimesh.load(GLB_PATH, force="scene", process=False)
    if not isinstance(reloaded, trimesh.Scene) or len(reloaded.geometry) != 34 * UNITS_PER_FLOOR:
        raise RuntimeError("Reloaded unit GLB did not preserve all named unit objects")
    all_names = {f"F{floor:02d}-U{unit:02d}" for floor in range(1, 35) for unit in range(1, UNITS_PER_FLOOR + 1)}
    if set(reloaded.geometry) != all_names:
        raise RuntimeError("Reloaded unit GLB names do not match expected unit IDs")
    for geometry in reloaded.geometry.values():
        if not geometry.is_watertight or not geometry.is_volume:
            raise RuntimeError("Reloaded unit GLB contains a non-watertight unit")

    building_volume = base_metadata["mesh"]["volume_m3"]
    volume_difference = all_unit_volume - building_volume
    if abs(volume_difference) > TOLERANCE_M3:
        raise RuntimeError("Total unit volume does not match Stage 4B building volume")

    all_areas = [unit["area_m2"] for floor in floors for unit in floor["units"]]
    report = {
        "building": "Prestige Kingfisher Towers",
        "classification": CLASSIFICATION,
        "parameters": {
            "floor_count": 34,
            "floor_count_classification": "PROTOTYPE_PARAMETER",
            "units_per_floor": UNITS_PER_FLOOR,
            "units_per_floor_classification": "PROTOTYPE_PARAMETER",
            "total_demo_units": 34 * UNITS_PER_FLOOR,
        },
        "source_base_model": "Datasets/derived/3d/kingfisher_building_3d.glb",
        "source_floors": "Datasets/derived/floors/kingfisher_floors.json",
        "source_footprint": "Datasets/processed/buildings/kingfisher_exact_candidate.geojson",
        "crs": TARGET_CRS,
        "partition_method": "Deterministic horizontal Y-band partition using cumulative-area quantile cuts, clipped to the exact Microsoft footprint.",
        "footprint_area_m2": footprint.area,
        "unit_area_summary_m2": {
            "minimum": min(all_areas),
            "maximum": max(all_areas),
            "mean": sum(all_areas) / len(all_areas),
            "total_unit_area_m2": sum(all_areas),
        },
        "floors": floors,
        "global_validation": {
            "total_units": 34 * UNITS_PER_FLOOR,
            "all_unit_geometries_valid": partition_validation["valid"],
            "all_unit_volumes_watertight": all_unit_watertight and all(geometry.is_watertight for geometry in reloaded.geometry.values()),
            "total_unit_volume_m3": all_unit_volume,
            "building_volume_m3": building_volume,
            "volume_difference_m3": volume_difference,
            "uncovered_area_m2": partition_validation["uncovered_area_m2"],
            "overlap_area_m2": partition_validation["overlap_area_m2"],
            "named_scene_objects": sorted(reloaded.geometry),
        },
        "limitations": [
            "Unit boundaries are derived demonstration geometry.",
            "Unit count is a prototype parameter.",
            "No authoritative apartment floor plan was available.",
            "No ownership or legal cadastral information is inferred.",
            "These volumes must not be interpreted as real apartment boundaries.",
            "No real apartment count of 81 was used or asserted.",
        ],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    JSON_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"units_per_floor": UNITS_PER_FLOOR, "total_demo_units": 34 * UNITS_PER_FLOOR, "unit_area_summary_m2": report["unit_area_summary_m2"], "global_validation": report["global_validation"]}, indent=2))


if __name__ == "__main__":
    main()
