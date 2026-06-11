import requests
from service.config import BASE
from service.models import Road, RoadCentreline

ROAD_URL        = f"{BASE}/NSW_Land_Parcel_Property_Theme_multiCRS/FeatureServer/5/query"
CENTRELINE_URL  = f"{BASE}/NSW_Land_Parcel_Property_Theme_multiCRS/FeatureServer/1/query"

# TODO: verify both dicts against layer 5 domain metadata at:
# https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Land_Parcel_Property_Theme_multiCRS/FeatureServer/5?f=json

ROAD_TYPE = {
    1: "Dedicated Road",
    2: "Crown Road",
    3: "Private Road",
    4: "Proposed Road",
    5: "Public Reserve",
}

ROAD_CORRIDOR_TYPE = {
    1: "Arterial",
    2: "Sub-Arterial",
    3: "Collector",
    4: "Local",
    5: "Unknown",
}


def _parse_rings(rings: list) -> list:
    """
    Converts ArcGIS polygon rings into a list of rings,
    each ring a list of [easting, northing] pairs.
    Same shape as Lot.geometry.
    """
    if not rings:
        return []
    return [[[coord[0], coord[1]] for coord in ring] for ring in rings]


def _parse_paths(paths: list) -> list:
    """
    Converts ArcGIS polyline paths into a list of paths,
    each path a list of [easting, northing] pairs.
    """
    if not paths:
        return []
    return [[[coord[0], coord[1]] for coord in path] for path in paths]


def get_road_info(x: float, y: float, epsg: int, distance: int = 200) -> list[Road] | None:
    """
    Spatial query — returns all road corridor polygons within distance metres
    of the given point. Source: FeatureServer/5 (road corridor layer).

    roadnamelabel is the human-readable road name e.g. "George Street".
    roadtype and roadcorridortype are coded values — see dicts above.
    Returns list[Road] or None if nothing found.
    """
    all_features = []
    offset = 0

    while True:
        params = {
            "geometry":          f'{{"x": {x}, "y": {y}, "spatialReference": {{"wkid": {epsg}}}}}',
            "geometryType":      "esriGeometryPoint",
            "spatialRel":        "esriSpatialRelIntersects",
            "distance":          distance,
            "units":             "esriSRUnit_Meter",
            "inSR":              str(epsg),
            "outSR":             str(epsg),
            "outFields":         "*",
            "returnGeometry":    True,
            "resultOffset":      offset,
            "resultRecordCount": 100,
            "f":                 "json",
        }

        response = requests.get(ROAD_URL, params=params)
        data     = response.json()
        features = data.get("features", [])
        all_features.extend(features)

        if not data.get("exceededTransferLimit", False):
            break

        offset += len(features)

    if not all_features:
        return None

    results = []
    for feature in all_features:
        attrs   = feature["attributes"]
        rings   = feature.get("geometry", {}).get("rings", [])
        rt_raw  = attrs.get("roadtype")
        rct_raw = attrs.get("roadcorridortype")

        results.append(Road(
            cadid               = attrs.get("cadid"),
            road_name_oid       = attrs.get("roadnameoid"),
            road_name_label     = attrs.get("roadnamelabel") or "",
            road_type           = rt_raw,
            road_type_label     = ROAD_TYPE.get(rt_raw),
            road_corridor_type  = rct_raw,
            road_corridor_label = ROAD_CORRIDOR_TYPE.get(rct_raw),
            urbanity            = attrs.get("urbanity"),
            classsubtype        = attrs.get("classsubtype"),
            geometry            = _parse_rings(rings),
        ))

    return results


def get_road_centreline_info(x: float, y: float, epsg: int, distance: int = 200) -> list[RoadCentreline] | None:
    """
    Spatial query — returns all road centrelines within distance metres
    of the given point. Source: FeatureServer/1 (RoadCentreline layer).
    Returns list[RoadCentreline] or None if nothing found.
    """
    all_features = []
    offset = 0

    while True:
        params = {
            "geometry":          f'{{"x": {x}, "y": {y}, "spatialReference": {{"wkid": {epsg}}}}}',
            "geometryType":      "esriGeometryPoint",
            "spatialRel":        "esriSpatialRelIntersects",
            "distance":          distance,
            "units":             "esriSRUnit_Meter",
            "inSR":              str(epsg),
            "outSR":             str(epsg),
            "outFields":         "*",
            "returnGeometry":    True,
            "resultOffset":      offset,
            "resultRecordCount": 100,
            "f":                 "json",
        }

        response = requests.get(CENTRELINE_URL, params=params)
        data     = response.json()
        features = data.get("features", [])
        all_features.extend(features)

        if not data.get("exceededTransferLimit", False):
            break

        offset += len(features)

    if not all_features:
        return None

    results = []
    for feature in all_features:
        attrs = feature["attributes"]
        paths = feature.get("geometry", {}).get("paths", [])

        results.append(RoadCentreline(
            cadid           = attrs.get("cadid"),
            road_name_oid   = attrs.get("roadnameoid"),
            road_name_label = attrs.get("roadnamelabel") or "",
            urbanity        = attrs.get("urbanity"),
            geometry        = _parse_paths(paths),
        ))

    return results