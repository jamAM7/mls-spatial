import requests
from config import BASE
from models import Address

ADDR_URL = "https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Geocoded_Addressing_Theme_multiCRS/MapServer/1/query"

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


def get_address_coordinates(address_string: str) -> Address | None:
    # Call 1 — MGA2020 Zone 56 for easting/northing
    feature_mga = _query_address(address_string, "7856")
    if not feature_mga:
        return None

    # Call 2 — WGS84 for longitude/latitude
    feature_geo = _query_address(address_string, "4326")

    attrs    = feature_mga["attributes"]
    geom_mga = feature_mga["geometry"]
    geom_geo = feature_geo["geometry"] if feature_geo else None

    return Address(
        input_string    = address_string,
        resolved_string = attrs.get("address") or address_string,
        easting         = geom_mga["x"],
        northing        = geom_mga["y"],
        longitude       = geom_geo["x"] if geom_geo else None,
        latitude        = geom_geo["y"] if geom_geo else None,
    )




# THIS IS THE OLD ONE WHICH PRINTS AND DOESNT RETURN ADDRESS OBJECT

# import requests
# from config import BASE
# # from models_james import Address
# from models import Address



# def get_address_coordinates(address_string):
#     url = f"{BASE}/NSW_Geocoded_Addressing_Theme/FeatureServer/1/query" # this is url for address stuff
    
#     params = {
#         "where": f"address = '{address_string.upper()}'", # I have chosen to use = instead of LIKE "address%" because I want an exact match, so no risk of returning wrong address. This assumes the survyeor knows the exact address they are looking for.
#         "outFields": "*",       # return all columns
#         "returnGeometry": True, # include x, y coordinates
#         "outSR": "7856",
#         "f": "json"
#     }
    
#     response = requests.get(url, params=params)
#     data = response.json()
    
#     features = data.get("features", [])
#     if not features:
#         print("No address found")
#         return None
    
#     # Take the first match
#     feature = features[0]
#     attrs = feature["attributes"]
#     geom  = feature["geometry"]
    
#     geotype = data.get("geometryType", [])
#     #geott = geotype[0]


#     return {
#         "x": geom["x"],
#         "y": geom["y"],
#     }
    



def get_address_info(address_string):
    url = f"{BASE}/NSW_Geocoded_Addressing_Theme/FeatureServer/1/query" # this is url for address stuff
    
    params = {
        "where": f"address = '{address_string.upper()}'", # I have chosen to use = instead of LIKE "address%" because I want an exact match, so no risk of returning wrong address. This assumes the survyeor knows the exact address they are looking for.
        "outFields": "*",       # return all columns
        "returnGeometry": True, # include x, y coordinates
        "outSR": "7856",
        "f": "json"
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    features = data.get("features", [])
    if not features:
        print("No address found")
        return None
    
    # Take the first match
    feature = features[0]
    attrs = feature["attributes"]
    geom  = feature["geometry"]
    
    geotype = data.get("geometryType", [])
    #geott = geotype[0]


    return {
        "address":    attrs.get("address"),
        "centroidid": attrs.get("centroidid"), # i thought this might be the centre point, but seems to be something else, returns none
        #"lotidstring": attrs.get("lotidstring"),  # e.g. "1//DP123456"
        "x": geom["x"],
        "y": geom["y"],
        "geometryType": geotype
    }



