"""
export.py — MLS Spatial Search Service
Converts a SearchResult into a GeoJSON FeatureCollection.
"""

from service.models import SearchResult, Lot, SurveyMark
from pathlib import Path
from service.utils import lot_label
import requests


def to_geojson(result: SearchResult) -> dict:
    plan_lookup = {plan.plan_label: plan for plan in result.plans}
    crs_label = f"{result.datum} MGA Zone {result.mga_zone} (EPSG:{result.epsg})"

    features = []

    for lot in result.nearby_lots:
        plan = plan_lookup.get(lot.plan_label)
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": lot.geometry,
            },
            "properties": {
                "feature_type":           "lot",
                "address":                lot.address,
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
        })

    for mark in result.survey_marks:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [mark.easting, mark.northing],
            },
            "properties": {
                "feature_type":               "survey_mark",
                "mark_number":                mark.mark_number,
                "mark_type":                  mark.mark_type,
                "mark_status":                mark.mark_status,
                "mark_symbol_label":          mark.mark_symbol_label,
                "marksymbol":                 mark.mark_symbol,
                "gda_class":                  mark.gda_class,
                "gda_date":                   str(mark.gda_date) if mark.gda_date else None,
                "gda_pos_uncertainty_label":  mark.gda_pos_uncertainty_label,
                "gda_height_pos_uncertainty": mark.gda_height_pos_uncertainty,
                "gda_loc_uncertainty_label":  mark.gda_loc_uncertainty_label,
                "gda_height_loc_uncertainty": mark.gda_height_loc_uncertainty,
                "mga_csf_2020":               mark.mga_csf_2020,
                "mga_csf_2020_label":         mark.mga_csf_2020_label,
                "ahd_height":                 mark.ahd_height,
                "ahd_height_label":           mark.ahd_height_label,
                "ahd_class":                  mark.ahd_class,
                "mga_zone":                   mark.mga_zone,
                "mga_easting_label":          mark.mga_easting_label,
                "mga_northing_label":         mark.mga_northing_label,
                "surface_level_ahd":          mark.surface_level_ahd,
                "retrieved_at":               mark.retrieved_at.isoformat() if mark.retrieved_at else None,
            }
        })

    for road in result.roads:
        if not road.geometry:
            continue
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": road.geometry,
            },
            "properties": {
                "feature_type":        "road",
                "road_name_label":     road.road_name_label,
                "road_type":           road.road_type,
                "road_type_label":     road.road_type_label,
                "road_corridor_type":  road.road_corridor_type,
                "road_corridor_label": road.road_corridor_label,
                "urbanity":            road.urbanity,
                "cadid":               road.cadid,
            }
        })

    for cl in result.road_centrelines:
        for path in cl.geometry:
            if len(path) < 2:
                continue
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": path,
                },
                "properties": {
                    "feature_type":    "road_centreline",
                    "road_name_label": cl.road_name_label,
                    "urbanity":        cl.urbanity,
                }
            })

    if result.elevation_grid:
        for pt in result.elevation_grid.points:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [pt["easting"], pt["northing"]],
                },
                "properties": {
                    "feature_type": "elevation_sample",
                    "row":          pt["row"],
                    "col":          pt["col"],
                    "ahd":          pt["ahd"],
                }
            })

    return {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {"name": f"urn:ogc:def:crs:EPSG::{result.epsg}"}
        },
        "search": {
            "address_input":     result.address.input_string,
            "address_resolved":  result.address.resolved_string,
            "search_mode":       result.search_mode,
            "suburb":            result.address.suburb,
            "lga":               result.address.lga,
            "parish":            result.address.parish,
            "county":            result.address.county,
            "surface_level_ahd": result.address.surface_level_ahd,
            "radius_m":          result.search_radius_m,
            "marks_radius_m":    result.marks_radius_m,
            "subject_lot":       lot_label(result.subject_lot),
            "lot_count":         len(result.nearby_lots),
            "plan_count":        len(result.plans),
            "mark_count":        len(result.survey_marks),
            "datum":             result.datum,
            "mga_zone":          result.mga_zone,
            "coordinate_system": crs_label,
            "elevation_grid": {
                "grid_spacing_m":   result.elevation_grid.grid_spacing_m,
                "padding_pct":      result.elevation_grid.padding_pct,
                "rows":             result.elevation_grid.rows,
                "cols":             result.elevation_grid.cols,
                "point_count":      result.elevation_grid.point_count,
                "capped":           result.elevation_grid.capped,
                "capped_spacing_m": result.elevation_grid.capped_spacing_m,
                "bbox_padded":      result.elevation_grid.bbox_padded,
            } if result.elevation_grid else None,
        },
        "features": features,
    }


def fetch_cre_map_image(result: SearchResult, output_folder: Path, map_radius_m: int = 500, output_path: str = "ss_cre_map.png") -> Path | None:
    """
    Fetches a PNG raster image of the cadastral map from the CRE MapServer.
    map_radius_m controls the area shown — defaults to 500m regardless of search radius.
    """
    cx = result.address.easting
    cy = result.address.northing
    pad = map_radius_m * 1.2

    xmin = cx - pad
    xmax = cx + pad
    ymin = cy - pad
    ymax = cy + pad

    url = "https://maps.six.nsw.gov.au/arcgis/rest/services/sixmaps/CRE/MapServer/export"
    params = {
        "bbox":   f"{xmin},{ymin},{xmax},{ymax}",
        "bboxSR": str(result.epsg),
        "size":   "2400,1800",
        "format": "png",
        "f":      "image",
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        return None

    output_folder.mkdir(parents=True, exist_ok=True)
    image_path = output_folder / "ss_cre_map.png"
    image_path.write_bytes(response.content)

    return image_path