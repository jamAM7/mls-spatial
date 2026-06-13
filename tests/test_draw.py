"""
test_draw.py — Tests for draw.py symbol loading and helper functions.
Does not test matplotlib rendering (no display available in CI).
"""
import io
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image

from clients.draw import (
    _filename_to_key,
    _get_symbol,
    _get_lots,
    _get_marks,
    _get_roads,
    _get_centrelines,
    _fallback_colour,
    _fallback_symbol,
    _SYMBOL_CACHE,
    _SYMBOL_DIR,
)


# ── _filename_to_key ──────────────────────────────────────────────────────────

def test_filename_to_key_established_gda_ahd():
    assert _filename_to_key("SS_Established_GDA_+_Accurate_AHD") == "SSR"


def test_filename_to_key_established_gda_only():
    assert _filename_to_key("PM_Established_GDA_Only") == "PMP"


def test_filename_to_key_accurate_ahd_only():
    assert _filename_to_key("TS_Accurate_AHD_Only") == "TSG"


def test_filename_to_key_approx_gda_ahd():
    assert _filename_to_key("CR_Approx_GDA_+_Accurate_AHD") == "CRC"


def test_filename_to_key_approx_gda_only():
    assert _filename_to_key("MM_Approx_GDA_Only") == "MMB"


def test_filename_to_key_unknown():
    assert _filename_to_key("CP_Unknown_GDA_+_AHD") == "CPU"


def test_filename_to_key_gb():
    assert _filename_to_key("GB_Established_GDA_+_Accurate_AHD") == "GBR"


def test_filename_to_key_unrecognised_returns_none():
    assert _filename_to_key("UNKNOWN_LABEL") is None


def test_filename_to_key_empty_returns_none():
    assert _filename_to_key("") is None


# ── _get_symbol ───────────────────────────────────────────────────────────────

def test_get_symbol_returns_none_when_dir_missing():
    with patch("clients.draw._SYMBOL_DIR", Path("/nonexistent/path")):
        _SYMBOL_CACHE.clear()
        assert _get_symbol("SSR") is None


def test_get_symbol_loads_from_disk(tmp_path):
    # Create a minimal RGBA PNG
    img = Image.new("RGBA", (14, 14), (0, 200, 255, 255))
    png_path = tmp_path / "SS_Established_GDA_+_Accurate_AHD.png"
    img.save(png_path)

    with patch("clients.draw._SYMBOL_DIR", tmp_path):
        _SYMBOL_CACHE.clear()
        result = _get_symbol("SSR")
        assert result is not None
        assert isinstance(result, Image.Image)


def test_get_symbol_caches_on_second_call(tmp_path):
    img = Image.new("RGBA", (14, 14), (0, 200, 255, 255))
    png_path = tmp_path / "SS_Established_GDA_+_Accurate_AHD.png"
    img.save(png_path)

    with patch("clients.draw._SYMBOL_DIR", tmp_path):
        _SYMBOL_CACHE.clear()
        first  = _get_symbol("SSR")
        second = _get_symbol("SSR")
        assert first is second  # same object from cache


def test_get_symbol_returns_none_for_unknown_key(tmp_path):
    with patch("clients.draw._SYMBOL_DIR", tmp_path):
        _SYMBOL_CACHE.clear()
        assert _get_symbol("ZZZZZ") is None


# ── Feature filter helpers ────────────────────────────────────────────────────

def _feature(feature_type):
    return {"type": "Feature", "geometry": {}, "properties": {"feature_type": feature_type}}


def test_get_lots_filters_correctly():
    features = [_feature("lot"), _feature("survey_mark"), _feature("road")]
    assert len(_get_lots(features)) == 1
    assert _get_lots(features)[0]["properties"]["feature_type"] == "lot"


def test_get_marks_filters_correctly():
    features = [_feature("lot"), _feature("survey_mark"), _feature("survey_mark")]
    assert len(_get_marks(features)) == 2


def test_get_roads_filters_correctly():
    features = [_feature("lot"), _feature("road"), _feature("road_centreline")]
    assert len(_get_roads(features)) == 1


def test_get_centrelines_filters_correctly():
    features = [_feature("road"), _feature("road_centreline")]
    assert len(_get_centrelines(features)) == 1


def test_get_lots_empty():
    assert _get_lots([]) == []


def test_get_marks_empty():
    assert _get_marks([]) == []


# ── _fallback_colour ──────────────────────────────────────────────────────────

def test_fallback_colour_established():
    assert _fallback_colour("established gda2020 and accurate ahd71") == "#ff1e28"


def test_fallback_colour_unknown():
    assert _fallback_colour("unknown") == "#11c6ff"


def test_fallback_colour_default():
    assert _fallback_colour("something unrecognised") == "#11c6ff"


def test_fallback_colour_case_insensitive():
    assert _fallback_colour("ESTABLISHED GDA2020 ONLY") == _fallback_colour("established gda2020 only")


def test_fallback_colour_none_returns_default():
    assert _fallback_colour(None) == "#11c6ff"


# ── _fallback_symbol ──────────────────────────────────────────────────────────

def test_fallback_symbol_ss():
    assert _fallback_symbol("SS") == r"$\odot$"


def test_fallback_symbol_pm():
    assert _fallback_symbol("PM") == "s"


def test_fallback_symbol_ts():
    assert _fallback_symbol("TS") == "^"


def test_fallback_symbol_cr():
    assert _fallback_symbol("CR") == "v"


def test_fallback_symbol_mm():
    assert _fallback_symbol("MM") == "P"


def test_fallback_symbol_cp():
    assert _fallback_symbol("CP") == r"$\oplus$"


def test_fallback_symbol_gb():
    assert _fallback_symbol("GB") == "*"


def test_fallback_symbol_unknown_returns_star():
    assert _fallback_symbol("XX") == "*"


def test_fallback_symbol_lowercase():
    assert _fallback_symbol("ss") == r"$\odot$"


def test_fallback_symbol_none_returns_star():
    assert _fallback_symbol(None) == "*"
