import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from service.config import BASE
from service.models import SurveyMark
from service.utils import to_web_mercator
from datetime import datetime

SM_URL      = f"{BASE}/SurveyMarkGDA2020_multiCRS/FeatureServer/0/query"
SM_ATTR_URL = "https://portal.spatial.nsw.gov.au/server/rest/services/SurveyMarkGDA2020/MapServer/0/query"
ELEV_URL    = "https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_5M_Elevation/ImageServer/identify"


def _epoch_ms_to_date(ms):
    if not ms:
        return None
    try:
        return datetime.fromtimestamp(ms / 1000).date()
    except (OSError, OverflowError, ValueError):
        return None


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


def _mark_from_feature(feature: dict) -> SurveyMark:
    attrs = feature["attributes"]
    geom  = feature.get("geometry") or {}
    return SurveyMark(
        # Identity
        mark_number               = attrs.get("marknumber"),
        mark_type                 = attrs.get("marktype") or "",
        mark_status               = attrs.get("markstatus") or "",
        mark_symbol               = attrs.get("marksymbol"),
        mark_symbol_label         = attrs.get("marksymbol_label"),
        mark_alias                = attrs.get("markalias"),
        monument_type             = attrs.get("monumenttype"),
        monument_location         = attrs.get("monumentlocation"),
        classsubtype              = attrs.get("classsubtype"),
        msoid                     = attrs.get("msoid"),
        is_gp_parent              = attrs.get("isgparent"),

        # Trig
        trig_name                 = attrs.get("trigname"),
        trig_type                 = attrs.get("trigtype"),

        # GDA2020 horizontal position
        easting                   = geom.get("x"),
        northing                  = geom.get("y"),
        longitude                 = attrs.get("longitude"),
        latitude                  = attrs.get("latitude"),
        mga_zone                  = attrs.get("mgazone"),
        mga_convergence           = attrs.get("mgacon"),
        mga_csf_2020              = attrs.get("mgacsf2020"),
        mga_csf_2020_label        = attrs.get("mgacsf2020_label"),
        mga_easting_label         = attrs.get("mgaeasting_label"),
        mga_northing_label        = attrs.get("mganorthing_label"),

        # GDA2020 horizontal quality
        gda_class                 = attrs.get("gdaclass"),
        gda_date                  = _epoch_ms_to_date(attrs.get("gdadate")),
        gda_source                = attrs.get("gdasource"),
        gda_source_type           = attrs.get("gdasourcetype"),
        gda_source_method         = attrs.get("gdasourcemethod"),
        gda_pos_uncertainty_label = attrs.get("gdaposuncertainty_label"),
        gda_loc_uncertainty_label = attrs.get("gdalocuncertainty_label"),

        # AHD height
        ahd_height                = float(attrs.get("ahdheight_label")) if attrs.get("ahdheight_label") else None,
        ahd_height_label          = attrs.get("ahdheight_label"),
        ahd_class                 = attrs.get("ahdclass"),
        ahd_date                  = _epoch_ms_to_date(attrs.get("ahddate")),
        ahd_source                = attrs.get("ahdsource"),
        ahd_source_type           = attrs.get("ahdsourcetype"),
        ahd_source_method         = attrs.get("ahdsourcemethod"),
        ahd_pos_uncertainty_label = attrs.get("ahdposuncertainty_label"),
        ahd_loc_uncertainty_label = attrs.get("ahdlocuncertainty_label"),

        # AUSGeoid2020
        ausgeoid2020              = attrs.get("ausgeoid2020"),
        ausgeoid2020_label        = attrs.get("ausgeoid2020_label"),

        # GDA2020 ellipsoidal height
        gda_height                = attrs.get("gdaheight"),
        gda_height_label          = attrs.get("gdaheight_label"),
        gda_height_date           = _epoch_ms_to_date(attrs.get("gdaheightdate")),
        gda_height_class          = attrs.get("gdaheightclass"),
        gda_height_order          = attrs.get("gdaheightorder"),
        gda_height_pos_uncertainty = attrs.get("gdaheightposuncertainty"),
        gda_height_loc_uncertainty = attrs.get("gdaheightlocuncertainty"),
        gda_height_source         = attrs.get("gdaheightsource"),
        gda_height_source_type    = attrs.get("gdaheightsourcetype"),
        gda_height_source_method  = attrs.get("gdaheightsourcemethod"),

        # Data currency
        retrieved_at              = datetime.now(),
    )


def get_survey_mark_info(x: float, y: float, epsg: int, distance: int = 200) -> list[SurveyMark] | None:
    """
    Spatial query — returns all survey marks within distance metres of the given point.
    Fetches surface level AHD from [ELEV] for each mark in parallel.
    Returns list[SurveyMark] or None if nothing found.
    """
    params = {
        "geometry":       f'{{"x": {x}, "y": {y}, "spatialReference": {{"wkid": {epsg}}}}}',
        "geometryType":   "esriGeometryPoint",
        "spatialRel":     "esriSpatialRelIntersects",
        "distance":       distance,
        "units":          "esriSRUnit_Meter",
        "inSR":           str(epsg),
        "outSR":          str(epsg),
        "outFields":      "*",
        "returnGeometry": "true",
        "f":              "json",
    }

    response = requests.get(SM_URL, params=params)
    features = response.json().get("features", [])
    if not features:
        return None

    marks = [_mark_from_feature(f) for f in features]

    # Fetch surface level for each mark in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(_fetch_surface_level, m.longitude, m.latitude): m
            for m in marks
            if m.longitude is not None and m.latitude is not None
        }
        for future, mark in futures.items():
            mark.surface_level_ahd = future.result()

    return marks


def get_mark_by_reference(mark_type: str, mark_number: str) -> SurveyMark | None:
    """
    Attribute query — fetches a single mark by type and number from [MARK_ATTR].
    Also fetches surface level AHD for the returned mark.
    """
    params = {
        "where":          f"marknumber={mark_number} AND marktype='{mark_type}'",
        "outFields":      "*",
        "returnGeometry": "true",
        "outSR":          "7856",
        "f":              "json",
    }

    response = requests.get(SM_ATTR_URL, params=params)
    features = response.json().get("features", [])
    if not features:
        return None

    mark = _mark_from_feature(features[0])

    if mark.longitude is not None and mark.latitude is not None:
        mark.surface_level_ahd = _fetch_surface_level(mark.longitude, mark.latitude)

    return mark


def download_sketch(mark: SurveyMark, dest_folder: Path) -> Path | None:
    """
    Downloads the sketch PDF for a survey mark from the SIX Maps SketchPlans API.
    
    API: http://maps.six.nsw.gov.au/SketchPlansWS/rest/getSketchPlans
    Parameter: surveyMark={mark_type}{mark_number} (e.g., surveyMark=PM31035)
    
    Returns the path to the downloaded PDF, or None if not found.
    """
    if not mark.mark_type or not mark.mark_number:
        return None
    
    mark_ref = f"{mark.mark_type}{mark.mark_number}"
    
    try:
        api_url = "http://maps.six.nsw.gov.au/SketchPlansWS/rest/getSketchPlans"
        params = {"surveyMark": mark_ref}
        
        response = requests.get(api_url, params=params, timeout=10)
        
        if response.status_code == 200 and "pdf" in response.headers.get("content-type", "").lower():
            out_path = dest_folder / f"{mark_ref}_sketch.pdf"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(response.content)
            return out_path
        
        return None
    
    except Exception:
        return None