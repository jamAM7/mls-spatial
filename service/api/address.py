import requests
from service.config import BASE
from service.models import Address
from concurrent.futures import ThreadPoolExecutor, as_completed

ADDR_URL = "https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Geocoded_Addressing_Theme_multiCRS/MapServer/1/query"
ADMIN_BASE = "https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Administrative_Boundaries_Theme/FeatureServer"

def _query_address(address_string: str, out_sr: str) -> dict | None:
    """Private helper — queries address API with given output spatial reference"""
    params = {
        "where":          f"address = '{address_string.upper()}'",
        "outFields":      "address",
        "returnGeometry": True,
        "outSR":          out_sr,
        "f":              "json"
    }

    response = requests.get(ADDR_URL, params=params)
    data = response.json()

    features = data.get("features", [])
    if not features:
        return None

    return features[0]


ADMIN_LAYERS = {
    "suburb": (2,  "suburbname"),
    "lga":    (8,  "lganame"),
    "parish": (5,  "parishname"),
    "county": (11, "countyname"),
}

def _get_admin_boundaries(easting: float, northing: float) -> dict:
    result = {"suburb": None, "lga": None, "parish": None, "county": None}

    def fetch(key, layer_id, field_name):
        url = f"{ADMIN_BASE}/{layer_id}/query"
        params = {
            "geometry":       f"{easting},{northing}",
            "geometryType":   "esriGeometryPoint",
            "inSR":           "7856",
            "spatialRel":     "esriSpatialRelIntersects",
            "outFields":      field_name,
            "returnGeometry": False,
            "f":              "json"
        }
        response = requests.get(url, params=params)
        data = response.json()
        features = data.get("features", [])
        if features:
            return key, features[0]["attributes"].get(field_name)
        return key, None

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(fetch, key, layer_id, field_name)
            for key, (layer_id, field_name) in ADMIN_LAYERS.items()
        ]
        for future in as_completed(futures):
            key, value = future.result()
            result[key] = value

    return result


def get_address_coordinates(address_string: str) -> Address | None:
    feature_mga = _query_address(address_string, "7856")
    if not feature_mga:
        return None

    feature_geo = _query_address(address_string, "4326")

    attrs    = feature_mga["attributes"]
    geom_mga = feature_mga["geometry"]
    geom_geo = feature_geo["geometry"] if feature_geo else None

    # Get admin boundaries
    admin = _get_admin_boundaries(geom_mga["x"], geom_mga["y"])

    return Address(
        input_string    = address_string,
        resolved_string = attrs.get("address") or address_string,
        easting         = geom_mga["x"],
        northing        = geom_mga["y"],
        longitude       = geom_geo["x"] if geom_geo else None,
        latitude        = geom_geo["y"] if geom_geo else None,
        suburb          = admin["suburb"],
        lga             = admin["lga"],
        parish          = admin["parish"],
        county          = admin["county"],
    )




