import requests
from config import BASE
from models import Lot

LOT_URL = f"{BASE}/NSW_Land_Parcel_Property_Theme_multiCRS/FeatureServer/8/query"

# Coded value lookups for Lot layer
ITS_TITLE_STATUS = {
    0: "Undefined",
    1: "Torrens Title",
    2: "Old System",
    3: "Qualified",
    4: "Partial",
    5: "Limited",
    6: "Fee Simple Crown Grant",
    7: "Road",
    8: "Not Applicable",
    9: "Crown Land",
}

STRATUM_LEVEL = {
    -10: "Level -10", -9: "Level -9", -8: "Level -8", -7: "Level -7",
    -6: "Level -6",  -5: "Level -5", -4: "Level -4", -3: "Level -3",
    -2: "Level -2",  -1: "Level -1",  0: "Surface",    1: "Level 1",
     2: "Level 2",   3: "Level 3",   4: "Level 4",    5: "Level 5",
}

HAS_STRATUM = {
    0: "Undefined",
    1: "False",
    2: "True",
}


def _parse_geometry(rings: list) -> list:
    """
    Converts ArcGIS polygon rings into a flat list of [easting, northing] pairs.
    Takes the first ring only (outer boundary).
    """
    if not rings:
        return []
    return [[coord[0], coord[1]] for coord in rings[0]]


def get_lot_info(x: float, y: float, distance: int = 200) -> list[Lot] | None:
    """
    Spatial query — returns all lots within distance metres of the given point.
    Returns list[Lot] or None if nothing found.
    """
    params = {
        "geometry":       f'{{"x": {x}, "y": {y}, "spatialReference": {{"wkid": 7856}}}}',
        "geometryType":   "esriGeometryPoint",
        "spatialRel":     "esriSpatialRelIntersects",
        "distance":       distance,
        "units":          "esriSRUnit_Meter",
        "inSR":           "7856",
        "outSR":          "7856",
        "outFields":      "*",
        "returnGeometry": True,
        "f":              "json"
    }


    response = requests.get(LOT_URL, params=params)
    data = response.json()

    features = data.get("features", [])
    if not features:
        return None

    results = []

    for feature in features:
        attrs = feature["attributes"]
        rings = feature.get("geometry", {}).get("rings", [])

        its_title_status_raw = attrs.get("itstitlestatus")
        stratum_level_raw    = attrs.get("stratumlevel")
        has_stratum_raw      = attrs.get("hasstratum")

        results.append(Lot(
            lot_number                  = attrs.get("lotnumber") or "",
            plan_label                  = attrs.get("planlabel") or "",
            section_number              = attrs.get("sectionnumber") or "",
            plan_number                 = attrs.get("plannumber"),
            plan_oid                    = attrs.get("planoid"),
            its_lot_id                  = attrs.get("itslotid"),
            cad_id                      = attrs.get("cadid"),
            controlling_authority_oid   = attrs.get("controllingauthorityoid"),
            classsubtype                = attrs.get("classsubtype"),
            its_title_status            = its_title_status_raw,
            its_title_status_label      = ITS_TITLE_STATUS.get(its_title_status_raw),
            stratum_level               = stratum_level_raw,
            stratum_level_label         = STRATUM_LEVEL.get(stratum_level_raw),
            has_stratum                 = bool(has_stratum_raw) if has_stratum_raw is not None else None,
            plan_lot_area               = attrs.get("planlotarea"),
            plan_lot_area_units         = attrs.get("planlotareaunits"),
            create_date                 = attrs.get("createdate"),
            modified_date               = attrs.get("modifieddate"),
            geometry                    = _parse_geometry(rings),
        ))

    # Note: is_subject is intentionally not set here — it defaults to False.
    # search.py is responsible for identifying the subject lot and setting is_subject=True.
    return results




# import requests
# from config import BASE
# from api.address import get_address_coordinates
# from utils import expand_address


# def get_lps():
#     address = expand_address(input('Enter an address: '))
#     distance = input('Enter a radius distance (metres): ')

#     result = get_address_coordinates(address)
#     if not result:
#         print('Address not found')
#         return
    
#     x, y = result["x"], result["y"]

#     lots = get_lot_info(x, y, distance)

#     if lots is None:
#         print('No lots found, try a further radius and check address')
#     else:
#         for lot in lots:
#             print(str(lot) + "\n")


# def get_lot_info(x, y, distance):
#     url = f"{BASE}/NSW_Land_Parcel_Property_Theme_multiCRS/FeatureServer/8/query"
    
#     params = {
#         "geometry":       f'{{"x": {x}, "y": {y}, "spatialReference": {{"wkid": 7856}}}}',
#         "geometryType":   "esriGeometryPoint",      # it says it will always be esriGeometryPoint on the website
#         "spatialRel":     "esriSpatialRelIntersects",
#         "inSR":           "7856",    
#         "outSR":          "7856",
#         "distance":       distance,
#         "units":          "esriSRUnit_Meter",
#         "outFields":      "*",
#         "returnGeometry": True,
#         "f":              "json"
#     }
    
#     response = requests.get(url, params=params)
#     data = response.json()


#     # # Test
#     # response = requests.get(url, params=params)
#     # print(response.url)
#     # print(response.json())
    



#     features = data.get("features", [])
#     if not features:
#         print("No lot found")
#         return None
    
#     print(f"Total lots returned: {len(data.get('features', []))}")

#     results = []

#     for feature in features:
#         attrs = feature["attributes"]
#         results.append({
#             "lotidstring":  attrs.get("lotidstring"),
#             "lotnumber":    attrs.get("lotnumber"),
#             "plannumber":   attrs.get("plannumber"),
#             "sectionnumber": attrs.get("sectionnumber"),
#             "startdate":     attrs.get("startdate"),
#             "enddate":       attrs.get("enddate"),
#             "centroidid":   attrs.get("centroidid"), # i thought this might be the centre point, but seems to be something else, returns none on
#             #"planlotarea":  attrs.get("planlotarea"), # dont think we'll need this
#             "geometry":     feature["geometry"]  # we'll need this for the survey mark query
#         })

#     return results
