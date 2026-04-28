# NOTE: These tests make real HTTP calls to the NSW Spatial Services APIs.
# Mocked HTTP tests will be added in Phase 3.
# Requires internet connection to run.

from api.plan import get_plan_info
from models import Plan

KNOWN_PLAN = "DP1048011"
UNKNOWN_PLAN = "DP999999999"

def test_returns_plan_object():
    result = get_plan_info(KNOWN_PLAN)
    assert isinstance(result, Plan)

def test_unknown_plan_returns_none():
    result = get_plan_info(UNKNOWN_PLAN)
    assert result is None

def test_plan_label_correct():
    result = get_plan_info(KNOWN_PLAN)
    assert result.plan_label == "DP1048011"

def test_plan_type_correct():
    result = get_plan_info(KNOWN_PLAN)
    assert result.plan_type == "DP"

def test_plan_number_correct():
    result = get_plan_info(KNOWN_PLAN)
    assert result.plan_number == 1048011

def test_is_surveyed_is_bool():
    """is_surveyed must be bool not string"""
    result = get_plan_info(KNOWN_PLAN)
    if result.is_surveyed is not None:
        assert isinstance(result.is_surveyed, bool)

def test_is_current_is_bool():
    result = get_plan_info(KNOWN_PLAN)
    if result.is_current is not None:
        assert isinstance(result.is_current, bool)

def test_registration_date_populated():
    result = get_plan_info(KNOWN_PLAN)
    assert result.registration_date is not None

def test_local_file_defaults_none():
    """local_file should be None until drive.py downloads it"""
    result = get_plan_info(KNOWN_PLAN)
    assert result.local_file is None

def test_invalid_plan_label_raises():
    """Unrecognised format should raise ValueError"""
    import pytest
    with pytest.raises(ValueError):
        get_plan_info("NOTAPLAN")