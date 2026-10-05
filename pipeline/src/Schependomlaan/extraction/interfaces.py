"""Extensible extraction architecture.

Three task interfaces (building extraction, floor segmentation, vertical property delineation)
with *registered implementations*.  The demonstrator ships only deterministic implementations
(method = rule_based | geometry_based).  A trained ML model can be plugged in by subclassing and
calling `register(...)`; until then `TrainedModelAdapter` reports model_status = "not_trained"
and never emits predictions.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from shapely.geometry import mapping, shape
from shapely.ops import unary_union

REGISTRY: dict[str, dict[str, "Extractor"]] = {"building_extraction": {}, "floor_segmentation": {}, "vertical_property_delineation": {}}


class ModelNotAvailable(RuntimeError):
    pass


class Extractor(ABC):
    task: str = ""
    name: str = ""
    method: str = "rule_based"          # rule_based | geometry_based | ml_model
    model_status: str = "not_applicable"

    @abstractmethod
    def run(self, **inputs: Any) -> dict[str, Any]: ...

    def describe(self) -> dict[str, str]:
        return {"task": self.task, "name": self.name, "method": self.method, "model_status": self.model_status}


def register(ext: Extractor) -> Extractor:
    REGISTRY[ext.task][ext.name] = ext
    return ext


def get(task: str, name: str) -> Extractor:
    return REGISTRY[task][name]


class TrainedModelAdapter(Extractor):
    """Placeholder for a future trained model. Never fabricates predictions."""
    method = "ml_model"
    model_status = "not_trained"

    def __init__(self, task: str, name: str = "trained_model", weights_path: str | None = None):
        self.task, self.name, self.weights_path = task, name, weights_path

    def run(self, **inputs):
        raise ModelNotAvailable(f"No trained model for '{self.task}' (model_status=not_trained). "
                                "Provide a model by subclassing Extractor and registering it.")


class IfcGeometryBuildingExtractor(Extractor):
    task, name, method = "building_extraction", "ifc_space_envelope", "geometry_based"

    def run(self, *, graph: dict, space_geom: dict | None = None, **_) -> dict[str, Any]:
        recs = [r for r in (space_geom or {}).get("spaces", []) if r["geometry_status"] != "unavailable" and r.get("footprint")]
        out = []
        for b in graph["buildings"]:
            ids = {s["global_id"] for s in graph["spaces"] if s["building_id"] == b["global_id"]}
            mine = [r for r in recs if r["space_global_id"] in ids]
            e: dict[str, Any] = {"building_id": b["global_id"], "name": b["name"], "method": self.method,
                                 "model_status": "not_applicable", "status": "derived", "storey_count": sum(
                                     1 for s in graph["storeys"] if s["building_id"] == b["global_id"])}
            if mine:
                fp = unary_union([shape(r["footprint"]) for r in mine])
                e.update({"footprint": mapping(fp), "footprint_area_m2": fp.area, "footprint_note": "union of net IfcSpace footprints (excludes walls)",
                          "z_min": min(r["z_min"] for r in mine), "z_max": max(r["z_max"] for r in mine),
                          "space_geometry_count": len(mine)})
            else:
                e.update({"footprint": None, "status": "unavailable", "note": "no space geometry"})
            out.append(e)
        return {"buildings": out}


class IfcStoreyFloorSegmenter(Extractor):
    task, name, method = "floor_segmentation", "ifc_storey_structure", "rule_based"

    def run(self, *, graph: dict, classification: dict, space_geom: dict | None = None, **_) -> dict[str, Any]:
        from Schependomlaan.floor_segmentation.floor_model import build_floor_records
        return build_floor_records(graph, classification, space_geom)


class RulePropertyDelineator(Extractor):
    task, name, method = "vertical_property_delineation", "prefix_composition_rules", "rule_based"

    def run(self, *, graph: dict, classification: dict, rules: dict, space_geom: dict | None = None, **_) -> dict[str, Any]:
        from Schependomlaan.apartment_generation.property_units import derive_property_units
        return derive_property_units(graph, classification, rules, space_geom)


for _e in (IfcGeometryBuildingExtractor(), IfcStoreyFloorSegmenter(), RulePropertyDelineator()):
    register(_e)
for _t in list(REGISTRY):
    register(TrainedModelAdapter(_t))
