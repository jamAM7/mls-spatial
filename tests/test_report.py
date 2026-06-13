"""
test_report.py — Tests for report.py PDF generation.
"""
import json
import tempfile
from datetime import date, datetime
from pathlib import Path

import pytest

from service.report import generate_report, safe, load_json


# ── safe() helper ─────────────────────────────────────────────────────────────

def test_safe_returns_value():
    assert safe("hello") == "hello"


def test_safe_returns_dash_for_none():
    assert safe(None) == "-"


def test_safe_returns_dash_for_empty_string():
    assert safe("") == "-"


def test_safe_returns_zero():
    assert safe(0) == 0  # 0 is a valid value, not empty


def test_safe_returns_false():
    assert safe(False) == False  # False is a valid value


# ── generate_report ───────────────────────────────────────────────────────────

def _make_summary(tmp_path: Path) -> dict:
    summary = {
        "address_resolved": "87 BUNARBA ROAD GYMEA BAY",
        "suburb":           "GYMEA BAY",
        "lga":              "SUTHERLAND SHIRE",
        "parish":           "WORONORA",
        "county":           "CUMBERLAND",
        "subject_lot":      "Lot 1 DP999001",
        "search_radius_m":  200,
        "datum":            "GDA2020",
        "mga_zone":         56,
        "epsg":             7856,
        "lot_count":        5,
        "plan_count":       2,
        "mark_count":       3,
        "searched_at":      "2024-01-01 12:00:00",
    }
    (tmp_path / "ss_summary.json").write_text(json.dumps(summary))
    return summary


def _make_geojson(tmp_path: Path) -> dict:
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [[[0,0],[1,0],[1,1],[0,1],[0,0]]]},
                "properties": {
                    "feature_type":           "lot",
                    "lot_number":             "1",
                    "plan_label":             "DP999001",
                    "section_number":         None,
                    "is_subject":             True,
                    "is_surveyed":            True,
                    "its_title_status_label": "Torrens Title",
                    "has_stratum":            False,
                    "stratum_level_label":    "Surface",
                    "plan_lot_area":          500.0,
                    "plan_lot_area_units":    "m2",
                    "registration_date":      "2000-01-01",
                    "plan_type":              "DP",
                }
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [336152.0, 6234478.0]},
                "properties": {
                    "feature_type":               "survey_mark",
                    "mark_number":                "12345",
                    "mark_type":                  "SS",
                    "mark_status":                "F",
                    "mark_symbol_label":          "SS Established GDA + Accurate AHD",
                    "marksymbol":                 "SSR",
                    "gda_class":                  "3A",
                    "gda_pos_uncertainty_label":  "0.010m",
                    "gda_loc_uncertainty_label":  "0.020m",
                    "ahd_height_label":           "12.500m",
                    "ahd_class":                  "LC",
                    "mga_csf_2020_label":         "1.00024",
                    "mga_zone":                   56,
                    "mga_easting_label":          "336152.000m E",
                    "mga_northing_label":         "6234478.000m N",
                }
            },
        ]
    }
    (tmp_path / "ss_search_result.geojson").write_text(json.dumps(geojson))
    return geojson


def test_report_creates_pdf(tmp_path):
    _make_summary(tmp_path)
    _make_geojson(tmp_path)
    pdf_path = generate_report(tmp_path)
    assert pdf_path.exists()
    assert pdf_path.suffix == ".pdf"
    assert pdf_path.name == "ss_report.pdf"


def test_report_pdf_has_content(tmp_path):
    _make_summary(tmp_path)
    _make_geojson(tmp_path)
    pdf_path = generate_report(tmp_path)
    assert pdf_path.stat().st_size > 1000  # non-trivial PDF


def test_report_returns_path_object(tmp_path):
    _make_summary(tmp_path)
    _make_geojson(tmp_path)
    result = generate_report(tmp_path)
    assert isinstance(result, Path)


def test_report_written_to_output_folder(tmp_path):
    _make_summary(tmp_path)
    _make_geojson(tmp_path)
    pdf_path = generate_report(tmp_path)
    assert pdf_path.parent == tmp_path


def test_report_no_subject_lot(tmp_path):
    """Report should not crash when no subject lot exists in geojson."""
    _make_summary(tmp_path)
    geojson = {"type": "FeatureCollection", "features": []}
    (tmp_path / "ss_search_result.geojson").write_text(json.dumps(geojson))
    pdf_path = generate_report(tmp_path)
    assert pdf_path.exists()


def test_report_no_marks(tmp_path):
    """Report should not crash when there are no survey marks."""
    _make_summary(tmp_path)
    geojson = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[0,0],[1,0],[1,1],[0,0]]]},
            "properties": {
                "feature_type": "lot", "lot_number": "1", "plan_label": "DP999001",
                "section_number": None, "is_subject": True, "is_surveyed": True,
                "its_title_status_label": "Torrens Title", "has_stratum": False,
                "stratum_level_label": "Surface", "plan_lot_area": None,
                "plan_lot_area_units": None, "registration_date": None, "plan_type": "DP",
            }
        }]
    }
    (tmp_path / "ss_search_result.geojson").write_text(json.dumps(geojson))
    assert generate_report(tmp_path).exists()


def test_report_missing_summary_raises(tmp_path):
    _make_geojson(tmp_path)
    with pytest.raises(Exception):
        generate_report(tmp_path)


def test_report_missing_geojson_raises(tmp_path):
    _make_summary(tmp_path)
    with pytest.raises(Exception):
        generate_report(tmp_path)
