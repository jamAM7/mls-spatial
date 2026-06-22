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


# def _parse_geometry(rings: list) -> list:
#     """
#     Converts ArcGIS polygon rings into a flat list of [easting, northing] pairs.
#     Takes the first ring only (outer boundary).
#     """
#     if not rings:
#         return []
#     return [[coord[0], coord[1]] for coord in rings[0]]


def _parse_geometry(rings: list) -> list:
    """
    Converts ArcGIS polygon rings into a list of rings,
    each ring being a list of [easting, northing] pairs.
    Part lots have multiple rings — all are kept.
    """
    if not rings:
        return []
    return [[[coord[0], coord[1]] for coord in ring] for ring in rings]


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
        # Test Debug
        if all_features and offset == 0:
            print("DEBUG lot attrs:", all_features[0]["attributes"])

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


def get_lot_by_folio(folio: str) -> Lot | None:
    """
    Query a lot by folio reference (lot/section/plan).
    
    Example: "102/1/DP574558" -> lot_number=102, section_number=1, plan_label=DP574558
    
    Returns the first matching Lot, or None if not found.
    """
    import re
    
    # Parse folio: "102/1/DP574558" or "102/DP574558"
    match = re.match(r'^(\d+)/(\d+|[A-Z]{2}\d+)(?:/([A-Z]{2}\d+))?$', folio.strip().upper())
    if not match:
        return None
    
    lot_number = match.group(1)
    middle = match.group(2)
    plan_label = match.group(3)
    
    # Determine if middle is section_number or plan_label
    if plan_label:
        # Format: lot/section/plan
        section_number = middle
    else:
        # Format: lot/plan (no section)
        section_number = None
        plan_label = middle
    
    try:
        # Query by lot number, section, and plan label attributes
        where_clauses = [
            f"lotnumber = '{lot_number}'",
            f"planlabel = '{plan_label}'",
        ]
        if section_number:
            where_clauses.append(f"sectionnumber = '{section_number}'")
        
        where = " AND ".join(where_clauses)
        
        params = {
            "where":          where,
            "outFields":      "*",
            "returnGeometry": "true",
            "inSR":           "7856",  # MGA Zone 56
            "outSR":          "7856",
            "f":              "json",
        }
        
        response = requests.get(LOT_URL, params=params)
        data = response.json()
        
        features = data.get("features", [])
        if not features:
            return None
        
        # Return the first matching lot
        feature = features[0]
        attrs = feature["attributes"]
        rings = feature.get("geometry", {}).get("rings", [])
        
        its_title_status_raw = attrs.get("itstitlestatus")
        stratum_level_raw    = attrs.get("stratumlevel")
        has_stratum_raw      = attrs.get("hasstratum")
        
        return Lot(
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
            has_stratum = (HAS_STRATUM.get(has_stratum_raw) == "True") if has_stratum_raw is not None else None,
            plan_lot_area               = attrs.get("planlotarea"),
            plan_lot_area_units         = attrs.get("planlotareaunits"),
            create_date                 = attrs.get("createdate"),
            modified_date               = attrs.get("modifieddate"),
            geometry                    = _parse_geometry(rings),
        )
    
    except Exception as e:
        print(f"[folio] Error querying lot {folio}: {e}")
        return None