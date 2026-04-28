# NOTE: These tests make real HTTP calls to the NSW Spatial Services APIs.
# Mocked HTTP tests will be added in Phase 3.
# Requires internet connection to run.

from api.address import get_address_coordinates
from models import Address
from utils import expand_address

ADDRESS = expand_address("483 GEORGE STREET SYDNEY")

def test_returns_address_object():
    result = get_address_coordinates(ADDRESS)
    assert isinstance(result, Address)

def test_invalid_address_returns_none():
    result = get_address_coordinates("FAKE ADDRESS THAT DOES NOT EXIST XYZ")
    assert result is None

def test_input_string_preserved():
    result = get_address_coordinates(ADDRESS)
    assert result.input_string == ADDRESS

def test_resolved_string_populated():
    result = get_address_coordinates(ADDRESS)
    assert result.resolved_string is not None
    assert len(result.resolved_string) > 0

def test_easting_in_mga_range():
    """MGA2020 Zone 56 eastings for NSW are roughly 300000-700000"""
    result = get_address_coordinates(ADDRESS)
    assert 300000 < result.easting < 700000

def test_northing_in_mga_range():
    """MGA2020 Zone 56 northings for NSW are roughly 6000000-7000000"""
    result = get_address_coordinates(ADDRESS)
    assert 6000000 < result.northing < 7000000

def test_longitude_in_nsw_range():
    """NSW longitudes are roughly 141-154 degrees east"""
    result = get_address_coordinates(ADDRESS)
    assert result.longitude is not None
    assert 141 < result.longitude < 154

def test_latitude_in_nsw_range():
    """NSW latitudes are roughly -28 to -38 degrees"""
    result = get_address_coordinates(ADDRESS)
    assert result.latitude is not None
    assert -38 < result.latitude < -28

def test_admin_boundaries_populated():
    """suburb, lga, parish, county should all be populated for a known address"""
    result = get_address_coordinates(ADDRESS)
    
    # All four should be populated
    assert result.suburb is not None
    assert result.lga is not None
    assert result.parish is not None
    assert result.county is not None

    # Should be strings
    assert isinstance(result.suburb, str)
    assert isinstance(result.lga, str)
    assert isinstance(result.parish, str)
    assert isinstance(result.county, str)

    # Check field length constraints from the API schema
    assert len(result.suburb) <= 40   # suburbname length: 40
    assert len(result.lga) <= 60      # lganame length: 60
    assert len(result.parish) <= 24   # parishname length: 24
    assert len(result.county) <= 16   # countyname length: 16

    # Check known values for 483 GEORGE STREET SYDNEY
    assert result.suburb == "SYDNEY"
    assert result.lga == "SYDNEY"
    assert result.parish == "ST ANDREW"
    assert result.county == "CUMBERLAND"