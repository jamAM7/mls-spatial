"""
test_search.py — Integration tests for the full search pipeline.
Mocks all NSW Spatial Services API calls using the responses library.
"""
import json
import urllib.parse
from pathlib import Path
from unittest.mock import patch

import pytest
import responses as resp

from service.search import search, _find_subject_lot
from service.models import SearchResult, Lot

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def _addr_callback(request):
    params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(request.url).query))
    data = _load("address_wgs84_response.json") if params.get("outSR") == "4326" else _load("address_response.json")
    return (200, {"Content-Type": "application/json"}, json.dumps(data))


ADDR_URL   = "https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Geocoded_Addressing_Theme/FeatureServer/1/query"
ADMIN_BASE = "https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Administrative_Boundaries_Theme/FeatureServer"
LOT_URL    = "https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Land_Parcel_Property_Theme/FeatureServer/8/query"
SM_URL     = "https://portal.spatial.nsw.gov.au/server/rest/services/SurveyMarkGDA2020/MapServer/0/query"
PLAN_BASE  = "https://maps.six.nsw.gov.au/arcgis/rest/services/sixmaps/Boundaries/MapServer"
ROAD_URL   = "https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Transport_Theme/FeatureServer/1/query"
CL_URL     = "https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Transport_Theme/FeatureServer/0/query"
ELEV_URL   = "https://portal.spatial.nsw.gov.au/server/rest/services/elevation/ImageServer/identify"


def _register_all(register_elevation=False):
    resp.add_callback(resp.GET, ADDR_URL, callback=_addr_callback, content_type="application/json")
    resp.add(resp.GET, f"{ADMIN_BASE}/2/query",  json=_load("admin_suburb_response.json"))
    resp.add(resp.GET, f"{ADMIN_BASE}/8/query",  json=_load("admin_lga_response.json"))
    resp.add(resp.GET, f"{ADMIN_BASE}/5/query",  json=_load("admin_parish_response.json"))
    resp.add(resp.GET, f"{ADMIN_BASE}/11/query", json=_load("admin_county_response.json"))
    resp.add(resp.GET, LOT_URL,                  json=_load("lot_response.json"))
    resp.add(resp.GET, SM_URL,                   json=_load("survey_marks_response.json"))
    resp.add(resp.GET, ROAD_URL,                 json={"features": []})
    resp.add(resp.GET, CL_URL,                   json={"features": []})
    resp.add(resp.GET, f"{PLAN_BASE}/2",         json=_load("plan_layer_response.json"))
    resp.add(resp.GET, f"{PLAN_BASE}/2/query",   json=_load("plan_response.json"))
    if register_elevation:
        resp.add(resp.GET, ELEV_URL, json={"value": "10.5"})


ADDRESS = "87 BUNARBA ROAD GYMEA BAY"


@resp.activate
def test_returns_search_result():
    _register_all()
    result = search(ADDRESS, 200, grid_spacing_m=None)
    assert isinstance(result, SearchResult)


@resp.activate
def test_invalid_address_returns_none():
    resp.add_callback(resp.GET, ADDR_URL, callback=lambda r: (200, {}, json.dumps({"features": []})))
    result = search("FAKE ADDRESS XYZ 999", 200, grid_spacing_m=None)
    assert result is None


@resp.activate
def test_nearby_lots_populated():
    _register_all()
    result = search(ADDRESS, 200, grid_spacing_m=None)
    assert len(result.nearby_lots) > 0
    assert all(isinstance(lot, Lot) for lot in result.nearby_lots)


@resp.activate
def test_survey_marks_populated():
    _register_all()
    result = search(ADDRESS, 200, grid_spacing_m=None)
    assert len(result.survey_marks) > 0


@resp.activate
def test_plans_populated():
    _register_all()
    result = search(ADDRESS, 200, grid_spacing_m=None)
    assert len(result.plans) > 0


@resp.activate
def test_epsg_set():
    _register_all()
    result = search(ADDRESS, 200, grid_spacing_m=None)
    assert result.epsg is not None
    assert str(result.epsg).startswith("785")


@resp.activate
def test_mga_zone_set():
    _register_all()
    result = search(ADDRESS, 200, grid_spacing_m=None)
    assert result.mga_zone in (54, 55, 56)


@resp.activate
def test_search_radius_preserved():
    _register_all()
    result = search(ADDRESS, 300, grid_spacing_m=None)
    assert result.search_radius_m == 300


@resp.activate
def test_marks_radius_defaults_to_search_radius():
    _register_all()
    result = search(ADDRESS, 200, grid_spacing_m=None)
    assert result.marks_radius_m == 200


@resp.activate
def test_marks_radius_override():
    _register_all()
    result = search(ADDRESS, 200, marks_radius_m=500, grid_spacing_m=None)
    assert result.marks_radius_m == 500


@resp.activate
def test_no_elevation_when_grid_spacing_none():
    _register_all()
    result = search(ADDRESS, 200, grid_spacing_m=None)
    assert result.elevation_grid is None


@resp.activate
def test_address_resolved_populated():
    _register_all()
    result = search(ADDRESS, 200, grid_spacing_m=None)
    assert result.address.resolved_string is not None
    assert len(result.address.resolved_string) > 0


@resp.activate
def test_datum_default():
    _register_all()
    result = search(ADDRESS, 200, grid_spacing_m=None)
    assert result.datum == "GDA2020"


# ── _find_subject_lot unit tests ──────────────────────────────────────────────

def _make_lot(coords, plan_label="DP999001", lot_number="1"):
    lot = Lot.__new__(Lot)
    lot.geometry = [coords]
    lot.plan_label = plan_label
    lot.lot_number = lot_number
    lot.is_subject = False
    return lot


def test_find_subject_lot_inside():
    coords = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
    lot = _make_lot(coords)
    result = _find_subject_lot([lot], 5, 5)
    assert result is lot


def test_find_subject_lot_outside():
    coords = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
    lot = _make_lot(coords)
    result = _find_subject_lot([lot], 20, 20)
    assert result is None


def test_find_subject_lot_empty():
    assert _find_subject_lot([], 5, 5) is None


def test_find_subject_lot_picks_correct_lot():
    coords_a = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
    coords_b = [[20, 20], [30, 20], [30, 30], [20, 30], [20, 20]]
    lot_a = _make_lot(coords_a, lot_number="1")
    lot_b = _make_lot(coords_b, lot_number="2")
    assert _find_subject_lot([lot_a, lot_b], 25, 25) is lot_b
    assert _find_subject_lot([lot_a, lot_b], 5, 5) is lot_a
