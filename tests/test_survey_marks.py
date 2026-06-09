import json
from datetime import date, datetime
from pathlib import Path

import responses as resp

from service.api.survey_marks import get_survey_mark_info, SM_URL
from service.models import SurveyMark

FIXTURES = Path(__file__).parent / "fixtures"

X    = 336152.34
Y    = 6234478.21
EPSG = 7856


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@resp.activate
def test_returns_list():
    resp.add(resp.GET, SM_URL, json=_load("survey_marks_response.json"))
    result = get_survey_mark_info(X, Y, EPSG)
    assert isinstance(result, list)


@resp.activate
def test_returns_survey_mark_objects():
    resp.add(resp.GET, SM_URL, json=_load("survey_marks_response.json"))
    result = get_survey_mark_info(X, Y, EPSG)
    assert all(isinstance(mark, SurveyMark) for mark in result)


@resp.activate
def test_retrieved_at_is_set():
    resp.add(resp.GET, SM_URL, json=_load("survey_marks_response.json"))
    result = get_survey_mark_info(X, Y, EPSG)
    for mark in result:
        assert mark.retrieved_at is not None
        assert isinstance(mark.retrieved_at, datetime)


@resp.activate
def test_retrieved_at_is_recent():
    resp.add(resp.GET, SM_URL, json=_load("survey_marks_response.json"))
    result = get_survey_mark_info(X, Y, EPSG)
    for mark in result:
        assert (datetime.now() - mark.retrieved_at).total_seconds() < 60


@resp.activate
def test_easting_northing_populated():
    resp.add(resp.GET, SM_URL, json=_load("survey_marks_response.json"))
    result = get_survey_mark_info(X, Y, EPSG)
    for mark in result:
        assert mark.easting is not None
        assert mark.northing is not None


@resp.activate
def test_easting_in_mga_range():
    resp.add(resp.GET, SM_URL, json=_load("survey_marks_response.json"))
    result = get_survey_mark_info(X, Y, EPSG)
    for mark in result:
        assert 300000 < mark.easting < 700000


@resp.activate
def test_northing_in_mga_range():
    resp.add(resp.GET, SM_URL, json=_load("survey_marks_response.json"))
    result = get_survey_mark_info(X, Y, EPSG)
    for mark in result:
        assert 6000000 < mark.northing < 7000000


@resp.activate
def test_longitude_latitude_populated():
    resp.add(resp.GET, SM_URL, json=_load("survey_marks_response.json"))
    result = get_survey_mark_info(X, Y, EPSG)
    for mark in result:
        assert mark.longitude is not None
        assert mark.latitude is not None


@resp.activate
def test_mark_number_populated():
    resp.add(resp.GET, SM_URL, json=_load("survey_marks_response.json"))
    result = get_survey_mark_info(X, Y, EPSG)
    for mark in result:
        assert mark.mark_number is not None


@resp.activate
def test_gda_date_parsed_from_epoch():
    """gdadate epoch ms should be converted to a date object."""
    resp.add(resp.GET, SM_URL, json=_load("survey_marks_response.json"))
    result = get_survey_mark_info(X, Y, EPSG)
    mark = result[0]
    assert isinstance(mark.gda_date, date)
    assert mark.gda_date == date(2000, 1, 1)


@resp.activate
def test_null_date_fields_stay_none():
    """Marks with null ahddate/gdaheightdate should have None, not raise."""
    resp.add(resp.GET, SM_URL, json=_load("survey_marks_response.json"))
    result = get_survey_mark_info(X, Y, EPSG)
    mark = result[1]  # second fixture mark has null ahddate and gdaheightdate
    assert mark.ahd_date is None
    assert mark.gda_height_date is None


@resp.activate
def test_invalid_coordinates_returns_none():
    resp.add(resp.GET, SM_URL, json={"features": []})
    assert get_survey_mark_info(0.0, 0.0, EPSG) is None
