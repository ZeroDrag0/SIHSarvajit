"""Shared derived massing geometry for the Kingfisher prototype."""

import json
from pathlib import Path

from shapely.geometry import Polygon, shape
from shapely.ops import transform
from pyproj import Transformer


TARGET_CRS = "EPSG:32643"
FOOTPRINT_PATH = Path(__file__).resolve().parents[1] / "Datasets" / "processed" / "buildings" / "kingfisher_exact_candidate.geojson"
BUILDING_HEIGHT_M = 120.0
FLOOR_COUNT = 34
CREST_START_M = BUILDING_HEIGHT_M * 30 / FLOOR_COUNT


def load_source_footprint():
    collection = json.loads(FOOTPRINT_PATH.read_text(encoding="utf-8"))
    source = shape(collection["features"][0]["geometry"])
    if not source.is_valid or source.geom_type != "Polygon":
        raise ValueError("Input footprint must be a valid Polygon")
    to_utm = Transformer.from_crs("EPSG:4326", TARGET_CRS, always_xy=True).transform
    projected = transform(to_utm, source)
    if not projected.is_valid or projected.interiors:
        raise ValueError("Projected footprint must be a valid polygon without interior rings")
    return projected


def build_architectural_footprint(source):
    """Create the restrained upper crown with symmetric rear scoops."""
    min_x, min_y, max_x, max_y = source.bounds
    width = max_x - min_x
    depth = max_y - min_y
    central_width = width * 0.304
    central_area = central_width * depth
    side_rear_y = min_y + (source.area - central_area) / (width - central_width)
    center_x = (min_x + max_x) / 2.0
    central_min_x = center_x - central_width / 2.0
    central_max_x = center_x + central_width / 2.0
    footprint = Polygon([
        (min_x, min_y),
        (max_x, min_y),
        (max_x, side_rear_y),
        (central_max_x, side_rear_y),
        (central_max_x, max_y),
        (central_min_x, max_y),
        (central_min_x, side_rear_y),
        (min_x, side_rear_y),
    ])
    if not footprint.is_valid or not footprint.is_simple:
        raise ValueError("Derived architectural footprint is invalid")
    if abs(footprint.area - source.area) > 1e-7:
        raise ValueError("Derived architectural footprint does not conserve source area")
    return footprint


def build_main_body_footprint(source):
    """Create the broad, restrained lower tower body from source dimensions."""
    min_x, min_y, max_x, _ = source.bounds
    body_depth = source.area / (max_x - min_x)
    return Polygon([
        (min_x, min_y),
        (max_x, min_y),
        (max_x, min_y + body_depth),
        (min_x, min_y + body_depth),
    ])


def footprint_for_floor(source, z_min):
    return build_architectural_footprint(source) if z_min >= CREST_START_M - 1e-9 else build_main_body_footprint(source)