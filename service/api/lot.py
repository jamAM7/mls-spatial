import requests
from service.config import BASE
from service.models import Lot

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


def get_lot_info(x: float, y: float, epsg: int, distance: int = 200) -> list[Lot] | None:
    all_features = []
    offset = 0

    while True:
        params = {
            "geometry":       f'{{"x": {x}, "y": {y}, "spatialReference": {{"wkid": {epsg}}}}}',
            "geometryType":   "esriGeometryPoint",
            "spatialRel":     "esriSpatialRelIntersects",
            "distance":       distance,
            "units":          "esriSRUnit_Meter",
            "inSR":           str(epsg),
            "outSR":          str(epsg),
            "outFields":      "*",
            "returnGeometry": True,
            "resultOffset":   offset,        # ← pagination start
            "resultRecordCount": 100,        # ← page size
            "f":              "json"
        }

        response = requests.get(LOT_URL, params=params)
        data = response.json()

        features = data.get("features", [])
        all_features.extend(features)

        if not data.get("exceededTransferLimit", False):
            break  # got all results

        offset += len(features)  # move to next page

    if not all_features:
        return None

    results = []
    for feature in all_features:
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
            # has_stratum                 = bool(has_stratum_raw) if has_stratum_raw is not None else None,
            has_stratum = (HAS_STRATUM.get(has_stratum_raw) == "True") if has_stratum_raw is not None else None,
            plan_lot_area               = attrs.get("planlotarea"),
            plan_lot_area_units         = attrs.get("planlotareaunits"),
            create_date                 = attrs.get("createdate"),
            modified_date               = attrs.get("modifieddate"),
            geometry                    = _parse_geometry(rings),
        ))

    # Note: is_subject is intentionally not set here — it defaults to False.
    # search.py is responsible for identifying the subject lot and setting is_subject=True.
    return results


