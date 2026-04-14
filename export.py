"""
export.py — MLS Spatial Search Service
Converts a SearchResult into a GeoJSON FeatureCollection.
"""

from models import SearchResult, Lot, SurveyMark
from pathlib import Path
from models import SearchResult, Lot, SurveyMark
import requests


def _lot_feature(lot: Lot) -> dict:
    """Converts a Lot object into a GeoJSON Feature."""
    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [lot.geometry]  # geometry is already list of [easting, northing] pairs
        },
        "properties": {
            "feature_type":          "lot",
            "lot_number":            lot.lot_number,
            "plan_label":            lot.plan_label,
            "plan_number":           lot.plan_number,
            "section_number":        lot.section_number,
            "is_subject":            lot.is_subject,
            "is_surveyed":           _get_plan_is_surveyed(lot),
            "registration_date":     _get_plan_registration_date(lot),
            "its_title_status_label": lot.its_title_status_label,
            "has_stratum":           lot.has_stratum,
            "stratum_level_label":   lot.stratum_level_label,
            "plan_lot_area":         lot.plan_lot_area,
            "plan_lot_area_units":   lot.plan_lot_area_units,
        }
    }


def _survey_mark_feature(mark: SurveyMark) -> dict:
    """Converts a SurveyMark object into a GeoJSON Feature."""
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [mark.easting, mark.northing]
        },
        "properties": {
            "feature_type":              "survey_mark",
            "mark_number":               mark.mark_number,
            "mark_type":                 mark.mark_type,
            "mark_status":               mark.mark_status,
            "mark_symbol_label":         mark.mark_symbol_label,
            "gda_class":                 mark.gda_class,
            "gda_date":                  str(mark.gda_date) if mark.gda_date else None,
            "gda_pos_uncertainty_label": mark.gda_pos_uncertainty_label,
            "ahd_height":                mark.ahd_height,
            "ahd_height_label":          mark.ahd_height_label,
            "ahd_class":                 mark.ahd_class,
            "mga_easting_label":         mark.mga_easting_label,
            "mga_northing_label":        mark.mga_northing_label,
            "retrieved_at":              mark.retrieved_at.isoformat() if mark.retrieved_at else None,
        }
    }


# These are helpers to get plan info for a lot
# plan data lives in SearchResult.plans, not on the Lot object directly
# search.py should pass plans as a lookup — for now we leave these as None
# and to_geojson accepts an optional plans lookup

def _get_plan_is_surveyed(lot: Lot):
    return None  # populated by to_geojson if plans lookup provided

def _get_plan_registration_date(lot: Lot):
    return None  # populated by to_geojson if plans lookup provided


def to_geojson(result: SearchResult) -> dict:
    """
    Converts a SearchResult into a GeoJSON FeatureCollection.
    Returns a dict ready to be serialised to JSON.
    """

    # Build plan lookup by plan_label for enriching lot features
    plan_lookup = {plan.plan_label: plan for plan in result.plans}

    features = []

    # Add lot features
    for lot in result.nearby_lots:
        plan = plan_lookup.get(lot.plan_label)
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [lot.geometry]
            },
            "properties": {
                "feature_type":           "lot",
                "lot_number":             lot.lot_number,
                "plan_label":             lot.plan_label,
                "plan_number":            lot.plan_number,
                "section_number":         lot.section_number,
                "is_subject":             lot.is_subject,
                "is_surveyed":            plan.is_surveyed if plan else None,
                "registration_date":      str(plan.registration_date) if plan and plan.registration_date else None,
                "its_title_status_label": lot.its_title_status_label,
                "has_stratum":            lot.has_stratum,
                "stratum_level_label":    lot.stratum_level_label,
                "plan_lot_area":          lot.plan_lot_area,
                "plan_lot_area_units":    lot.plan_lot_area_units,
            }
        }
        features.append(feature)

    # Add survey mark features
    for mark in result.survey_marks:
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [mark.easting, mark.northing]
            },
            "properties": {
                "feature_type":              "survey_mark",
                "mark_number":               mark.mark_number,
                "mark_type":                 mark.mark_type,
                "mark_status":               mark.mark_status,
                "mark_symbol_label":         mark.mark_symbol_label,
                "gda_class":                 mark.gda_class,
                "gda_date":                  str(mark.gda_date) if mark.gda_date else None,
                "gda_pos_uncertainty_label": mark.gda_pos_uncertainty_label,
                "ahd_height":                mark.ahd_height,
                "ahd_height_label":          mark.ahd_height_label,
                "ahd_class":                 mark.ahd_class,
                "mga_easting_label":         mark.mga_easting_label,
                "mga_northing_label":        mark.mga_northing_label,
                "retrieved_at":              mark.retrieved_at.isoformat() if mark.retrieved_at else None,
            }
        }
        features.append(feature)

    # Build subject lot label
    subject_lot_label = None
    if result.subject_lot:
        subject_lot_label = f"{result.subject_lot.lot_number}//{result.subject_lot.plan_label}"

    return {
        "type": "FeatureCollection",
        "search": {
            "address_input":    result.address.input_string,
            "address_resolved": result.address.resolved_string,
            "suburb":           result.address.suburb,
            "lga":              result.address.lga,
            "parish":           result.address.parish,
            "county":           result.address.county,
            "radius_m":         result.search_radius_m,
            "subject_lot":      subject_lot_label,
            "lot_count":        len(result.nearby_lots),
            "plan_count":       len(result.plans),
            "mark_count":       len(result.survey_marks),
        },
        "features": features
    }



# TODO: fetch_cre_map_image(result: SearchResult) -> Path
# Queries the CRE MapServer export endpoint with the bounding box of all lots
# and saves the PNG map image locally.
# Endpoint: https://maps.six.nsw.gov.au/arcgis/rest/services/sixmaps/CRE/MapServer/export
# See SPEC.md for full details.
# Required before server.py can return cre_map_image in the SearchResult.








def fetch_cre_map_image(result: SearchResult, output_folder: Path, map_radius_m: int = 500) -> Path | None:
    """
    Fetches a PNG raster image of the cadastral map from the CRE MapServer.
    map_radius_m controls the area shown — defaults to 500m regardless of search radius.
    """
    from api.lot import get_lot_info

    # Get lots for the larger map area
    map_lots = get_lot_info(result.address.easting, result.address.northing, map_radius_m)
    if not map_lots:
        return None

    all_eastings = []
    all_northings = []

    for lot in map_lots:
        for point in lot.geometry:
            all_eastings.append(point[0])
            all_northings.append(point[1])

    if not all_eastings:
        return None

    # Calculate bounding box with 10% buffer
    xmin = min(all_eastings)
    xmax = max(all_eastings)
    ymin = min(all_northings)
    ymax = max(all_northings)

    x_buffer = (xmax - xmin) * 0.1
    y_buffer = (ymax - ymin) * 0.1

    xmin -= x_buffer
    xmax += x_buffer
    ymin -= y_buffer
    ymax += y_buffer

    # Fetch PNG
    url = "https://maps.six.nsw.gov.au/arcgis/rest/services/sixmaps/CRE/MapServer/export"
    params = {
        "bbox":   f"{xmin},{ymin},{xmax},{ymax}",
        "bboxSR": "7856",
        "size":   "2400,1800",
        "format": "png",
        "f":      "image",
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        return None

    output_folder.mkdir(parents=True, exist_ok=True)
    image_path = output_folder / "cre_map.png"
    image_path.write_bytes(response.content)

    return image_path











# def fetch_cre_map_image(result: SearchResult, output_folder: Path) -> Path | None:
#     """
#     Fetches a PNG raster image of the cadastral map from the CRE MapServer
#     for the bounding box of all nearby lots.
#     Saves to output_folder/cre_map.png and returns the path.
#     """
#     # Collect all coordinates from all lot geometries
#     all_eastings = []
#     all_northings = []

#     for lot in result.nearby_lots:
#         for point in lot.geometry:
#             all_eastings.append(point[0])
#             all_northings.append(point[1])

#     if not all_eastings:
#         return None

#     # Calculate bounding box
#     xmin = min(all_eastings)
#     xmax = max(all_eastings)
#     ymin = min(all_northings)
#     ymax = max(all_northings)

#     # Add 10% buffer
#     x_buffer = (xmax - xmin) * 0.1
#     y_buffer = (ymax - ymin) * 0.1

#     xmin -= x_buffer
#     xmax += x_buffer
#     ymin -= y_buffer
#     ymax += y_buffer

#     # Fetch the PNG from CRE MapServer
#     url = "https://maps.six.nsw.gov.au/arcgis/rest/services/sixmaps/CRE/MapServer/export"
#     params = {
#         "bbox":   f"{xmin},{ymin},{xmax},{ymax}",
#         "bboxSR": "7856",
#         "size":   "1200,900",
#         "format": "png",
#         "f":      "image",
#     }

#     response = requests.get(url, params=params)
#     if response.status_code != 200:
#         return None

#     # Save the PNG
#     output_folder.mkdir(parents=True, exist_ok=True)
#     image_path = output_folder / "cre_map.png"
#     image_path.write_bytes(response.content)

#     return image_path