"""Interoperable 3D cadastral model: Parcel > Building > Storey > Vertical Property Unit > IfcSpaces,
plus an independent Underground / Volumetric Entity branch."""
from __future__ import annotations

from typing import Any

from Schependomlaan.utils.provenance import provenance

MODEL_VERSION = "schependomlaan-3d-cadastre/0.1"
LEGAL_NOTICE = ("Prototype demonstrator. Property units are derived/inferred from IFC evidence; they are not legal "
                "cadastral units. Ownership is not provided and not invented.")


def build_model(*, graph: dict, floors: dict, units_doc: dict, units: list[dict], common_spaces: list[dict],
                ulpins: dict, validation: dict, cad_link: dict, cad_summary: dict, building_extr: dict,
                underground: dict, crs: dict, terrain: dict) -> dict[str, Any]:
    ul = {r["property_unit_id"]: r for r in ulpins["records"]}
    parcel_id = cad_link.get("parcel_id")
    parcel_ref = parcel_id if parcel_id else None
    prov_src = graph["source_file"]
    unit_nodes = []
    for u in units:
        g = u["geometry"]
        r = ul[u["candidate_id"]]
        unit_nodes.append({
            "unit_id": u["candidate_id"], "prototype_ulpin": r["prototype_ulpin"], "label": u["label"],
            "status": u["status"], "classification": u["classification"],
            "parcel_ref": parcel_ref, "building_ref": r["building_id"], "storey_refs": u["source_storey_ids"],
            "footprint_2d": g.get("footprint"), "volume_3d": {
                "representation": g.get("representation"), "geometry_status": g["geometry_status"],
                "volume_m3": g.get("volume_m3"), "surface_area_m2": g.get("surface_area_m2"),
                "glb_node": u["candidate_id"] if g["geometry_status"] != "unavailable" else None},
            "vertical_extent": {"z_min": g.get("z_min"), "z_max": g.get("z_max"), "height_m": g.get("height_m"),
                                "reference": crs["vertical_reference"]},
            "centroid": g.get("centroid"),
            "ifc_spaces": [{"global_id": s["global_id"], "name": s["name"], "long_name": s["long_name"], "function": s["function"]}
                           for s in u["spaces"]],
            "validation_status": r["validation_status"], "legal_status": "not_a_legal_cadastral_unit",
            "ownership_status": "unknown_not_provided", "confidence": u["confidence"], "warnings": u["warnings"],
            "provenance": provenance(source_file=prov_src, source_ifc_global_ids=u["source_space_ids"],
                                     derivation_method="; ".join(u["derivation_method"]), method_type=u["method_type"],
                                     confidence=u["confidence"], validation_state=r["validation_status"],
                                     coordinate_reference=crs, data_status="inferred"),
        })
    by_storey = {}
    for n in unit_nodes:
        for s in n["storey_refs"]:
            by_storey.setdefault(s, []).append(n["unit_id"])
    building_nodes = []
    for b in graph["buildings"]:
        be = next((x for x in building_extr["buildings"] if x["building_id"] == b["global_id"]), {})
        building_nodes.append({
            "building_id": b["global_id"], "name": b["name"], "parcel_ref": parcel_ref, "status": "derived",
            "bag_id": cad_link.get("bag_id"), "footprint_2d": be.get("footprint"), "z_min": be.get("z_min"), "z_max": be.get("z_max"),
            "storeys": [{"storey_id": s["storey_id"], "name": s["name"], "elevation_m": s["elevation_m"], "z_min": s["z_min"],
                         "z_max": s["z_max"], "height_m": s["height_m"], "z_source": s["z_source"],
                         "property_unit_refs": by_storey.get(s["storey_id"], []), "space_count": s["space_count"]}
                        for s in floors["storeys"] if s["building_id"] == b["global_id"]],
            "provenance": provenance(source_file=prov_src, source_ifc_global_ids=[b["global_id"]], derivation_method="IFC spatial structure",
                                     coordinate_reference=crs, data_status="derived"),
        })
    parcels = [{
        "parcel_id": parcel_id, "cadastral_status": cad_link.get("cadastral_status", cad_summary["cadastral_status"]),
        "link_basis": cad_link.get("link_basis"), "building_refs": [b["building_id"] for b in building_nodes],
        "ownership_status": "unknown_not_provided",
        "provenance": provenance(source_file=None, derivation_method="no parcel data" if not parcel_id else cad_link.get("link_basis", "supplied"),
                                 data_status="unavailable" if not parcel_id else "authoritative" if cad_summary["cadastral_status"] == "supplied" else "unverified"),
    }]
    nested = [{"parcel": parcel_id, "buildings": [{
        "building": b["building_id"], "storeys": [{
            "storey": s["storey_id"], "name": s["name"], "units": [{
                "unit": un["unit_id"], "prototype_ulpin": un["prototype_ulpin"], "ifc_spaces": [sp["global_id"] for sp in un["ifc_spaces"]]}
                for un in unit_nodes if s["storey_id"] in un["storey_refs"]]}
            for s in b["storeys"]]} for b in building_nodes]}]
    return {
        "model_version": MODEL_VERSION, "legal_notice": LEGAL_NOTICE, "coordinate_reference": crs,
        "hierarchy_order": ["Parcel", "Building", "Storey", "VerticalPropertyUnit", "IfcSpace"],
        "parcels": parcels, "buildings": building_nodes, "property_units": unit_nodes, "hierarchy": nested,
        "common_service_spaces": common_spaces,
        "underground_volumetric_entities": {"underground_status": underground["underground_status"],
                                            "entities": underground["entities"], "supported_types": underground.get("supported_types")},
        "terrain": {"terrain_status": terrain["terrain_status"]},
        "validation_summary": {"valid": validation["valid"], "error_count": len(validation["errors"]),
                               "warning_count": len(validation["warnings"]), "required_checks_not_passed": validation["metrics"]["required_checks_not_passed"]},
        "unit_grouping_summary": units_doc["summary"], "declared_count_check": units_doc["declared_count_check"],
    }


def build_schema() -> dict[str, Any]:
    status = {"enum": ["authoritative", "derived", "inferred", "prototype", "unavailable", "unverified"]}
    prov = {"type": "object", "required": ["source_dataset", "derivation_method", "data_status"],
            "properties": {"source_dataset": {"type": "string"}, "source_file": {"type": ["string", "null"]},
                           "source_ifc_global_ids": {"type": "array", "items": {"type": "string"}},
                           "derivation_method": {"type": "string"}, "confidence": {"type": ["number", "null"]},
                           "validation_state": {"type": "string"}, "coordinate_reference": {"type": ["object", "null"]},
                           "data_status": status}}
    geom = {"type": ["object", "null"]}
    return {
        "$schema": "http://json-schema.org/draft-07/schema#", "title": "Schependomlaan prototype 3D cadastral model",
        "type": "object", "required": ["model_version", "legal_notice", "coordinate_reference", "parcels", "buildings",
                                       "property_units", "underground_volumetric_entities", "validation_summary"],
        "properties": {
            "model_version": {"type": "string"}, "legal_notice": {"type": "string"},
            "coordinate_reference": {"type": "object", "required": ["source_crs", "target_crs", "vertical_reference", "transformation_status", "coordinate_status"]},
            "parcels": {"type": "array", "items": {"type": "object", "required": ["parcel_id", "cadastral_status", "building_refs"],
                                                   "properties": {"parcel_id": {"type": ["string", "null"]}, "cadastral_status": {"type": "string"},
                                                                  "building_refs": {"type": "array", "items": {"type": "string"}}}}},
            "buildings": {"type": "array", "items": {"type": "object", "required": ["building_id", "storeys", "provenance"],
                                                     "properties": {"building_id": {"type": "string"}, "parcel_ref": {"type": ["string", "null"]},
                                                                    "storeys": {"type": "array", "items": {"type": "object", "required": ["storey_id", "name", "property_unit_refs"]}},
                                                                    "provenance": prov}}},
            "property_units": {"type": "array", "items": {"type": "object", "required": [
                "unit_id", "prototype_ulpin", "status", "classification", "building_ref", "storey_refs", "footprint_2d", "volume_3d",
                "vertical_extent", "ifc_spaces", "validation_status", "legal_status", "ownership_status", "provenance"],
                "properties": {"unit_id": {"type": "string"}, "prototype_ulpin": {"type": "string", "pattern": "^P3D-"},
                               "status": {"enum": ["inferred", "derived", "prototype"]},
                               "footprint_2d": geom, "volume_3d": {"type": "object", "required": ["geometry_status"],
                                                                   "properties": {"geometry_status": {"enum": ["valid", "non_watertight", "invalid", "fallback", "unavailable"]}}},
                               "vertical_extent": {"type": "object", "required": ["z_min", "z_max", "height_m"]},
                               "legal_status": {"const": "not_a_legal_cadastral_unit"},
                               "ownership_status": {"type": "string"}, "provenance": prov}}},
            "underground_volumetric_entities": {"type": "object", "required": ["underground_status", "entities"], "properties": {
                "underground_status": {"enum": ["data_not_available", "supplied", "supplied_unreadable"]},
                "entities": {"type": "array", "items": {"type": "object", "required": [
                    "entity_id", "geometry", "z_min", "z_max", "type", "source", "confidence", "legal_status", "ownership_status", "provenance"]}}}},
            "validation_summary": {"type": "object", "required": ["valid"]},
        },
    }
