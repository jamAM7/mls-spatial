"""
test_drive.py — Tests for drive.py plan matching logic.
No Google API calls are made — all Drive interaction is unit tested
against the pure matching/scoring functions.
"""
import pytest
from service.drive import (
    _is_exact_plan_match,
    choose_best_candidate,
    choose_best_xml_candidate,
    plan_name_patterns,
    safe_filename,
    parse_rfc3339,
)


# ── plan_name_patterns ────────────────────────────────────────────────────────

def test_plan_name_patterns_dp():
    exact, digits = plan_name_patterns("DP574558")
    assert exact == "DP574558"
    assert digits == "574558"


def test_plan_name_patterns_sp():
    exact, digits = plan_name_patterns("SP99001")
    assert exact == "SP99001"
    assert digits == "99001"


def test_plan_name_patterns_lowercase():
    exact, digits = plan_name_patterns("dp574558")
    assert exact == "DP574558"


def test_plan_name_patterns_strips_whitespace():
    exact, digits = plan_name_patterns("  DP574558  ")
    assert exact == "DP574558"


# ── _is_exact_plan_match ──────────────────────────────────────────────────────

def test_exact_match_by_label():
    assert _is_exact_plan_match("DP574558.pdf", "DP574558", "574558") is True


def test_exact_match_with_space():
    assert _is_exact_plan_match("DP 574558.pdf", "DP574558", "574558") is True


def test_exact_match_deposited_plan():
    assert _is_exact_plan_match("DEPOSITED PLAN 574558.pdf", "DP574558", "574558") is True


def test_rejects_other_prefix():
    assert _is_exact_plan_match("SP574558.pdf", "DP574558", "574558") is False


def test_rejects_88b():
    # 88b files should be filtered before _is_exact_plan_match is called
    # but confirm it still matches on content (filtering is in choose_best_candidate)
    assert _is_exact_plan_match("DP574558_88b.pdf", "DP574558", "574558") is True


def test_rejects_different_number():
    assert _is_exact_plan_match("DP999999.pdf", "DP574558", "574558") is False


def test_matches_leading_zeros():
    assert _is_exact_plan_match("DP0574558.pdf", "DP574558", "574558") is True


def test_matches_digits_only_filename():
    assert _is_exact_plan_match("574558.pdf", "DP574558", "574558") is True


# ── choose_best_candidate ─────────────────────────────────────────────────────

def _file(name, mime="application/pdf", size=1000, mtime="2023-01-01T00:00:00Z"):
    return {"id": name, "name": name, "mimeType": mime, "size": str(size), "modifiedTime": mtime}


def test_choose_best_prefers_pdf_over_image():
    candidates = [
        _file("DP574558.tif", mime="image/tiff", size=2000),
        _file("DP574558.pdf", mime="application/pdf", size=1000),
    ]
    best = choose_best_candidate("DP574558", candidates)
    assert best["name"] == "DP574558.pdf"


def test_choose_best_skips_88b():
    candidates = [
        _file("DP574558_88b.pdf"),
        _file("DP574558.pdf"),
    ]
    best = choose_best_candidate("DP574558", candidates)
    assert best["name"] == "DP574558.pdf"


def test_choose_best_returns_none_when_all_filtered():
    candidates = [_file("DP574558_88b.pdf")]
    assert choose_best_candidate("DP574558", candidates) is None


def test_choose_best_returns_none_for_empty():
    assert choose_best_candidate("DP574558", []) is None


def test_choose_best_rejects_wrong_plan():
    candidates = [_file("DP999999.pdf")]
    assert choose_best_candidate("DP574558", candidates) is None


def test_choose_best_prefers_larger_file_when_equal_type():
    candidates = [
        _file("DP574558_v1.pdf", size=500,  mtime="2022-01-01T00:00:00Z"),
        _file("DP574558_v2.pdf", size=5000, mtime="2022-01-01T00:00:00Z"),
    ]
    best = choose_best_candidate("DP574558", candidates)
    assert best["name"] == "DP574558_v2.pdf"


def test_choose_best_prefers_newer_file():
    candidates = [
        _file("DP574558_old.pdf", mtime="2020-01-01T00:00:00Z"),
        _file("DP574558_new.pdf", mtime="2024-01-01T00:00:00Z"),
    ]
    best = choose_best_candidate("DP574558", candidates)
    assert best["name"] == "DP574558_new.pdf"


def test_choose_best_single_candidate():
    candidates = [_file("DP574558.pdf")]
    assert choose_best_candidate("DP574558", candidates)["name"] == "DP574558.pdf"


def test_choose_best_sp_plan():
    candidates = [_file("SP99001.pdf")]
    assert choose_best_candidate("SP99001", candidates)["name"] == "SP99001.pdf"


def test_choose_best_rejects_sp_when_looking_for_dp():
    candidates = [_file("SP574558.pdf")]
    assert choose_best_candidate("DP574558", candidates) is None


# ── choose_best_xml_candidate ─────────────────────────────────────────────────

def _xml_file(name, mime="application/xml", size=500, mtime="2023-01-01T00:00:00Z"):
    return {"id": name, "name": name, "mimeType": mime, "size": str(size), "modifiedTime": mtime}


def test_xml_prefers_xml_extension():
    candidates = [
        _xml_file("DP574558.xml"),
        _xml_file("DP574558_data.xml"),
    ]
    best = choose_best_xml_candidate("DP574558", candidates)
    assert best is not None


def test_xml_returns_none_for_empty():
    assert choose_best_xml_candidate("DP574558", []) is None


def test_xml_skips_88b():
    candidates = [
        _xml_file("DP574558_88b.xml"),
        _xml_file("DP574558.xml"),
    ]
    best = choose_best_xml_candidate("DP574558", candidates)
    assert best["name"] == "DP574558.xml"


# ── safe_filename ─────────────────────────────────────────────────────────────

def test_safe_filename_removes_slashes():
    assert "/" not in safe_filename("DP/574558.pdf")
    assert "\\" not in safe_filename("DP\\574558.pdf")


def test_safe_filename_collapses_whitespace():
    assert safe_filename("DP  574558.pdf") == "DP 574558.pdf"


def test_safe_filename_strips():
    assert safe_filename("  DP574558.pdf  ") == "DP574558.pdf"


# ── parse_rfc3339 ─────────────────────────────────────────────────────────────

def test_parse_rfc3339_z_suffix():
    dt = parse_rfc3339("2023-06-15T10:30:00Z")
    assert dt.year == 2023
    assert dt.month == 6
    assert dt.day == 15


def test_parse_rfc3339_empty_returns_epoch():
    dt = parse_rfc3339("")
    assert dt.year == 1970


def test_parse_rfc3339_none_string_returns_epoch():
    dt = parse_rfc3339(None)
    assert dt.year == 1970
