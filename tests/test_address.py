import json
import urllib.parse
from pathlib import Path

import pytest
import responses as resp

from service.api.address import get_address_coordinates, ADDR_URL, ADMIN_BASE
from service.models import Address

FIXTURES = Path(__file__).parent / "fixtures"
ADDRESS = "87 BUNARBA ROAD GYMEA BAY"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def _addr_callback(request):
    """Returns MGA or WGS84 fixture depending on outSR query param."""
    params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(request.url).query))
    data = _load("address_wgs84_response.json") if params.get("outSR") == "4326" else _load("address_response.json")
    return (200, {"Content-Type": "application/json"}, json.dumps(data))


def _register_valid_address():
    resp.add_callback(resp.GET, ADDR_URL, callback=_addr_callback, content_type="application/json")
    resp.add(resp.GET, f"{ADMIN_BASE}/2/query",  json=_load("admin_suburb_response.json"))
    resp.add(resp.GET, f"{ADMIN_BASE}/8/query",  json=_load("admin_lga_response.json"))
    resp.add(resp.GET, f"{ADMIN_BASE}/5/query",  json=_load("admin_parish_response.json"))
    resp.add(resp.GET, f"{ADMIN_BASE}/11/query", json=_load("admin_county_response.json"))


@resp.activate
def test_returns_address_object():
    _register_valid_address()
    assert isinstance(get_address_coordinates(ADDRESS), Address)


@resp.activate
def test_invalid_address_returns_none():
    resp.add(resp.GET, ADDR_URL, json={"features": []})
    assert get_address_coordinates("FAKE ADDRESS THAT DOES NOT EXIST XYZ") is None


@resp.activate
def test_input_string_preserved():
    _register_valid_address()
    result = get_address_coordinates(ADDRESS)
    assert result.input_string == ADDRESS


@resp.activate
def test_resolved_string_populated():
    _register_valid_address()
    result = get_address_coordinates(ADDRESS)
    assert result.resolved_string == "87 BUNARBA ROAD GYMEA BAY"


@resp.activate
def test_easting_in_mga_range():
    _register_valid_address()
    result = get_address_coordinates(ADDRESS)
    assert 300000 < result.easting < 700000


@resp.activate
def test_northing_in_mga_range():
    _register_valid_address()
    result = get_address_coordinates(ADDRESS)
    assert 6000000 < result.northing < 7000000


@resp.activate
def test_longitude_in_nsw_range():
    _register_valid_address()
    result = get_address_coordinates(ADDRESS)
    assert result.longitude is not None
    assert 141 < result.longitude < 154


@resp.activate
def test_latitude_in_nsw_range():
    _register_valid_address()
    result = get_address_coordinates(ADDRESS)
    assert result.latitude is not None
    assert -38 < result.latitude < -28


@resp.activate
def test_admin_boundaries_populated():
    _register_valid_address()
    result = get_address_coordinates(ADDRESS)

    assert result.suburb  == "GYMEA BAY"
    assert result.lga     == "SUTHERLAND SHIRE"
    assert result.parish  == "WORONORA"
    assert result.county  == "CUMBERLAND"

    assert isinstance(result.suburb, str)
    assert isinstance(result.lga,    str)
    assert isinstance(result.parish, str)
    assert isinstance(result.county, str)
