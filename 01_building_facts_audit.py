"""Audit building facts and provenance without generating model geometry."""

from datetime import datetime, timezone
import json
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DATASETS = ROOT / "Datasets"
FOOTPRINT_PATH = DATASETS / "processed" / "buildings" / "kingfisher_exact_candidate.geojson"
ELEVATION_STATS_PATH = DATASETS / "derived" / "validation" / "kingfisher_elevation_stats.json"
SITE_PLAN_PATH = DATASETS / "reference" / "architectural" / "s3c81w8j.png"
OUTPUT_PATH = DATASETS / "derived" / "validation" / "kingfisher_building_facts.json"
TARGET_CRS = "EPSG:32643"
REFERENCE = {"latitude": 12.9722, "longitude": 77.5956}


def audit_footprint():
    collection = json.loads(FOOTPRINT_PATH.read_text(encoding="utf-8"))
    feature = collection["features"][0]
    geometry_wgs84 = shape(feature["geometry"])
    if not geometry_wgs84.is_valid:
        raise ValueError("Microsoft footprint geometry is invalid")

    to_utm = Transformer.from_crs("EPSG:4326", TARGET_CRS, always_xy=True).transform
    geometry_utm = transform(to_utm, geometry_wgs84)
    centroid = geometry_utm.centroid
    properties = feature.get("properties", {})

    return {
        "source": "Datasets/processed/buildings/kingfisher_exact_candidate.geojson",
        "crs": TARGET_CRS,
        "source_crs_assumption": "GeoJSON coordinates are WGS84 longitude/latitude; no CRS member is present.",
        "geometry_type": geometry_wgs84.geom_type,
        "valid": geometry_wgs84.is_valid,
        "bounds_epsg32643": list(geometry_utm.bounds),
        "area_m2": geometry_utm.area,
        "perimeter_m": geometry_utm.length,
        "centroid_epsg32643": [centroid.x, centroid.y],
        "height_attribute": properties.get("height"),
        "confidence_attribute": properties.get("confidence"),
        "height_attribute_interpretation": "Unavailable because Microsoft value is -1.",
        "confidence_attribute_interpretation": "Unavailable because Microsoft value is -1.",
    }


def audit_site_plan():
    with Image.open(SITE_PLAN_PATH) as image:
        image_metadata = {
            "format": image.format,
            "width": image.width,
            "height": image.height,
        }

    return {
        "source": "Datasets/reference/architectural/s3c81w8j.png",
        "source_type": "Architectural/site-plan reference; not cadastral or legal ground truth.",
        "image_metadata": image_metadata,
        "findings": [
            "Three labelled towers are visible: TOWER A, TOWER B, and TOWER C.",
            "The towers are arranged together in the northern portion of the illustrated site, around internal landscaped/open circulation space.",
            "Kasturba Road and a Kasturba Road cross-road are labelled along the north/west side of the plan.",
            "Vital Mallya Road is labelled along the southern edge of the plan.",
            "Internal driveways and perimeter circulation are shown around the tower and site areas.",
            "An EXIT/ENTRY label is visible near the northern road access.",
            "Parking areas and parking-level/site parking structures are illustrated in the southern and central site areas.",
            "A north arrow is visible at the lower-right of the plan.",
            "The plan also shows landscaped areas, trees, open courts, and other site facilities/context.",
        ],
        "limitations": [
            "The plan is a dated architectural reference and does not establish cadastral/legal boundaries.",
            "It does not provide authoritative building height, floor count, or apartment/unit count for this audit.",
            "The illustration is not used to derive precise geospatial coordinates or dimensions.",
        ],
    }


def main():
    footprint = audit_footprint()
    elevation = json.loads(ELEVATION_STATS_PATH.read_text(encoding="utf-8"))
    site_plan = audit_site_plan()

    report = {
        "building": "Prestige Kingfisher Towers",
        "location": REFERENCE,
        "evidence_search": {
            "searched_terms": [
                "Prestige Kingfisher Towers",
                "Kingfisher Towers",
                "122 m",
                "34 floors",
                "81 apartments",
                "81 units",
                "building height",
                "floor count",
                "apartment count",
            ],
            "workspace_conclusion": "No workspace source document was found that verifies height_m, floor_count, or unit_count. The supplied values are therefore not promoted to verified facts in this report.",
            "existing_json_path_note": "The existing cadastral and OSM JSON reports retain historical pre-reorganization source paths. They were read only and not modified.",
        },
        "facts": {
            "height_m": {
                "value": None,
                "classification": "UNVERIFIED",
                "source": None,
                "evidence": None,
                "limitations": ["No supporting project document was found for 122 m.", "Microsoft height attribute is -1 and unavailable.", "CartoDEM DSM elevation is not tower height."],
            },
            "floor_count": {
                "value": None,
                "classification": "UNVERIFIED",
                "source": None,
                "evidence": None,
                "limitations": ["No supporting project document was found for 34 floors.", "The architectural site plan labels towers but does not establish floor count."],
            },
            "unit_count": {
                "value": None,
                "classification": "UNVERIFIED",
                "source": None,
                "evidence": None,
                "limitations": ["No supporting project document was found for 81 apartments or units.", "The architectural site plan does not establish unit count."],
            },
        },
        "footprint": footprint,
        "site_plan": site_plan,
        "elevation": {
            "source": "Datasets/derived/validation/kingfisher_elevation_stats.json",
            "product_type": "DSM",
            "statistics": {
                "building_area": elevation["building_elevation_statistics"],
                "surrounding_aoi": elevation["aoi_elevation_statistics"],
                "approximate_ground_elevation_m": elevation["approximate_ground_elevation_m"],
            },
            "valid_pixel_count": {
                "building_area": elevation["building_elevation_statistics"]["valid_pixel_count"],
                "surrounding_aoi": elevation["aoi_elevation_statistics"]["valid_pixel_count"],
            },
            "nodata_handling": elevation["nodata_handling"],
            "limitations": [
                "CartoDEM source metadata identifies the product as a DSM, not a verified bare-earth model.",
                "The approximately 30 m raster resolution provides only six valid pixels in the building mask.",
                "DSM elevation statistics must not be interpreted as tower height or floor elevation.",
            ],
        },
        "limitations": [
            "Height, floor count, and unit count remain unresolved from workspace evidence.",
            "The Microsoft footprint is a derived building footprint, not an official cadastral boundary.",
            "The architectural site plan is reference material, not cadastral/legal ground truth.",
        ],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    OUTPUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT_PATH), "facts": report["facts"], "area_m2": footprint["area_m2"], "perimeter_m": footprint["perimeter_m"]}, indent=2))


if __name__ == "__main__":
    main()
