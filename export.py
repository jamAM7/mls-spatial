"""
export.py — MLS Spatial Search Service
Converts a SearchResult into a GeoJSON FeatureCollection.
"""

from models import SearchResult, Lot, SurveyMark


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