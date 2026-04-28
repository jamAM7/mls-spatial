import requests
from config import BASE
from models import SurveyMark
from datetime import datetime

SM_URL = f"{BASE}/SurveyMarkGDA2020_multiCRS/FeatureServer/0/query"


def get_survey_mark_info(x: float, y: float, distance: int = 200) -> list[SurveyMark] | None:
    """
    Spatial query — returns all survey marks within distance metres of the given point.
    Returns list[SurveyMark] or None if nothing found.
    """

    params = {
        "geometry":     f'{{"x": {x}, "y": {y}, "spatialReference": {{"wkid": 7856}}}}',
        "geometryType": "esriGeometryPoint",
        "spatialRel":   "esriSpatialRelIntersects",
        "distance":     distance,
        "units":        "esriSRUnit_Meter",
        "inSR":         "7856",
        "outSR":        "7856",
        "outFields":    "*",
        "returnGeometry": "true",
        "f":            "json"
    }


    response = requests.get(SM_URL, params=params)
    data = response.json()

    features = data.get("features", [])
    if not features:
        return None

    results = []


    for feature in features:
        attrs = feature["attributes"]
        

        results.append(SurveyMark(
            # Identity
            mark_number             = attrs.get("marknumber"),
            mark_type               = attrs.get("marktype") or "",
            mark_status             = attrs.get("markstatus") or "",
            mark_symbol             = attrs.get("marksymbol"),
            mark_symbol_label       = attrs.get("marksymbol_label"),
            mark_alias              = attrs.get("markalias"),
            monument_type           = attrs.get("monumenttype"),
            monument_location       = attrs.get("monumentlocation"),
            classsubtype            = attrs.get("classsubtype"),
            msoid                   = attrs.get("msoid"),
            is_gp_parent            = attrs.get("isgparent"),

            # Trig
            trig_name               = attrs.get("trigname"),
            trig_type               = attrs.get("trigtype"),

            # GDA2020 horizontal position
            easting                 = feature["geometry"]["x"],
            northing                = feature["geometry"]["y"],
            longitude               = attrs.get("longitude"),
            latitude                = attrs.get("latitude"),
            mga_zone                = attrs.get("mgazone"),
            mga_convergence         = attrs.get("mgacon"),
            mga_csf_2020            = attrs.get("mgacsf2020"),
            mga_csf_2020_label      = attrs.get("mgacsf2020_label"),
            mga_easting_label       = attrs.get("mgaeasting_label"),
            mga_northing_label      = attrs.get("mganorthing_label"),

            # GDA2020 horizontal quality
            gda_class               = attrs.get("gdaclass"),
            gda_date                = attrs.get("gdadate"),
            gda_source              = attrs.get("gdasource"),
            gda_source_type         = attrs.get("gdasourcetype"),
            gda_source_method       = attrs.get("gdasourcemethod"),
            gda_pos_uncertainty_label = attrs.get("gdaposuncertainty_label"),
            gda_loc_uncertainty_label = attrs.get("gdalocuncertainty_label"),

            # AHD height
            ahd_height              = attrs.get("ahdheight_label"),
            ahd_height_label        = attrs.get("ahdheight_label"),
            ahd_class               = attrs.get("ahdclass"),
            ahd_date                = attrs.get("ahddate"),
            ahd_source              = attrs.get("ahdsource"),
            ahd_source_type         = attrs.get("ahdsourcetype"),
            ahd_source_method       = attrs.get("ahdsourcemethod"),
            ahd_pos_uncertainty_label = attrs.get("ahdposuncertainty_label"),
            ahd_loc_uncertainty_label = attrs.get("ahdlocuncertainty_label"),

            # AUSGeoid2020
            ausgeoid2020            = attrs.get("ausgeoid2020"),
            ausgeoid2020_label      = attrs.get("ausgeoid2020_label"),

            # GDA2020 ellipsoidal height
            gda_height              = attrs.get("gdaheight"),
            gda_height_label        = attrs.get("gdaheight_label"),
            gda_height_date         = attrs.get("gdaheightdate"),
            gda_height_class        = attrs.get("gdaheightclass"),
            gda_height_order        = attrs.get("gdaheightorder"),
            gda_height_pos_uncertainty = attrs.get("gdaheightposuncertainty"),
            gda_height_loc_uncertainty = attrs.get("gdaheightlocuncertainty"),
            gda_height_source       = attrs.get("gdaheightsource"),
            gda_height_source_type  = attrs.get("gdaheightsourcetype"),
            gda_height_source_method = attrs.get("gdaheightsourcemethod"),

            # Data currency
            retrieved_at            = datetime.now(),
            # retrieved_at is set at time of API call.
            # Staleness check (> 180 days) will be implemented in search.py when caching is added (Phase 4).
        ))    

    return results












# import requests
# from config import BASE
# from api.address import get_address_coordinates
# from utils import expand_address

# def survey_mark_search():
#     address = expand_address(input('Enter an address: '))
#     distance = input('Enter a radius distance (metres): ')

#     result = get_address_coordinates(address)
#     if not result:
#         print('Address not found')
#         return
    
#     x, y = result["x"], result["y"]
#     marks = get_survey_mark_info(x, y, distance)

#     if marks is None:
#         print('No marks found, try a further radius and check address')
#     else:
#         for mark in marks:
#             print(str(mark) + "\n")


# def get_survey_mark_by_number():
#     url = f"{BASE}/SurveyMarkGDA2020_multiCRS/FeatureServer/0/query"

#     marknumber = input('Enter a mark number: ')

#     params = {
#         "where":          f"marknumber = {marknumber}",
#         "outFields":      "*",
#         "returnGeometry": "true",
#         "outSR":          "7856",
#         "f":              "json"
#     }

#     response = requests.get(url, params=params)
#     data = response.json()

#     features = data.get("features", [])
#     if not features:
#         print('No mark found')
#         return

#     attrs = features[0]["attributes"]
#     feature = features[0]

#     result = {
#         "marknumber":      attrs.get("marknumber"),
#         "marktype":        attrs.get("marktype"),
#         "markstatus":      attrs.get("markstatus"),
#         "marksymbol":      attrs.get("marksymbol"),
#         "easting":         feature["geometry"]["x"],
#         "northing":        feature["geometry"]["y"],
#         "zone":            attrs.get("mgazone"),
#         "gda_class":       attrs.get("gdaclass"),
#         "pos_uncertainty": attrs.get("gdaposuncertainty_label"),
#         "loc_uncertainty": attrs.get("gdalocuncertainty_label"),
#         "source":          attrs.get("gdasource"),
#         "csf":             attrs.get("mgacsf2020"),
#         "convergence":     attrs.get("mgacon"),
#         "ahd_height":      attrs.get("ahdheight_label"),
#         "ahd_class":       attrs.get("ahdclass"),
#         "ausgeoid2020":    attrs.get("ausgeoid2020"),
#     }

#     for key, value in result.items():
#         print(f"{key}: {value}")


# def get_survey_mark_info(x, y, distance):
#     url = f"{BASE}/SurveyMarkGDA2020_multiCRS/FeatureServer/0/query"

#     params = {
#         "geometry":     f'{{"x": {x}, "y": {y}, "spatialReference": {{"wkid": 7856}}}}',
#         "geometryType": "esriGeometryPoint",
#         "spatialRel":   "esriSpatialRelIntersects",
#         "distance":     distance,
#         "units":        "esriSRUnit_Meter",
#         "inSR":         "7856",
#         "outSR":        "7856",
#         "outFields":    "*",
#         "returnGeometry": "true",
#         "f":            "json"
#     }

#     response = requests.get(url, params=params)
#     data = response.json()

#     features = data.get("features", [])
#     if not features:
#         return None

#     results = []

#     for feature in features:
#         attrs = feature["attributes"]
#         results.append({
#             "marknumber":      attrs.get("marknumber"),
#             "marktype":        attrs.get("marktype"),
#             "markstatus":      attrs.get("markstatus"),
#             "marksymbol":      attrs.get("marksymbol"),
#             "easting":         feature["geometry"]["x"],
#             "northing":        feature["geometry"]["y"],
#             "zone":            attrs.get("mgazone"),
#             "gda_class":       attrs.get("gdaclass"),
#             "pos_uncertainty": attrs.get("gdaposuncertainty_label"),
#             "loc_uncertainty": attrs.get("gdalocuncertainty_label"),
#             "source":          attrs.get("gdasource"),
#             "csf":             attrs.get("mgacsf2020"),
#             "convergence":     attrs.get("mgacon"),
#             "ahd_height":      attrs.get("ahdheight_label"),
#             "ahd_class":       attrs.get("ahdclass"),
#             "ausgeoid2020":    attrs.get("ausgeoid2020"),
#         })

#     return results
