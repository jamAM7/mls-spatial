# NOTE: These tests make real HTTP calls to the NSW Spatial Services APIs.
# Mocked HTTP tests will be added in Phase 3.
# Requires internet connection to run.

from server.api.address import get_address_coordinates
from server.api.survey_marks import get_survey_mark_info
from service.models import SurveyMark
from datetime import datetime
from service.utils import expand_address

ADDRESS = expand_address("483 GEORGE STREET SYDNEY")

def _get_coords():
    result = get_address_coordinates(ADDRESS)
    assert result is not None
    return result.easting, result.northing

def test_returns_list():
    x, y = _get_coords()
    result = get_survey_mark_info(x, y)
    assert isinstance(result, list)

def test_returns_survey_mark_objects():
    x, y = _get_coords()
    result = get_survey_mark_info(x, y)
    assert all(isinstance(mark, SurveyMark) for mark in result)

def test_retrieved_at_is_set():
    """retrieved_at must always be set at time of API call"""
    x, y = _get_coords()
    result = get_survey_mark_info(x, y)
    for mark in result:
        assert mark.retrieved_at is not None
        assert isinstance(mark.retrieved_at, datetime)

def test_retrieved_at_is_recent():
    """retrieved_at should be within the last minute"""
    x, y = _get_coords()
    result = get_survey_mark_info(x, y)
    for mark in result:
        age_seconds = (datetime.now() - mark.retrieved_at).total_seconds()
        assert age_seconds < 60

def test_easting_northing_populated():
    x, y = _get_coords()
    result = get_survey_mark_info(x, y)
    for mark in result:
        assert mark.easting is not None
        assert mark.northing is not None

def test_easting_in_mga_range():
    x, y = _get_coords()
    result = get_survey_mark_info(x, y)
    for mark in result:
        assert 300000 < mark.easting < 700000

def test_northing_in_mga_range():
    x, y = _get_coords()
    result = get_survey_mark_info(x, y)
    for mark in result:
        assert 6000000 < mark.northing < 7000000

def test_longitude_latitude_populated():
    x, y = _get_coords()
    result = get_survey_mark_info(x, y)
    for mark in result:
        assert mark.longitude is not None
        assert mark.latitude is not None

def test_mark_number_populated():
    x, y = _get_coords()
    result = get_survey_mark_info(x, y)
    for mark in result:
        assert mark.mark_number is not None

def test_invalid_coordinates_returns_none():
    result = get_survey_mark_info(0.0, 0.0)
    assert result is None