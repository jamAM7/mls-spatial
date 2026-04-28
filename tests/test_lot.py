# NOTE: These tests make real HTTP calls to the NSW Spatial Services APIs.
# Mocked HTTP tests will be added in Phase 3.
# Requires internet connection to run.

from server.api.address import get_address_coordinates
from server.api.lot import get_lot_info
from service.models import Lot
from service.utils import expand_address

ADDRESS = expand_address("483 GEORGE STREET SYDNEY")

def _get_coords():
    result = get_address_coordinates(ADDRESS)
    assert result is not None
    return result.easting, result.northing

def test_returns_list():
    x, y = _get_coords()
    result = get_lot_info(x, y)
    assert isinstance(result, list)

def test_returns_lot_objects():
    x, y = _get_coords()
    result = get_lot_info(x, y)
    assert all(isinstance(lot, Lot) for lot in result)

def test_subject_lot_in_results():
    """DP1048011 lot 100 is the subject lot for 483 George Street Sydney"""
    x, y = _get_coords()
    result = get_lot_info(x, y)
    plan_labels = [lot.plan_label for lot in result]
    assert "DP1048011" in plan_labels

def test_geometry_populated():
    x, y = _get_coords()
    result = get_lot_info(x, y)
    for lot in result:
        assert isinstance(lot.geometry, list)
        assert len(lot.geometry) > 0

def test_geometry_contains_coordinate_pairs():
    x, y = _get_coords()
    result = get_lot_info(x, y)
    for lot in result:
        for point in lot.geometry:
            assert len(point) == 2
            assert 300000 < point[0] < 700000    # easting
            assert 6000000 < point[1] < 7000000  # northing

def test_title_status_decoded():
    x, y = _get_coords()
    result = get_lot_info(x, y)
    for lot in result:
        if lot.its_title_status is not None:
            assert lot.its_title_status_label is not None
            assert isinstance(lot.its_title_status_label, str)

def test_is_subject_defaults_false():
    """is_subject should always be False — set by search.py not api"""
    x, y = _get_coords()
    result = get_lot_info(x, y)
    assert all(lot.is_subject == False for lot in result)

def test_invalid_coordinates_returns_none():
    result = get_lot_info(0.0, 0.0)
    assert result is None