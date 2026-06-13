"""
test_server.py — Tests for FastAPI endpoints in server.py.
Uses FastAPI TestClient and mocks service layer functions.
"""
import json
import tempfile
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

# with
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from service.server import app
from service.models import SearchResult, Address, Lot, Plan, SurveyMark

client = TestClient(app)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_address():
    a = Address.__new__(Address)
    a.input_string      = "87 BUNARBA ROAD GYMEA BAY"
    a.resolved_string   = "87 BUNARBA ROAD GYMEA BAY"
    a.easting           = 336152.0
    a.northing          = 6234478.0
    a.longitude         = 151.07
    a.latitude          = -34.04
    a.suburb            = "GYMEA BAY"
    a.lga               = "SUTHERLAND SHIRE"
    a.parish            = "WORONORA"
    a.county            = "CUMBERLAND"
    a.surface_level_ahd = 12.5
    return a


def _make_lot():
    lot = Lot.__new__(Lot)
    lot.lot_number          = "1"
    lot.plan_label          = "DP999001"
    lot.plan_number         = 999001
    lot.section_number      = None
    lot.is_subject          = True
    lot.its_title_status    = 1
    lot.its_title_status_label = "Torrens Title"
    lot.has_stratum         = False
    lot.stratum_level_label = "Surface"
    lot.plan_lot_area       = 500.0
    lot.plan_lot_area_units = "m2"
    lot.geometry            = [[[336100, 6234400], [336200, 6234400], [336200, 6234500], [336100, 6234500], [336100, 6234400]]]
    return lot


def _make_plan():
    p = Plan.__new__(Plan)
    p.plan_label        = "DP999001"
    p.plan_type         = "DP"
    p.plan_number       = 999001
    p.is_surveyed       = True
    p.is_current        = True
    p.registration_date = date(2000, 1, 1)
    p.local_file        = None
    return p


def _make_result():
    r = SearchResult.__new__(SearchResult)
    r.address          = _make_address()
    r.subject_lot      = _make_lot()
    r.nearby_lots      = [_make_lot()]
    r.survey_marks     = []
    r.plans            = [_make_plan()]
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


# ── /health ───────────────────────────────────────────────────────────────────

def test_health_returns_200():
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_ok():
    response = client.get("/health")
    assert response.json() == {"status": "ok"}


# ── /search ───────────────────────────────────────────────────────────────────

def test_search_returns_200():
    with patch("server.search", return_value=_make_result()), \
         patch("server.record_search"):
        response = client.get("/search", params={"address": "87 BUNARBA ROAD GYMEA BAY"})
    assert response.status_code == 200


def test_search_returns_feature_collection():
    with patch("server.search", return_value=_make_result()), \
         patch("server.record_search"):
        response = client.get("/search", params={"address": "87 BUNARBA ROAD GYMEA BAY"})
    assert response.json()["type"] == "FeatureCollection"


def test_search_404_on_invalid_address():
    with patch("server.search", return_value=None):
        response = client.get("/search", params={"address": "FAKE ADDRESS XYZ"})
    assert response.status_code == 404


def test_search_requires_address_param():
    response = client.get("/search")
    assert response.status_code == 422


# ── /search/png ───────────────────────────────────────────────────────────────

def test_search_png_404_on_invalid_address():
    with patch("server.search", return_value=None):
        response = client.get("/search/png", params={"address": "FAKE ADDRESS XYZ"})
    assert response.status_code == 404


def test_search_png_requires_address_param():
    response = client.get("/search/png")
    assert response.status_code == 422


# ── /full-search ──────────────────────────────────────────────────────────────

def test_full_search_404_on_invalid_address(tmp_path):
    with patch("server.search", return_value=None):
        response = client.get("/full-search", params={
            "address": "FAKE ADDRESS XYZ",
            "output_folder": str(tmp_path),
        })
    assert response.status_code == 404


def test_full_search_requires_output_folder():
    response = client.get("/full-search", params={"address": "87 BUNARBA ROAD GYMEA BAY"})
    assert response.status_code == 422


def test_full_search_returns_summary_keys(tmp_path):
    with patch("server.search", return_value=_make_result()), \
         patch("server.fetch_cre_map_image", return_value=None), \
         patch("server.draw_png"), \
         patch("server.download_plans", return_value=_make_result()), \
         patch("server.generate_report", return_value=tmp_path / "ss_report.pdf"), \
         patch("server.record_search"):
        response = client.get("/full-search", params={
            "address": "87 BUNARBA ROAD GYMEA BAY",
            "output_folder": str(tmp_path),
        })
    assert response.status_code == 200
    data = response.json()
    assert "address_resolved" in data
    assert "lot_count" in data
    assert "mark_count" in data
    assert "plan_count" in data


# ── /history ──────────────────────────────────────────────────────────────────

def test_history_returns_200():
    with patch("server.get_history", return_value=[]):
        response = client.get("/history")
    assert response.status_code == 200


def test_history_returns_list():
    with patch("server.get_history", return_value=[]):
        response = client.get("/history")
    assert isinstance(response.json(), list)


# ── /plan/{plan_label} ────────────────────────────────────────────────────────

def test_plan_endpoint_404_on_unknown():
    with patch("server.get_plan_info", return_value=None):
        response = client.get("/plan/DP000000")
    assert response.status_code == 404


def test_plan_endpoint_returns_200_when_found():
    with patch("server.get_plan_info", return_value=_make_plan()):
        response = client.get("/plan/DP999001")
    assert response.status_code == 200


# ── /mark/{type}/{number} ─────────────────────────────────────────────────────

def test_mark_endpoint_404_on_unknown():
    with patch("server.get_mark_by_reference", return_value=None):
        response = client.get("/mark/SS/99999")
    assert response.status_code == 404
