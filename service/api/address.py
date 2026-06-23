import requests
from service.config import BASE
from service.models import Address
from service.utils import to_web_mercator
from concurrent.futures import ThreadPoolExecutor, as_completed

ADDR_URL = "https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Geocoded_Addressing_Theme_multiCRS/MapServer/1/query"
ADMIN_BASE = "https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Administrative_Boundaries_Theme/FeatureServer"
ELEV_URL = "https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_5M_Elevation/ImageServer/identify"


# def _query_address(address_string: str, out_sr: str) -> dict | None:
#     """Private helper — queries address API with given output spatial reference"""
#     params = {
#         "where":          f"address = '{address_string.upper()}'",
#         "outFields":      "address",
#         "returnGeometry": True,
#         "outSR":          out_sr,
#         "f":              "json"
#     }

#     response = requests.get(ADDR_URL, params=params)
#     data = response.json()

#     features = data.get("features", [])
#     if not features:
#         return None

#     return features[0]


# ADMIN_LAYERS = {
#     "suburb": (2,  "suburbname"),
#     "lga":    (8,  "lganame"),
#     "parish": (5,  "parishname"),
#     "county": (11, "countyname"),
# }
def _query_address(address_string: str, out_sr: str) -> dict | None:
    def _query(where: str) -> dict | None:
        params = {
            "where":          where,
            "outFields":      "address",
            "returnGeometry": True,
            "outSR":          out_sr,
            "f":              "json",
        }
        response = requests.get(ADDR_URL, params=params)
        features = response.json().get("features", [])
        return features[0] if features else None

    # Try exact match first — fastest and most precise
    result = _query(f"address = '{address_string.upper()}'")
    if result:
        return result

    # Fall back to starts-with LIKE — handles suburb name variations
    # e.g. "1 SMITH STREET BONDI" matches "1 SMITH STREET BONDI BEACH"
    return _query(f"address LIKE '{address_string.upper()}%'")


ADMIN_LAYERS = {
    "suburb": (2,  "suburbname"),
    "lga":    (8,  "lganame"),
    "parish": (5,  "parishname"),
    "county": (11, "countyname"),
}


def _fetch_surface_level(longitude: float, latitude: float) -> float | None:
    """Fetch AHD surface level from NSW 5M Elevation DEM at a WGS84 point."""
    x, y = to_web_mercator(longitude, latitude)
    params = {
        "geometry":     f"{x},{y}",
        "geometryType": "esriGeometryPoint",
        "inSR":         "3857",
        "f":            "json",
    }
    try:
        response = requests.get(ELEV_URL, params=params)
        data = response.json()
        value = data.get("value")
        if value is None or value == "NoData":
            return None
        return round(float(value), 3)
    except Exception:
        return None


def _get_admin_boundaries(easting: float, northing: float, inSR: int = 7856) -> dict:
    result = {"suburb": None, "lga": None, "parish": None, "county": None}

    def fetch(key, layer_id, field_name):
        url = f"{ADMIN_BASE}/{layer_id}/query"
        params = {
            "geometry":       f"{easting},{northing}",
            "geometryType":   "esriGeometryPoint",
            "inSR":           str(inSR),
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


def get_address_coordinates(address_string: str, out_sr: int = 7856) -> Address | None:
    feature_mga = _query_address(address_string, str(out_sr))
    if not feature_mga:
        return None

    feature_geo = _query_address(address_string, "4326")

    attrs    = feature_mga["attributes"]
    geom_mga = feature_mga["geometry"]
    geom_geo = feature_geo["geometry"] if feature_geo else None

    longitude = geom_geo["x"] if geom_geo else None
    latitude  = geom_geo["y"] if geom_geo else None

    # Run admin boundaries and elevation concurrently
    with ThreadPoolExecutor(max_workers=2) as executor:
        admin_future = executor.submit(
            _get_admin_boundaries, geom_mga["x"], geom_mga["y"], inSR=out_sr
        )
        elev_future = executor.submit(
            _fetch_surface_level, longitude, latitude
        ) if longitude and latitude else None

        admin = admin_future.result()
        surface_level_ahd = elev_future.result() if elev_future else None

    return Address(
        input_string      = address_string,
        resolved_string   = attrs.get("address") or address_string,
        easting           = geom_mga["x"],
        northing          = geom_mga["y"],
        longitude         = longitude,
        latitude          = latitude,
        suburb            = admin["suburb"],
        lga               = admin["lga"],
        parish            = admin["parish"],
        county            = admin["county"],
        surface_level_ahd = surface_level_ahd,
    )


# def get_address_suggestions(address_string: str, limit: int = 10) -> list[str] | None:
#     """
#     Returns a list of matching addresses from NSW API using LIKE query.
    
#     Used for address suggestion/autocomplete — user types partial address,
#     this returns candidates for the user to pick from.
    
#     Example: "14 Dellview Street Tamarama" might return:
#     - "14-16 DELLVIEW STREET TAMARAMA"
#     - "14 DELLVIEW STREET TAMARAMA"
#     """
#     from service.utils import sanitise_address
    
#     normalised = sanitise_address(address_string)
    
#     params = {
#         "where":          f"address LIKE '%{normalised}%'",
#         "outFields":      "address",
#         "returnGeometry": False,
#         "resultRecordCount": limit,
#         "f":              "json"
#     }
    
#     try:
#         response = requests.get(ADDR_URL, params=params)
#         data = response.json()
#         features = data.get("features", [])
        
#         if not features:
#             return None
        
#         # Extract unique addresses
#         addresses = list(set(f["attributes"]["address"] for f in features))
#         return sorted(addresses)
    
#     except Exception as e:
#         print(f"[address] Error querying suggestions for '{address_string}': {e}")
#         return None
def get_address_suggestions(address_string: str, limit: int = 10) -> list[str] | None:
    from service.utils import sanitise_address

    normalised = sanitise_address(address_string)

    # AND together a LIKE condition per token so "14 DELLVIEW TAMARAMA" matches
    # "14-16 DELLVIEW STREET TAMARAMA" — single full-string LIKE would miss it
    tokens = [t for t in normalised.split() if len(t) > 1]
    if not tokens:
        return None

    where = " AND ".join(f"address LIKE '%{token}%'" for token in tokens)

    params = {
        "where":             where,
        "outFields":         "address",
        "returnGeometry":    False,
        "resultRecordCount": limit,
        "f":                 "json",
    }

    try:
        response = requests.get(ADDR_URL, params=params)
        data = response.json()
        features = data.get("features", [])
        if not features:
            return None
        addresses = list({f["attributes"]["address"] for f in features})
        return sorted(addresses)
    except Exception as e:
        print(f"[address] Error querying suggestions for '{address_string}': {e}")
        return None