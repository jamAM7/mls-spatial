import json
from pathlib import Path

import pytest
import responses as resp

import service.api.plan as plan_module
from service.api.plan import get_plan_info
from service.models import Plan

FIXTURES = Path(__file__).parent / "fixtures"

PLAN_BASE  = "https://maps.six.nsw.gov.au/arcgis/rest/services/sixmaps/Boundaries/MapServer"
LAYER_URL  = f"{PLAN_BASE}/2"
QUERY_URL  = f"{PLAN_BASE}/2/query"

KNOWN_PLAN   = "DP999001"
UNKNOWN_PLAN = "DP000000001"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture(autouse=True)
def reset_domain_cache():
    """Reset module-level cache so each test fetches domain metadata fresh."""
    plan_module._domain_cache = None
    yield
    plan_module._domain_cache = None


def _register_valid_plan():
    resp.add(resp.GET, LAYER_URL, json=_load("plan_layer_response.json"))
    resp.add(resp.GET, QUERY_URL, json=_load("plan_response.json"))


@resp.activate
def test_returns_plan_object():
    _register_valid_plan()
    assert isinstance(get_plan_info(KNOWN_PLAN), Plan)


@resp.activate
def test_unknown_plan_returns_none():
    resp.add(resp.GET, LAYER_URL, json=_load("plan_layer_response.json"))
    resp.add(resp.GET, QUERY_URL, json={"features": []})
    assert get_plan_info(UNKNOWN_PLAN) is None


@resp.activate
def test_plan_label_correct():
    _register_valid_plan()
    assert get_plan_info(KNOWN_PLAN).plan_label == "DP999001"


@resp.activate
def test_plan_type_correct():
    _register_valid_plan()
    assert get_plan_info(KNOWN_PLAN).plan_type == "DP"


@resp.activate
def test_plan_number_correct():
    _register_valid_plan()
    assert get_plan_info(KNOWN_PLAN).plan_number == 999001


@resp.activate
def test_is_surveyed_is_bool():
    _register_valid_plan()
    result = get_plan_info(KNOWN_PLAN)
    if result.is_surveyed is not None:
        assert isinstance(result.is_surveyed, bool)
    # Fixture: issurveyed=1 with classsubtype=1 (DP) → True
    assert result.is_surveyed is True


@resp.activate
def test_is_current_is_bool():
    _register_valid_plan()
    result = get_plan_info(KNOWN_PLAN)
    if result.is_current is not None:
        assert isinstance(result.is_current, bool)
    assert result.is_current is True


@resp.activate
def test_registration_date_populated():
    _register_valid_plan()
    result = get_plan_info(KNOWN_PLAN)
    assert result.registration_date is not None
    # Fixture: registrationdate=946684800000 ms → 2000-01-01
    assert result.registration_date == "2000-01-01"


@resp.activate
def test_local_file_defaults_none():
    _register_valid_plan()
    assert get_plan_info(KNOWN_PLAN).local_file is None


def test_invalid_plan_label_raises():
    with pytest.raises(ValueError):
        get_plan_info("NOTAPLAN")
