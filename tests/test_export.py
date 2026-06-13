"""
test_export.py — Tests for export.py GeoJSON output.
"""
from datetime import date
from unittest.mock import MagicMock

import pytest

from service.export import to_geojson
from service.models import (
    SearchResult, Address, Lot, Plan, SurveyMark,
    Road, RoadCentreline,
)
from datetime import datetime


def _make_address():
    a = Address.__new__(Address)
    a.input_string     = "87 BUNARBA ROAD GYMEA BAY"
    a.resolved_string  = "87 BUNARBA ROAD GYMEA BAY"
    a.easting          = 336152.0
    a.northing         = 6234478.0
    a.longitude        = 151.07
    a.latitude         = -34.04
    a.suburb           = "GYMEA BAY"
    a.lga              = "SUTHERLAND SHIRE"
    a.parish           = "WORONORA"
    a.county           = "CUMBERLAND"
    a.surface_level_ahd = 12.5
    return a


def _make_lot(lot_number="1", plan_label="DP999001", is_subject=False, section_number=None):
    lot = Lot.__new__(Lot)
    lot.lot_number          = lot_number
    lot.plan_label          = plan_label
    lot.plan_number         = 999001
    lot.section_number      = section_number
    lot.is_subject          = is_subject
    lot.its_title_status    = 1
    lot.its_title_status_label = "Torrens Title"
    lot.has_stratum         = False
    lot.stratum_level_label = "Surface"
    lot.plan_lot_area       = 500.0
    lot.plan_lot_area_units = "m2"
    lot.geometry            = [[[336100, 6234400], [336200, 6234400], [336200, 6234500], [336100, 6234500], [336100, 6234400]]]
    return lot


def _make_plan(plan_label="DP999001"):
    p = Plan.__new__(Plan)
    p.plan_label       = plan_label
    p.plan_type        = "DP"
    p.plan_number      = 999001
    p.is_surveyed      = True
    p.is_current       = True
    p.registration_date = date(2000, 1, 1)
    p.local_file       = None
    return p


def _make_mark():
    m = SurveyMark.__new__(SurveyMark)
    m.mark_number               = "12345"
    m.mark_type                 = "SS"
    m.mark_status               = "F"
    m.mark_symbol               = "SSR"
    m.mark_symbol_label         = "SS Established GDA + Accurate AHD"
    m.easting                   = 336152.0
    m.northing                  = 6234478.0
    m.longitude                 = 151.07
    m.latitude                  = -34.04
    m.gda_class                 = "3A"
    m.gda_date                  = date(2000, 1, 1)
    m.gda_pos_uncertainty_label = "0.010m"
    m.gda_height_pos_uncertainty = "0.015m"
    m.gda_loc_uncertainty_label = "0.020m"
    m.gda_height_loc_uncertainty = "0.025m"
    m.mga_csf_2020              = 1.00024
    m.mga_csf_2020_label        = "1.00024"
    m.ahd_height                = 12.5
    m.ahd_height_label          = "12.500m"
    m.ahd_class                 = "LC"
    m.ahd_date                  = None
    m.mga_zone                  = 56
    m.mga_easting_label         = "336152.000m E"
    m.mga_northing_label        = "6234478.000m N"
    m.surface_level_ahd         = 12.5
    m.retrieved_at              = datetime(2024, 1, 1, 12, 0, 0)
    return m


def _make_result(lots=None, marks=None, plans=None):
    r = SearchResult.__new__(SearchResult)
    r.address          = _make_address()
    r.subject_lot      = lots[0] if lots else None
    r.nearby_lots      = lots or []
    r.survey_marks     = marks or []
    r.plans            = plans or []
    r.roads            = []
    r.road_centrelines = []
    r.elevation_grid   = None
    r.search_radius_m  = 200
    r.marks_radius_m   = 200
    r.cre_map_image    = None
    r.epsg             = 7856
    r.datum            = "GDA2020"
    r.mga_zone         = 56
    r.search_mode      = "address"
    return r


# ── Structure tests ───────────────────────────────────────────────────────────

def test_returns_feature_collection():
    result = _make_result()
    geojson = to_geojson(result)
    assert geojson["type"] == "FeatureCollection"


def test_features_is_list():
    result = _make_result()
    assert isinstance(to_geojson(result)["features"], list)


def test_search_block_present():
    result = _make_result()
    assert "search" in to_geojson(result)


def test_crs_block_present():
    result = _make_result()
    assert "crs" in to_geojson(result)


def test_crs_contains_epsg():
    result = _make_result()
    crs = to_geojson(result)["crs"]
    assert "7856" in crs["properties"]["name"]


# ── Lot feature tests ─────────────────────────────────────────────────────────

def test_lot_feature_type():
    lot = _make_lot()
    result = _make_result(lots=[lot], plans=[_make_plan()])
    features = to_geojson(result)["features"]
    lot_features = [f for f in features if f["properties"]["feature_type"] == "lot"]
    assert len(lot_features) == 1


def test_lot_properties_populated():
    lot = _make_lot(lot_number="5", plan_label="DP999001")
    result = _make_result(lots=[lot], plans=[_make_plan()])
    f = [f for f in to_geojson(result)["features"] if f["properties"]["feature_type"] == "lot"][0]
    p = f["properties"]
    assert p["lot_number"] == "5"
    assert p["plan_label"] == "DP999001"
    assert p["its_title_status_label"] == "Torrens Title"


def test_lot_is_surveyed_from_plan():
    lot = _make_lot()
    plan = _make_plan()
    plan.is_surveyed = True
    result = _make_result(lots=[lot], plans=[plan])
    f = [f for f in to_geojson(result)["features"] if f["properties"]["feature_type"] == "lot"][0]
    assert f["properties"]["is_surveyed"] is True


def test_lot_is_surveyed_none_when_no_plan():
    lot = _make_lot()
    result = _make_result(lots=[lot], plans=[])
    f = [f for f in to_geojson(result)["features"] if f["properties"]["feature_type"] == "lot"][0]
    assert f["properties"]["is_surveyed"] is None


def test_lot_section_number_in_properties():
    lot = _make_lot(section_number="11")
    result = _make_result(lots=[lot], plans=[_make_plan()])
    f = [f for f in to_geojson(result)["features"] if f["properties"]["feature_type"] == "lot"][0]
    assert f["properties"]["section_number"] == "11"


def test_lot_geometry_type():
    lot = _make_lot()
    result = _make_result(lots=[lot], plans=[_make_plan()])
    f = [f for f in to_geojson(result)["features"] if f["properties"]["feature_type"] == "lot"][0]
    assert f["geometry"]["type"] == "Polygon"


# ── Survey mark feature tests ─────────────────────────────────────────────────

def test_mark_feature_type():
    mark = _make_mark()
    result = _make_result(marks=[mark])
    features = to_geojson(result)["features"]
    mark_features = [f for f in features if f["properties"]["feature_type"] == "survey_mark"]
    assert len(mark_features) == 1


def test_mark_properties_populated():
    mark = _make_mark()
    result = _make_result(marks=[mark])
    f = [f for f in to_geojson(result)["features"] if f["properties"]["feature_type"] == "survey_mark"][0]
    p = f["properties"]
    assert p["mark_number"] == "12345"
    assert p["mark_type"] == "SS"
    assert p["marksymbol"] == "SSR"
    assert p["gda_class"] == "3A"
    assert p["ahd_height_label"] == "12.500m"
    assert p["mga_csf_2020_label"] == "1.00024"


def test_mark_geometry_is_point():
    mark = _make_mark()
    result = _make_result(marks=[mark])
    f = [f for f in to_geojson(result)["features"] if f["properties"]["feature_type"] == "survey_mark"][0]
    assert f["geometry"]["type"] == "Point"
    assert len(f["geometry"]["coordinates"]) == 2


def test_mark_retrieved_at_is_isoformat():
    mark = _make_mark()
    result = _make_result(marks=[mark])
    f = [f for f in to_geojson(result)["features"] if f["properties"]["feature_type"] == "survey_mark"][0]
    assert f["properties"]["retrieved_at"] == "2024-01-01T12:00:00"


# ── Search block tests ────────────────────────────────────────────────────────

def test_search_lot_count():
    lots = [_make_lot("1"), _make_lot("2")]
    result = _make_result(lots=lots, plans=[_make_plan()])
    assert to_geojson(result)["search"]["lot_count"] == 2


def test_search_mark_count():
    result = _make_result(marks=[_make_mark(), _make_mark()])
    assert to_geojson(result)["search"]["mark_count"] == 2


def test_search_radius_m():
    result = _make_result()
    result.search_radius_m = 350
    assert to_geojson(result)["search"]["radius_m"] == 350


def test_search_coordinate_system_label():
    result = _make_result()
    cs = to_geojson(result)["search"]["coordinate_system"]
    assert "GDA2020" in cs
    assert "56" in cs


def test_no_elevation_grid_when_none():
    result = _make_result()
    assert to_geojson(result)["search"]["elevation_grid"] is None
