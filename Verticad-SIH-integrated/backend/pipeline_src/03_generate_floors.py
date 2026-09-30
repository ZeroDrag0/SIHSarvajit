"""Generate parametric floor volumes from the Stage 4B base footprint."""

from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
import trimesh
from shapely.ops import triangulate

from kingfisher_geometry import footprint_for_floor, load_source_footprint

ROOT = Path(__file__).resolve().parents[1]
DATASETS = ROOT / "Datasets"
BASE_METADATA_PATH = DATASETS / "derived" / "3d" / "kingfisher_3d_metadata.json"
OUTPUT_DIR = DATASETS / "derived" / "floors"
GLB_PATH = OUTPUT_DIR / "kingfisher_floors.glb"
JSON_PATH = OUTPUT_DIR / "kingfisher_floors.json"
TARGET_CRS = "EPSG:32643"
FLOOR_COUNT = 34
BUILDING_HEIGHT_M = 120.0


def load_local_footprint(metadata, z_min):
    footprint_utm = footprint_for_floor(load_source_footprint(), z_min)
    origin_x = metadata["georeference"]["origin_x_m"]
    origin_y = metadata["georeference"]["origin_y_m"]
    local_ring = [(x - origin_x, y - origin_y) for x, y in footprint_utm.exterior.coords]
    from shapely.geometry import Polygon
    footprint_local = Polygon(local_ring)
    if not footprint_local.is_valid:
        raise ValueError("Local footprint is invalid")
    return footprint_local


def extrude_between(footprint, z_min, z_max):
    ring = np.asarray(footprint.exterior.coords[:-1], dtype=np.float64)
    triangles = [triangle for triangle in triangulate(footprint) if triangle.representative_point().within(footprint)]
    if not triangles:
        raise ValueError("Footprint triangulation produced no interior triangles")
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


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    base_metadata = json.loads(BASE_METADATA_PATH.read_text(encoding="utf-8"))
    floor_height = BUILDING_HEIGHT_M / FLOOR_COUNT
    floor_meshes = []
    floor_records = []

    for number in range(1, FLOOR_COUNT + 1):
        z_min = (number - 1) * floor_height
        z_max = BUILDING_HEIGHT_M if number == FLOOR_COUNT else number * floor_height
        footprint = load_local_footprint(base_metadata, z_min)
        mesh = extrude_between(footprint, z_min, z_max)
        if not mesh.is_watertight or not mesh.is_volume:
            raise RuntimeError(f"Floor F{number:02d} failed watertight volume validation")
        if not np.isclose(mesh.bounds[0, 2], z_min) or not np.isclose(mesh.bounds[1, 2], z_max):
            raise RuntimeError(f"Floor F{number:02d} has unexpected Z bounds")
        floor_id = f"F{number:02d}"
        mesh.metadata["name"] = floor_id
        floor_meshes.append((floor_id, mesh))
        floor_records.append({
            "floor_id": floor_id,
            "floor_number": number,
            "z_min_local_m": z_min,
            "z_max_local_m": z_max,
            "height_m": z_max - z_min,
            "area_m2": footprint.area,
            "volume_m3": float(mesh.volume),
            "vertices": int(len(mesh.vertices)),
            "faces": int(len(mesh.faces)),
            "watertight": bool(mesh.is_watertight),
        })

    scene = trimesh.Scene()
    for floor_id, mesh in floor_meshes:
        scene.add_geometry(mesh, node_name=floor_id, geom_name=floor_id)
    scene.export(GLB_PATH, file_type="glb")

    reloaded = trimesh.load(GLB_PATH, force="scene", process=False)
    if not isinstance(reloaded, trimesh.Scene):
        raise RuntimeError("Reloaded floor GLB is not a scene")
    if len(reloaded.geometry) != FLOOR_COUNT:
        raise RuntimeError("Reloaded floor GLB did not preserve all floor objects")
    for floor_id in [f"F{number:02d}" for number in range(1, FLOOR_COUNT + 1)]:
        geometry = reloaded.geometry.get(floor_id)
        if geometry is None or not geometry.is_watertight:
            raise RuntimeError(f"Reloaded floor {floor_id} failed watertight validation")

    volume_sum = sum(record["volume_m3"] for record in floor_records)
    base_volume = base_metadata["mesh"]["volume_m3"]
    volume_difference = volume_sum - base_volume
    top_z = floor_records[-1]["z_max_local_m"]
    heights_sum = sum(record["height_m"] for record in floor_records)
    if not np.isclose(volume_sum, base_volume, rtol=1e-9, atol=1e-6):
        raise RuntimeError("Floor volumes do not conserve the Stage 4B base volume")
    if not np.isclose(heights_sum, BUILDING_HEIGHT_M, rtol=0, atol=1e-9):
        raise RuntimeError("Floor heights do not sum to the building height")

    report = {
        "building": "Prestige Kingfisher Towers",
        "source_base_model": "Datasets/derived/3d/kingfisher_building_3d.glb",
        "source_metadata": "Datasets/derived/3d/kingfisher_3d_metadata.json",
        "source_footprint": "Datasets/processed/buildings/kingfisher_exact_candidate.geojson",
        "crs": TARGET_CRS,
        "floor_count": {
            "value": FLOOR_COUNT,
            "classification": "PROTOTYPE_PARAMETER",
            "verified": False,
        },
        "building_height_m": {
            "value": BUILDING_HEIGHT_M,
            "classification": "PROTOTYPE_PARAMETER",
            "verified": False,
        },
        "floor_height_m": floor_height,
        "method": "Uniform vertical subdivision of the prototype building volume",
        "footprint": {
            "area_m2": footprint.area,
            "perimeter_m": footprint.length,
        },
        "floors": floor_records,
        "validation": {
            "floor_count": FLOOR_COUNT,
            "volume_sum_m3": volume_sum,
            "base_volume_m3": base_volume,
            "volume_difference_m3": volume_difference,
            "all_floors_watertight": all(record["watertight"] for record in floor_records),
            "top_z_m": top_z,
            "height_sum_m": heights_sum,
            "named_scene_objects": sorted(reloaded.geometry.keys()),
        },
        "limitations": [
            "Floor count is a prototype parameter and is not verified.",
            "Uniform floor height is an approximation.",
            "Actual architectural floor-to-floor heights are not available.",
            "Floor boundaries are derived vertical subdivisions, not surveyed cadastral boundaries.",
            "No apartment boundaries, units, ULPINs, or underground data are represented.",
        ],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    JSON_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"floor_count": FLOOR_COUNT, "floor_height_m": floor_height, "validation": report["validation"], "output": str(JSON_PATH)}, indent=2))


if __name__ == "__main__":
    main()
