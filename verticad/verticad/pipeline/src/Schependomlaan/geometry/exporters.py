from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import trimesh


def units_geojson(units: list[dict[str, Any]], crs_info: dict[str, Any]) -> dict[str, Any]:
    feats = []
    for u in units:
        g = u["geometry"]
        feats.append({
            "type": "Feature",
            "geometry": g.get("footprint"),
            "properties": {
                "candidate_id": u["candidate_id"], "status": u["status"], "label": u["label"],
                "storeys": u["storey_names"], "z_min": g.get("z_min"), "z_max": g.get("z_max"),
                "height_m": g.get("height_m"), "volume_m3": g.get("volume_m3"),
                "geometry_status": g["geometry_status"], "source_ifc_global_ids": u["source_space_ids"],
                "legal_status": "not_legal_cadastral_unit",
            },
        })
    return {"type": "FeatureCollection", "name": "schependomlaan_property_units",
            "crs_note": crs_info, "features": feats}


def export_glb(named_meshes: dict[str, trimesh.Trimesh], path: str | Path) -> None:
    """Write GLB with glTF Y-up convention (x, z, -y) so a Three.js viewer shows it upright."""
    scene = trimesh.Scene()
    rot = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], dtype=float)
    for name, m in named_meshes.items():
        mm = m.copy()
        mm.apply_transform(rot)
        scene.add_geometry(mm, geom_name=name, node_name=name)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(scene.export(file_type="glb"))


def export_ply(named_meshes: dict[str, trimesh.Trimesh], path: str | Path) -> None:
    """Single binary PLY (Z-up, IFC metres) of all unit meshes with one deterministic colour per unit."""
    parts = []
    for i, (name, m) in enumerate(sorted(named_meshes.items())):
        mm = m.copy()
        h = (i * 0.61803398875) % 1.0
        import colorsys
        r, g, b = colorsys.hsv_to_rgb(h, 0.55, 0.9)
        mm.visual.face_colors = np.tile(np.array([int(r * 255), int(g * 255), int(b * 255), 255], dtype=np.uint8), (len(mm.faces), 1))
        parts.append(mm)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(trimesh.util.concatenate(parts).export(file_type="ply"))
