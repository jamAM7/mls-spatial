"""
property.py — NSW Land Parcel Property Theme, FeatureServer/12 (Property layer)
Fetches property address strings to enrich Lot features.

Each lot centroid is queried individually against FS/12 to find which property
polygon it falls inside, returning the address for that property.
"""

import requests
from service.config import BASE

PROPERTY_URL = f"{BASE}/NSW_Land_Parcel_Property_Theme_multiCRS/FeatureServer/12/query"


def get_address_at_point(x: float, y: float, epsg: int) -> str | None:
    """
    Query FS/12 at a single point. Returns the address of the property at that
    point, or None if no property is found.

    Used to match individual lot centroids to property addresses.
    Distance is set to 1m to effectively do a point-in-polygon lookup.
    """
    params = {
        "geometry":          f'{{"x": {x}, "y": {y}, "spatialReference": {{"wkid": {epsg}}}}}',
        "geometryType":      "esriGeometryPoint",
        "spatialRel":        "esriSpatialRelIntersects",
        "distance":          1,
        "units":             "esriSRUnit_Meter",
        "inSR":              str(epsg),
        "outFields":         "address,housenumber",
        "returnGeometry":    False,
        "resultRecordCount": 1,
        "f":                 "json",
    }
    try:
        data = requests.get(PROPERTY_URL, params=params).json()
        features = data.get("features", [])
        if features:
            attrs = features[0]["attributes"]
            return attrs.get("address") or attrs.get("housenumber") or None
    except Exception:
        pass
    return None