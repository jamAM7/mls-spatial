import json
from pathlib import Path

import responses as resp

from service.api.lot import get_lot_info, LOT_URL
from service.models import Lot

FIXTURES = Path(__file__).parent / "fixtures"

X    = 336152.34
Y    = 6234478.21
EPSG = 7856


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@resp.activate
def test_returns_list():
    resp.add(resp.GET, LOT_URL, json=_load("lot_response.json"))
    result = get_lot_info(X, Y, EPSG)
    assert isinstance(result, list)


@resp.activate
def test_returns_lot_objects():
    resp.add(resp.GET, LOT_URL, json=_load("lot_response.json"))
    result = get_lot_info(X, Y, EPSG)
    assert all(isinstance(lot, Lot) for lot in result)


@resp.activate
def test_subject_lot_in_results():
    resp.add(resp.GET, LOT_URL, json=_load("lot_response.json"))
    result = get_lot_info(X, Y, EPSG)
    plan_labels = [lot.plan_label for lot in result]
    assert "DP999001" in plan_labels


@resp.activate
def test_geometry_populated():
    resp.add(resp.GET, LOT_URL, json=_load("lot_response.json"))
    result = get_lot_info(X, Y, EPSG)
    for lot in result:
        assert isinstance(lot.geometry, list)
        assert len(lot.geometry) > 0


@resp.activate
def test_geometry_contains_coordinate_pairs():
    resp.add(resp.GET, LOT_URL, json=_load("lot_response.json"))
    result = get_lot_info(X, Y, EPSG)
    for lot in result:
        for point in lot.geometry:
            assert len(point) == 2
            assert 300000 < point[0] < 700000   # easting
            assert 6000000 < point[1] < 7000000  # northing


@resp.activate
def test_title_status_decoded():
    resp.add(resp.GET, LOT_URL, json=_load("lot_response.json"))
    result = get_lot_info(X, Y, EPSG)
    for lot in result:
        if lot.its_title_status is not None:
            assert lot.its_title_status_label is not None
            assert isinstance(lot.its_title_status_label, str)
    # Fixture uses itstitlestatus=1 → "Torrens Title"
    assert result[0].its_title_status_label == "Torrens Title"


@resp.activate
def test_is_subject_defaults_false():
    resp.add(resp.GET, LOT_URL, json=_load("lot_response.json"))
    result = get_lot_info(X, Y, EPSG)
    assert all(lot.is_subject is False for lot in result)


@resp.activate
def test_invalid_coordinates_returns_none():
    resp.add(resp.GET, LOT_URL, json={"features": [], "exceededTransferLimit": False})
    assert get_lot_info(0.0, 0.0, EPSG) is None
