"""Generate deterministic prototype ULPIN identifiers from named unit meshes."""

from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import re

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
DATASETS = ROOT / "Datasets"
UNITS_GLB_PATH = DATASETS / "derived" / "units" / "kingfisher_units.glb"
UNITS_REPORT_PATH = DATASETS / "derived" / "units" / "kingfisher_units.json"
BASE_METADATA_PATH = DATASETS / "derived" / "3d" / "kingfisher_3d_metadata.json"
OUTPUT_DIR = DATASETS / "derived" / "ulpin"
REPORT_PATH = OUTPUT_DIR / "kingfisher_ulpin_prototypes.json"
INDEX_PATH = OUTPUT_DIR / "kingfisher_ulpin_index.json"
CLASSIFICATION = "ULPIN_PROTOTYPE"
GEOMETRY_CLASSIFICATION = "DERIVED_DEMO_UNIT_PARTITION"
BUILDING_ID = "B01"
HASH_PRECISION = 6
ID_PATTERN = re.compile(r"^ULPIN-PROTO-(B\d+)-(F\d+)-(U\d+)-([0-9A-F]{8})$")


def canonical_geometry_bytes(mesh):
    vertices = np.round(np.asarray(mesh.vertices, dtype=np.float64), HASH_PRECISION)
    faces = np.asarray(mesh.faces, dtype=np.int64)
    vertex_order = sorted(range(len(vertices)), key=lambda index: tuple(vertices[index]))
    remap = {old: new for new, old in enumerate(vertex_order)}
    sorted_vertices = vertices[vertex_order]
    sorted_faces = np.asarray(sorted((tuple(remap[index] for index in face) for face in faces)), dtype=np.int64)
    payload = {
        "precision": HASH_PRECISION,
        "vertices": sorted_vertices.tolist(),
        "faces": sorted_faces.tolist(),
    }
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("ascii")


def geometry_hash(mesh):
    return hashlib.sha256(canonical_geometry_bytes(mesh)).hexdigest()[:8].upper()


def parse_identifier(identifier):
    match = ID_PATTERN.fullmatch(identifier)
    if not match:
        raise ValueError(f"Identifier cannot be parsed: {identifier}")
    return {
        "building": match.group(1),
        "floor": match.group(2),
        "unit": match.group(3),
        "geometry_hash": match.group(4),
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    unit_report = json.loads(UNITS_REPORT_PATH.read_text(encoding="utf-8"))
    base_metadata = json.loads(BASE_METADATA_PATH.read_text(encoding="utf-8"))
    scene = trimesh.load(UNITS_GLB_PATH, force="scene", process=False)
    if not isinstance(scene, trimesh.Scene):
        raise RuntimeError("Unit GLB did not load as a scene")

    source_units = [unit for floor in unit_report["floors"] for unit in floor["units"]]
    if len(source_units) != 136 or len(scene.geometry) != 136:
        raise RuntimeError("Expected exactly 136 source unit records and GLB objects")

    records = []
    index = {}
    for source in source_units:
        unit_id = source["unit_id"]
        mesh = scene.geometry.get(unit_id)
        if mesh is None:
            raise RuntimeError(f"Unit geometry missing from GLB: {unit_id}")
        if not mesh.is_watertight or not mesh.is_volume:
            raise RuntimeError(f"Unit geometry is not a valid closed volume: {unit_id}")
        digest = geometry_hash(mesh)
        identifier = f"ULPIN-PROTO-{BUILDING_ID}-{source['floor_id']}-{unit_id.split('-')[1]}-{digest}"
        parsed = parse_identifier(identifier)
        if parsed["building"] != BUILDING_ID or parsed["floor"] != source["floor_id"] or parsed["unit"] != unit_id.split("-")[1]:
            raise RuntimeError(f"Identifier hierarchy mismatch: {identifier}")
        record = {
            "ulpin_prototype": identifier,
            "building_id": BUILDING_ID,
            "floor_id": source["floor_id"],
            "floor_number": source["floor_number"],
            "unit_id": unit_id,
            "unit_number": source["unit_number"],
            "classification": CLASSIFICATION,
            "geometry_classification": GEOMETRY_CLASSIFICATION,
            "z_min_local_m": source["z_min_local_m"],
            "z_max_local_m": source["z_max_local_m"],
            "height_m": source["height_m"],
            "area_m2": source["area_m2"],
            "volume_m3": source["volume_m3"],
            "geometry_hash": digest,
            "crs": "EPSG:32643",
            "coordinate_reference": {
                "origin_x_m": base_metadata["georeference"]["origin_x_m"],
                "origin_y_m": base_metadata["georeference"]["origin_y_m"],
                "origin_z_m": base_metadata["georeference"]["origin_z_m"],
            },
            "geometry_reference": {
                "source_glb": "Datasets/derived/units/kingfisher_units.glb",
                "node_name": unit_id,
            },
        }
        records.append(record)
        index[identifier] = {"building_id": BUILDING_ID, "floor_id": source["floor_id"], "unit_id": unit_id}

    identifiers = [record["ulpin_prototype"] for record in records]
    duplicate_count = len(identifiers) - len(set(identifiers))
    if duplicate_count:
        raise RuntimeError("Duplicate prototype identifiers found")
    floor_counts = {}
    for record in records:
        floor_counts.setdefault(record["floor_id"], 0)
        floor_counts[record["floor_id"]] += 1
    if set(floor_counts.values()) != {4} or len(floor_counts) != 34:
        raise RuntimeError("Every floor must have exactly four prototype identifiers")

    recomputed_hashes_match = all(record["geometry_hash"] == geometry_hash(scene.geometry[record["unit_id"]]) for record in records)
    identical_geometry_reproducible = all(
        geometry_hash(scene.geometry[record["unit_id"]]) == geometry_hash(copy.deepcopy(scene.geometry[record["unit_id"]]))
        for record in records
    )
    changed_mesh = scene.geometry[records[0]["unit_id"]].copy()
    changed_mesh.vertices[0, 0] += 0.001
    changed_geometry_changes_hash = geometry_hash(changed_mesh) != records[0]["geometry_hash"]
    parse_success = all(parse_identifier(identifier) for identifier in identifiers)
    if not (recomputed_hashes_match and identical_geometry_reproducible and changed_geometry_changes_hash and parse_success):
        raise RuntimeError("Geometry fingerprint reproducibility validation failed")

    report = {
        "building": "Prestige Kingfisher Towers",
        "classification": CLASSIFICATION,
        "provenance_statement": "These identifiers are prototype identifiers generated for the SIH26011 demonstration. They are not official government-issued ULPINs.",
        "geometry_statement": "Unit geometry is DERIVED_DEMO_UNIT_PARTITION and does not represent verified ownership or legal apartment boundaries.",
        "sources": {
            "unit_glb": "Datasets/derived/units/kingfisher_units.glb",
            "unit_report": "Datasets/derived/units/kingfisher_units.json",
            "base_metadata": "Datasets/derived/3d/kingfisher_3d_metadata.json",
        },
        "identifier_format": "ULPIN-PROTO-B01-F01-U01-XXXXXXXX",
        "geometry_hash": {
            "algorithm": "SHA-256",
            "coordinate_precision_decimal_places": HASH_PRECISION,
            "input": "Canonical sorted local-coordinate vertices and faces from the source unit GLB.",
        },
        "records": records,
        "validation": {
            "total_records": len(records),
            "unique_identifier_count": len(set(identifiers)),
            "duplicate_count": duplicate_count,
            "floors_represented": len(floor_counts),
            "units_per_floor": sorted(set(floor_counts.values())),
            "geometry_hashes_verified": recomputed_hashes_match,
            "identifiers_reproducible": identical_geometry_reproducible and changed_geometry_changes_hash,
            "identifier_parse_success": parse_success,
            "geometry_to_id_linkage_success_rate": 1.0 if all(record["geometry_reference"]["node_name"] in scene.geometry for record in records) else 0.0,
            "every_floor_has_four_ids": all(count == 4 for count in floor_counts.values()),
        },
        "limitations": [
            "These identifiers are not official government-issued ULPINs.",
            "The identifier format is a demonstration convention, not an official cadastral standard.",
            "Unit geometry is derived demonstration geometry and does not represent verified ownership or legal apartment boundaries.",
            "The unit count is a prototype parameter; the unverified value 81 was not used.",
        ],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    INDEX_PATH.write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(json.dumps({"total": len(records), "unique": len(set(identifiers)), "duplicates": duplicate_count, "floors": len(floor_counts), "units_per_floor": 4, "hashes_verified": recomputed_hashes_match, "reproducible": report["validation"]["identifiers_reproducible"], "linkage": report["validation"]["geometry_to_id_linkage_success_rate"], "outputs": [str(REPORT_PATH), str(INDEX_PATH)]}, indent=2))


if __name__ == "__main__":
    main()
