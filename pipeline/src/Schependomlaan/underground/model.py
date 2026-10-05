"""Volumetric entity model for underground / subsurface cadastre (adapter only; nothing fabricated)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from shapely.geometry import mapping, shape

TYPES = ["basement", "foundation", "utility", "tunnel", "subsurface_corridor", "other_volumetric"]


@dataclass
class VolumetricEntity:
    entity_id: str
    type: str
    geometry: dict[str, Any] | None
    z_min: float | None
    z_max: float | None
    source: str
    confidence: float | None = None
    legal_status: str = "unknown"
    ownership_status: str = "unknown_not_provided"
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_underground(dirs: list[Path]) -> dict[str, Any]:
    files = [p for d in dirs if d.is_dir() for p in sorted(d.rglob("*.geojson"))]
    if not files:
        return {"underground_status": "data_not_available", "entities": [],
                "supported_types": TYPES,
                "notes": ["no authoritative underground/subsurface source supplied; none fabricated. Place GeoJSON features "
                          "with properties {entity_id,type,z_min,z_max,legal_status,ownership_status} in external/underground/"]}
    ents, errs = [], []
    for p in files:
        d = json.loads(p.read_text(encoding="utf-8"))
        for i, f in enumerate(d.get("features", [])):
            pr = f.get("properties") or {}
            try:
                g = shape(f["geometry"]) if f.get("geometry") else None
                ents.append(VolumetricEntity(
                    entity_id=str(pr.get("entity_id", f"{p.stem}-{i}")), type=pr.get("type", "other_volumetric"),
                    geometry=mapping(g) if g else None, z_min=pr.get("z_min"), z_max=pr.get("z_max"),
                    source=p.name, confidence=pr.get("confidence"), legal_status=pr.get("legal_status", "unknown"),
                    ownership_status=pr.get("ownership_status", "unknown_not_provided"),
                    provenance={"source_file": p.name, "data_status": "unverified", "supplied_locally": True}).to_dict())
            except Exception as exc:  # noqa: BLE001
                errs.append(f"{p.name}[{i}]: {type(exc).__name__}: {exc}")
    return {"underground_status": "supplied" if ents else "supplied_unreadable", "entities": ents, "errors": errs,
            "supported_types": TYPES}
