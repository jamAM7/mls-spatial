import requests
import re
from datetime import datetime, timedelta, timezone

from config import BASE
from models import Plan


BASE = "https://maps.six.nsw.gov.au/arcgis/rest/services/sixmaps/Boundaries/MapServer"
PLAN_LAYER = 2

PLAN_TOKEN_RE = re.compile(r"^\s*(DP|SP)\s*0*(\d+)\s*([A-Z])?\s*$", re.IGNORECASE)


def _parse_plan_label(plan_label: str):
    """Splits 'DP574558' into ('DP', 574558, '')"""
    m = PLAN_TOKEN_RE.match(plan_label or "")
    if not m:
        raise ValueError(f"Unrecognised plan label: {plan_label!r}")
    return m.group(1).upper(), int(m.group(2)), (m.group(3) or "").upper()


def _ms_to_date(ms):
    """Converts ArcGIS millisecond timestamp to readable date string"""
    if ms is None:
        return None
    try:
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        return (epoch + timedelta(milliseconds=int(ms))).date().isoformat()
    except Exception:
        return str(ms)


def _load_domain_lookups():
    """
    Fetches layer metadata and builds coded value lookup dictionaries.
    These are needed to decode things like issurveyed: 2 -> 'True'
    """
    url = f"{BASE}/{PLAN_LAYER}"
    r = requests.get(url, params={"f": "json"}, timeout=60)
    r.raise_for_status()
    js = r.json()

    field_domains = {}
    subtype_map = {}
    subtype_field_domains = {}

    # Build field-level coded value lookups
    for f in js.get("fields", []):
        dom = f.get("domain")
        if dom and dom.get("type") == "codedValue":
            field_domains[f["name"]] = {
                cv["code"]: cv["name"] for cv in dom.get("codedValues", [])
            }

    # Build subtype lookups (DP vs SP etc)
    for st in js.get("types", []) or []:
        sid = st.get("id")
        if sid is None:
            continue
        subtype_map[sid] = st.get("name")
        for fld, dom in (st.get("domains") or {}).items():
            if dom and dom.get("type") == "codedValue":
                subtype_field_domains[(sid, fld)] = {
                    cv["code"]: cv["name"] for cv in dom.get("codedValues", [])
                }

    return field_domains, subtype_map, subtype_field_domains


def _decode(field, value, classsubtype, field_domains, subtype_field_domains):
    """Converts a coded value to its human readable label"""
    if value is None:
        return None
    if (classsubtype, field) in subtype_field_domains:
        return subtype_field_domains[(classsubtype, field)].get(value, value)
    if field in field_domains:
        return field_domains[field].get(value, value)
    return value

def _to_surveyed_bool(decoded_value):
    """
    Converts issurveyed decoded string to bool or None.
    True = Survey, False = Compilation, None = Unresearched/Undefined
    """
    if decoded_value == "True":
        return True
    elif decoded_value == "False":
        return False
    else:
        return None  # Unresearched, Undefined etc

def get_plan_info(plan_label: str):
    """
        Takes a plan number string like 'DP574558' or 'SP10027'
        and returns metadata about that plan.
    """
    prefix, number, suffix = _parse_plan_label(plan_label)

    field_domains, subtype_map, subtype_field_domains = _load_domain_lookups()

    wanted_subtype = 1 if prefix == "DP" else 2 if prefix == "SP" else None
    subtypes = [wanted_subtype] if wanted_subtype in subtype_map else list(subtype_map.keys())

    attrs = None
    for subtype in subtypes:
        where = f"(classsubtype = {subtype}) AND (plannumber = {number})"
        if suffix:
            where += f" AND (plannumbersuffix = '{suffix}')"
        else:
            where += " AND (plannumbersuffix IS NULL OR plannumbersuffix = '')"

        url = f"{BASE}/{PLAN_LAYER}/query"
        r = requests.get(url, params={
            "where":             where,
            "outFields":         "*",
            "returnGeometry":    "false",
            "resultRecordCount": 1,
            "f":                 "json"
        }, timeout=60)
        r.raise_for_status()
        js = r.json()

        if "error" in js:
            err = js["error"]
            raise RuntimeError(f"ArcGIS error {err.get('code')}: {err.get('message')}")

        feats = js.get("features") or []
        if feats:
            attrs = feats[0].get("attributes") or {}
            break

    if not attrs:
        print(f"Plan {plan_label} not found")
        return

    classsubtype = attrs.get("classsubtype")


    is_surveyed_raw = _decode("issurveyed", attrs.get("issurveyed"), classsubtype, field_domains, subtype_field_domains)
    is_current_raw  = _decode("iscurrent",  attrs.get("iscurrent"),  classsubtype, field_domains, subtype_field_domains)
    has_stratum_raw = _decode("hasstratum", attrs.get("hasstratum"), classsubtype, field_domains, subtype_field_domains)

    return Plan(
        plan_label        = plan_label.upper(),
        plan_type         = prefix,
        plan_number       = number,
        # is_surveyed       = is_surveyed_raw == "True" if is_surveyed_raw is not None else None,
        is_surveyed       = _to_surveyed_bool(is_surveyed_raw), # Dont think this is working (seems to be issue with 6maps API)
        is_current        = is_current_raw  == "True" if is_current_raw  is not None else None,
        has_stratum       = has_stratum_raw == "True" if has_stratum_raw is not None else None,
        purpose           = _decode("planpurpose",      attrs.get("planpurpose"),      classsubtype, field_domains, subtype_field_domains),
        extent_status     = _decode("planextentstatus", attrs.get("planextentstatus"), classsubtype, field_domains, subtype_field_domains),
        registration_date = _ms_to_date(attrs.get("registrationdate")),
        survey_date       = _ms_to_date(attrs.get("surveydate")),
        process_state     = attrs.get("processstate"),

        # Note: local_file is intentionally not set here — it defaults to None.
        # drive.py is responsible for downloading the plan file and setting local_file.
    )












# def get_plan_info():
#     """
#     Takes a plan number string like 'DP574558' or 'SP10027'
#     and returns metadata about that plan.
#     """
#     plan_label = input('Enter a plan label: ')

#     prefix, number, suffix = _parse_plan_label(plan_label)

#     field_domains, subtype_map, subtype_field_domains = _load_domain_lookups()

#     wanted_subtype = 1 if prefix == "DP" else 2 if prefix == "SP" else None
#     subtypes = [wanted_subtype] if wanted_subtype in subtype_map else list(subtype_map.keys())

#     attrs = None
#     for subtype in subtypes:
#         where = f"(classsubtype = {subtype}) AND (plannumber = {number})"
#         if suffix:
#             where += f" AND (plannumbersuffix = '{suffix}')"
#         else:
#             where += " AND (plannumbersuffix IS NULL OR plannumbersuffix = '')"

#         url = f"{BASE}/{PLAN_LAYER}/query"
#         r = requests.get(url, params={
#             "where":             where,
#             "outFields":         "*",
#             "returnGeometry":    "false",
#             "resultRecordCount": 1,
#             "f":                 "json"
#         }, timeout=60)
#         r.raise_for_status()
#         js = r.json()

#         if "error" in js:
#             err = js["error"]
#             raise RuntimeError(f"ArcGIS error {err.get('code')}: {err.get('message')}")

#         feats = js.get("features") or []
#         if feats:
#             attrs = feats[0].get("attributes") or {}
#             break

#     if not attrs:
#         print(f"Plan {plan_label} not found")
#         return

#     classsubtype = attrs.get("classsubtype")

#     result = {
#         "plan":              plan_label.upper(),
#         "subtype":           subtype_map.get(classsubtype, classsubtype),
#         "is_current":        _decode("iscurrent",        attrs.get("iscurrent"),        classsubtype, field_domains, subtype_field_domains),
#         "is_surveyed":       _decode("issurveyed",       attrs.get("issurveyed"),        classsubtype, field_domains, subtype_field_domains),
#         "has_stratum":       _decode("hasstratum",       attrs.get("hasstratum"),        classsubtype, field_domains, subtype_field_domains),
#         "purpose":           _decode("planpurpose",      attrs.get("planpurpose"),       classsubtype, field_domains, subtype_field_domains),
#         "extent_status":     _decode("planextentstatus", attrs.get("planextentstatus"),  classsubtype, field_domains, subtype_field_domains),
#         "registration_date": _ms_to_date(attrs.get("registrationdate")),
#         "survey_date":       _ms_to_date(attrs.get("surveydate")),
#         "process_state":     attrs.get("processstate"),
#     }

#     for key, value in result.items():
#         print(f"{key}: {value}")


        


























# def get_plan_info(plan_label: str):
#     """
#     Takes a plan number string like 'DP574558' or 'SP10027'
#     and returns metadata about that plan.
#     """
#     prefix, number, suffix = _parse_plan_label(plan_label)

#     field_domains, subtype_map, subtype_field_domains = _load_domain_lookups()

#     # Determine subtype to query (DP=1, SP=2)
#     wanted_subtype = 1 if prefix == "DP" else 2 if prefix == "SP" else None
#     subtypes = [wanted_subtype] if wanted_subtype in subtype_map else list(subtype_map.keys())

#     attrs = None
#     for subtype in subtypes:
#         where = f"(classsubtype = {subtype}) AND (plannumber = {number})"
#         if suffix:
#             where += f" AND (plannumbersuffix = '{suffix}')"
#         else:
#             where += " AND (plannumbersuffix IS NULL OR plannumbersuffix = '')"

#         url = f"{BASE}/{PLAN_LAYER}/query"
#         r = requests.get(url, params={
#             "where":             where,
#             "outFields":         "*",
#             "returnGeometry":    "false",
#             "resultRecordCount": 1,
#             "f":                 "json"
#         }, timeout=60)
#         r.raise_for_status()
#         js = r.json()

#         if "error" in js:
#             err = js["error"]
#             raise RuntimeError(f"ArcGIS error {err.get('code')}: {err.get('message')}")

#         feats = js.get("features") or []
#         if feats:
#             attrs = feats[0].get("attributes") or {}
#             break

#     if not attrs:
#         print(f"Plan {plan_label} not found")
#         return None

#     classsubtype = attrs.get("classsubtype")

#     return {
#         "plan":              plan_label.upper(),
#         "subtype":           subtype_map.get(classsubtype, classsubtype),
#         "is_current":        _decode("iscurrent",        attrs.get("iscurrent"),        classsubtype, field_domains, subtype_field_domains),
#         "is_surveyed":       _decode("issurveyed",       attrs.get("issurveyed"),        classsubtype, field_domains, subtype_field_domains),
#         "has_stratum":       _decode("hasstratum",       attrs.get("hasstratum"),        classsubtype, field_domains, subtype_field_domains),
#         "purpose":           _decode("planpurpose",      attrs.get("planpurpose"),       classsubtype, field_domains, subtype_field_domains),
#         "extent_status":     _decode("planextentstatus", attrs.get("planextentstatus"),  classsubtype, field_domains, subtype_field_domains),
#         "registration_date": _ms_to_date(attrs.get("registrationdate")),
#         "survey_date":       _ms_to_date(attrs.get("surveydate")),
#         "process_state":     attrs.get("processstate"),
#     }