"""Build and validate the parametric Kingfisher base volume only."""

from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
import trimesh
from shapely.ops import triangulate

from kingfisher_geometry import CREST_START_M, build_architectural_footprint, build_main_body_footprint, load_source_footprint

ROOT = Path(__file__).resolve().parents[1]
DATASETS = ROOT / "Datasets"
OUTPUT_DIR = DATASETS / "derived" / "3d"
OBJ_PATH = OUTPUT_DIR / "kingfisher_building_3d.obj"
GLB_PATH = OUTPUT_DIR / "kingfisher_building_3d.glb"
METADATA_PATH = OUTPUT_DIR / "kingfisher_3d_metadata.json"
TARGET_CRS = "EPSG:32643"
BASE_ELEVATION_M = 826.29
BUILDING_HEIGHT_M = 120.0


def extrude_polygon(footprint, z_min, z_max):
    ring = np.asarray(footprint.exterior.coords[:-1], dtype=np.float64)
    if len(ring) < 3:
        raise ValueError("Footprint has fewer than three vertices")
    triangle_geometries = [triangle for triangle in triangulate(footprint) if triangle.representative_point().within(footprint)]
    if not triangle_geometries:
        raise ValueError("Footprint triangulation produced no interior triangles")
    vertex_indices = {}
    vertices = []

    def vertex_index(x, y, z):
        key = (round(x, 9), round(y, 9), z)
        if key not in vertex_indices:
            vertex_indices[key] = len(vertices)
            vertices.append([x, y, z])
        return vertex_indices[key]

    faces = []
    for triangle in triangle_geometries:
        points = list(triangle.exterior.coords)[:3]
        bottom_indices = [vertex_index(x, y, BASE_ELEVATION_M + z_min) for x, y in points]
        top_indices = [vertex_index(x, y, BASE_ELEVATION_M + z_max) for x, y in points]
        faces.append(list(reversed(bottom_indices)))
        faces.append(top_indices)

    for index in range(len(ring)):
        next_index = (index + 1) % len(ring)
        bottom_a = vertex_index(ring[index, 0], ring[index, 1], BASE_ELEVATION_M + z_min)
        bottom_b = vertex_index(ring[next_index, 0], ring[next_index, 1], BASE_ELEVATION_M + z_min)
        top_a = vertex_index(ring[index, 0], ring[index, 1], BASE_ELEVATION_M + z_max)
        top_b = vertex_index(ring[next_index, 0], ring[next_index, 1], BASE_ELEVATION_M + z_max)
        faces.extend([[bottom_a, bottom_b, top_b], [bottom_a, top_b, top_a]])

    mesh = trimesh.Trimesh(vertices=np.asarray(vertices), faces=np.asarray(faces, dtype=np.int64), process=False)
    mesh.remove_unreferenced_vertices()
    return mesh


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    source_footprint = load_source_footprint()
    main_footprint = build_main_body_footprint(source_footprint)
    crown_footprint = build_architectural_footprint(source_footprint)
    origin = source_footprint.centroid
    components = {
        "main_body": extrude_polygon(main_footprint, 0.0, CREST_START_M),
        "upper_crown": extrude_polygon(crown_footprint, CREST_START_M, BUILDING_HEIGHT_M),
    }
    for mesh in components.values():
        mesh.vertices[:, 0] -= origin.x
        mesh.vertices[:, 1] -= origin.y
        mesh.vertices[:, 2] -= BASE_ELEVATION_M
        if not mesh.is_watertight or not mesh.is_volume:
            raise RuntimeError("Generated base component is not a valid closed volume")

    expected_volume = sum(float(mesh.volume) for mesh in components.values())
    expected_surface_area = sum(float(mesh.area) for mesh in components.values())
    combined_mesh = trimesh.util.concatenate(list(components.values()))
    combined_mesh.export(OBJ_PATH, file_type="obj")
    scene = trimesh.Scene()
    for name, mesh in components.items():
        scene.add_geometry(mesh, node_name=name, geom_name=name)
    scene.export(GLB_PATH, file_type="glb")

    reloaded = trimesh.load(GLB_PATH, force="scene", process=False)
    if not isinstance(reloaded, trimesh.Scene) or set(reloaded.geometry) != set(components):
        raise RuntimeError("Reloaded building GLB did not preserve body and crown components")
    reloaded_meshes = {
        name: {
            "vertices": int(len(mesh.vertices)),
            "faces": int(len(mesh.faces)),
            "watertight": bool(mesh.is_watertight),
            "volume_m3": float(mesh.volume),
            "bounds": mesh.bounds.tolist(),
        }
        for name, mesh in reloaded.geometry.items()
    }

    metadata = {
        "building": "Prestige Kingfisher Towers",
        "source_footprint": "Datasets/processed/buildings/kingfisher_exact_candidate.geojson",
        "crs": TARGET_CRS,
        "parameters": {
            "building_height_m": {
                "value": BUILDING_HEIGHT_M,
                "classification": "PROTOTYPE_PARAMETER",
                "verified": False,
                "note": "Model parameter only; not the verified building height.",
            },
            "base_elevation_m": {
                "value": BASE_ELEVATION_M,
                "classification": "DSM_CONTEXT",
                "verified": False,
                "source": "CartoDEM D43X",
                "note": "Approximate DSM statistic; not a verified foundation elevation.",
            },
        },
        "footprint": {
            "geometry_type": source_footprint.geom_type,
            "valid": source_footprint.is_valid,
            "area_m2": source_footprint.area,
            "perimeter_m": source_footprint.length,
            "centroid_epsg32643": [source_footprint.centroid.x, source_footprint.centroid.y],
            "bounds_epsg32643": list(source_footprint.bounds),
            "source_area_m2": source_footprint.area,
            "profile": "Broad area-preserving main body derived from source dimensions through 30 floors; a short continuous upper crown adds restrained mirrored rear scoops over the top 4 floors.",
            "crest_start_m": CREST_START_M,
            "crest_height_m": BUILDING_HEIGHT_M - CREST_START_M,
            "crown_area_m2": crown_footprint.area,
        },
        "georeference": {
            "crs": TARGET_CRS,
            "origin_x_m": origin.x,
            "origin_y_m": origin.y,
            "origin_z_m": BASE_ELEVATION_M,
            "coordinate_system": "LOCAL_MODEL_COORDINATES",
            "note": "3D mesh vertices are translated relative to this origin for visualization.",
        },
        "mesh": {
            "vertices": int(len(combined_mesh.vertices)),
            "faces": int(len(combined_mesh.faces)),
            "closed": all(component.is_watertight for component in components.values()),
            "watertight": all(component.is_watertight for component in components.values()),
            "valid_volume": all(component.is_volume for component in components.values()),
            "volume_m3": expected_volume,
            "surface_area_m2": expected_surface_area,
            "bounding_box_local": [
                float(combined_mesh.bounds[0, 0]),
                float(combined_mesh.bounds[0, 1]),
                float(combined_mesh.bounds[0, 2]),
                float(combined_mesh.bounds[1, 0]),
                float(combined_mesh.bounds[1, 1]),
                float(combined_mesh.bounds[1, 2]),
            ],
            "x_bounds_m": [float(combined_mesh.bounds[0, 0]), float(combined_mesh.bounds[1, 0])],
            "y_bounds_m": [float(combined_mesh.bounds[0, 1]), float(combined_mesh.bounds[1, 1])],
            "z_min_m": float(combined_mesh.bounds[0, 2]),
            "z_max_m": float(combined_mesh.bounds[1, 2]),
            "components": reloaded_meshes,
            "geometry_repair": "The source-derived main body remains dominant; the symmetric rear-scooped crown is limited to the top four prototype floors.",
        },
        "exports": {
            "obj": "Datasets/derived/3d/kingfisher_building_3d.obj",
            "glb": "Datasets/derived/3d/kingfisher_building_3d.glb",
        },
        "limitations": [
            "Building height is a prototype parameter and is not verified.",
            "Base elevation comes from coarse CartoDEM DSM context.",
            "The model is a volumetric prototype, not a surveyed 3D cadastral model.",
            "No floors, apartments, units, ULPINs, or underground utilities are represented.",
        ],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
