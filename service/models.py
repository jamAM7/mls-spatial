"""
models.py — MLS Spatial Search Service
Data model definitions for all objects returned by the search pipeline.

This file contains only dataclass definitions.
No API calls, no logic, no imports from other project files.
Every other module imports from here.

API sources:
  [ADDR]   NSW Geocoded Addressing — portal.spatial.nsw.gov.au (FeatureServer/1)
  [ADMIN]  NSW Administrative Boundaries — portal.spatial.nsw.gov.au (NSW_Administrative_Boundaries_Theme/FeatureServer)
  [LOT]    NSW Land Parcel Property — portal.spatial.nsw.gov.au (FeatureServer/8)
  [MARKS]  Survey Marks GDA2020 — portal.spatial.nsw.gov.au (SurveyMarkGDA2020_multiCRS/FeatureServer/0)
  [PLAN]   SIX Maps Boundaries — maps.six.nsw.gov.au (sixmaps/Boundaries/MapServer/2)
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional


# ── Address ───────────────────────────────────────────────────────────────────

@dataclass
class Address:
    """
    Resolved street address with coordinates and administrative context.
    Sources: [ADDR] for coordinates, [ADMIN] for boundaries.
    """

    # From user input
    input_string: str               # as typed by the user

    # From [ADDR] — geocoding
    resolved_string: str            # normalised form e.g. "1 PIT STREET SYDNEY"
    longitude: float                # WGS84
    latitude: float                 # WGS84
    easting: float                  # GDA2020 MGA (zone varies)
    northing: float                 # GDA2020 MGA (zone varies)

    # From [ADMIN] — administrative boundaries (spatial query at address point)
    suburb: Optional[str] = None    # e.g. "MIRANDA"
    lga: Optional[str] = None       # e.g. "SUTHERLAND SHIRE"
    parish: Optional[str] = None    # e.g. "WORONORA"
    county: Optional[str] = None    # e.g. "CUMBERLAND"

    # From [ELEV] — AHD surface level (DEM) at this address point
    surface_level_ahd: Optional[float] = None
    # Note: each SurveyMark also carries its own surface_level_ahd (DEM at mark location)
    # allowing comparison with the SCIMS AHD height to detect disturbed marks or significant cut/fill


# ── Lot ───────────────────────────────────────────────────────────────────────

@dataclass
class Lot:
    """
    A cadastral lot polygon from the NSW Land Parcel Property theme.
    Source: [LOT]

    Field names match the NSW API schema where possible.
    DmC_ prefix fields in the API are coded values — intern must decode these
    using the layer metadata (same pattern as plan.py domain lookups).
    """

    # Identity — [LOT]
    lot_number: str                         # LotNumber e.g. "102"
    plan_label: str                         # PlanLabel e.g. "DP574558"
    section_number: str                     # SectionNumber — empty string if none
    plan_number: Optional[int] = None       # PlanNumber e.g. 574558
    plan_oid: Optional[int] = None          # PlanOID — internal plan object ID
    its_lot_id: Optional[int] = None        # ITSLotID — LRS lot identifier
    cad_id: Optional[int] = None            # CadID — cadastral object ID
    controlling_authority_oid: Optional[int] = None  # ControllingAuthorityOID
    classsubtype: Optional[int] = None      # ClassSubtype

    # Title — [LOT]
    its_title_status: Optional[int] = None          # ITSTitleStatus coded value
    its_title_status_label: Optional[str] = None    # decoded e.g. "Torrens Title", "Old System"

    # Stratum — [LOT]
    has_stratum: Optional[bool] = None      # HasStratum — lot has stratum lots above/below
    stratum_level: Optional[int] = None     # StratumLevel coded value
    stratum_level_label: Optional[str] = None  # decoded e.g. "Surface", "Above Surface"

    # Area — [LOT]
    plan_lot_area: Optional[float] = None       # PlanLotArea — area from deposited plan
    plan_lot_area_units: Optional[str] = None   # PlanLotAreaUnits e.g. "m2", "ha"

    # Dates — [LOT]
    create_date: Optional[datetime] = None      # CreateDate — when lot was created in system
    modified_date: Optional[datetime] = None    # ModifiedDate

    # Geometry — [LOT]
    geometry: list = field(default_factory=list)    # list of polygon rings — each ring is a list of
                                                    # [easting, northing] pairs. Part lots have
                                                    # multiple rings; normal lots have one.
                                                    # returnGeometry=true must be set in API query

    # Search context — set by search.py, not from API
    is_subject: bool = False            # True for the lot at the searched address

    # From [PROP] — FeatureServer/12 Property layer, joined by cadid == propid
    address: Optional[str] = None           # full address string e.g. "12 SMITH ST SYDNEY NSW 2000"


# ── Road ──────────────────────────────────────────────────────────────────────

@dataclass
class Road:
    """
    A road corridor polygon from the NSW Land Parcel Property theme.
    Source: [ROAD] — FeatureServer/5

    road_name_label is the human-readable road name e.g. "George Street".
    road_type and road_corridor_type are coded values decoded in api/road.py.
    Verify both domain dicts against the layer 5 metadata.
    """

    # Identity
    cadid: Optional[int] = None
    road_name_oid: Optional[int] = None         # roadnameoid — links to road name register
    road_name_label: str = ""                   # roadnamelabel e.g. "George Street"

    # Road classification
    road_type: Optional[int] = None             # roadtype — coded value
    road_type_label: Optional[str] = None       # decoded e.g. "Dedicated Road"
    road_corridor_type: Optional[int] = None    # roadcorridortype — coded value
    road_corridor_label: Optional[str] = None   # decoded e.g. "Arterial", "Local"

    # Context
    urbanity: Optional[str] = None              # "U" urban / "R" rural
    classsubtype: Optional[int] = None

    # Geometry — list of rings, each ring a list of [easting, northing] pairs.
    # Same shape as Lot.geometry.
    geometry: list = field(default_factory=list)


# ── RoadCentreline ────────────────────────────────────────────────────────────

@dataclass
class RoadCentreline:
    """
    A road centreline from the NSW Land Parcel Property theme.
    Source: FeatureServer/1

    Geometry is a list of paths (polyline), each path a list of
    [easting, northing] pairs. Most centrelines have a single path.
    """

    cadid: Optional[int] = None
    road_name_oid: Optional[int] = None
    road_name_label: str = ""           # roadnamelabel e.g. "George Street"
    urbanity: Optional[str] = None      # "U" urban / "R" rural

    # Geometry — list of paths, each path a list of [easting, northing] pairs
    geometry: list = field(default_factory=list)


# ── ElevationGrid ─────────────────────────────────────────────────────────────

@dataclass
class ElevationGrid:
    """
    AHD surface elevation sampled at a regular grid over the subject lot bbox.
    Built by api/elevation.py — fetch_elevation_grid().

    grid_spacing_m may differ from the requested spacing if the point count
    exceeded MAX_GRID_POINTS and was automatically scaled up (see capped field).

    points: list of dicts with keys: row, col, easting, northing, ahd
    """
    grid_spacing_m:   int
    padding_pct:      float
    bbox_padded:      dict               # min_e, max_e, min_n, max_n in MGA metres
    rows:             int
    cols:             int
    point_count:      int
    capped:           bool               # True if spacing was increased to stay under cap
    capped_spacing_m: Optional[int]      # actual spacing used if capped, else None
    points:           list = field(default_factory=list)


# ── Plan ──────────────────────────────────────────────────────────────────────

@dataclass
class Plan:
    """
    Survey or compiled plan metadata.
    Source: [PLAN]

    Note: the issurveyed field from SIX Maps is unreliable for older DPs.
    Treat with caution — the issurveyed field is unreliable for older DPs.
    """

    # Identity
    plan_label: str                         # e.g. "DP574558"
    plan_type: str                          # "DP" or "SP"
    plan_number: int                        # 574558

    # Attributes — decoded from ArcGIS coded value domains
    is_surveyed: Optional[bool] = None      # True = survey plan, False = compiled plan
    is_current: Optional[bool] = None
    has_stratum: Optional[bool] = None
    purpose: Optional[str] = None          # e.g. "Subdivision", "Survey", "Strata"
    extent_status: Optional[str] = None
    process_state: Optional[str] = None    # e.g. "Registered"

    # Dates
    registration_date: Optional[date] = None
    survey_date: Optional[date] = None

    # Local file — set by drive.py after Google Drive download
    local_file: Optional[Path] = None


# ── SurveyMark ────────────────────────────────────────────────────────────────

@dataclass
class SurveyMark:
    """
    Survey control mark from the NSW SCIMS database (GDA2020).
    Source: [MARKS]

    Data currency: gdadate and ahddate indicate when the mark's coordinates
    were last determined. retrieved_at records when this data was fetched
    from the API. If retrieved_at is more than 6 months ago, re-fetch before use.
    """

    # ── Identity ─────────────────────────────────────────────────────────────
    mark_number: int                        # marknumber
    mark_type: str                          # marktype — coded value e.g. "PM", "SSM", "BM"
    mark_status: str                        # markstatus — coded value e.g. "EX" (existing)
    mark_symbol: Optional[str] = None       # marksymbol — coded value
    mark_symbol_label: Optional[str] = None # marksymbol_label — decoded display string
    mark_alias: Optional[str] = None        # markalias — alternative name/reference
    monument_type: Optional[str] = None     # monumenttype — physical description
    monument_location: Optional[str] = None # monumentlocation — coded value
    classsubtype: Optional[int] = None      # classsubtype
    msoid: Optional[int] = None             # msoid — internal object ID
    is_gp_parent: Optional[int] = None      # isgparent — 1 if GPS parent mark

    # ── Trig station (if applicable) ─────────────────────────────────────────
    trig_name: Optional[str] = None         # trigname
    trig_type: Optional[str] = None         # trigtype — coded value

    # ── GDA2020 horizontal position ───────────────────────────────────────────
    easting: Optional[float] = None         # from feature geometry (GDA2020 MGA)
    northing: Optional[float] = None        # from feature geometry (GDA2020 MGA)
    longitude: Optional[float] = None       # longitude (GDA2020 geographic)
    latitude: Optional[float] = None        # latitude (GDA2020 geographic)
    mga_zone: Optional[int] = None          # mgazone e.g. 56
    mga_convergence: Optional[str] = None   # mgacon — convergence and scale factor label
    mga_csf_2020: Optional[float] = None    # mgacsf2020 — combined scale factor
    mga_csf_2020_label: Optional[str] = None    # mgacsf2020_label
    mga_easting_label: Optional[str] = None     # mgaeasting_label — formatted string
    mga_northing_label: Optional[str] = None    # mganorthing_label — formatted string

    # GDA2020 horizontal quality
    gda_class: Optional[str] = None         # gdaclass e.g. "A", "B", "C"
    gda_date: Optional[date] = None         # gdadate — when horizontal position was determined
    gda_source: Optional[int] = None        # gdasource
    gda_source_type: Optional[str] = None   # gdasourcetype
    gda_source_method: Optional[str] = None # gdasourcemethod
    gda_pos_uncertainty_label: Optional[str] = None  # gdaposuncertainty_label
    gda_loc_uncertainty_label: Optional[str] = None  # gdalocuncertainty_label

    # ── AHD height ────────────────────────────────────────────────────────────
    ahd_height: Optional[float] = None      # from geometry or dedicated field
    ahd_height_label: Optional[str] = None  # ahdheight_label — formatted string
    ahd_class: Optional[str] = None         # ahdclass e.g. "LC", "1", "2"
    ahd_date: Optional[date] = None         # ahddate — when AHD height was determined
    ahd_source: Optional[int] = None        # ahdsource
    ahd_source_type: Optional[str] = None   # ahdsourcetype
    ahd_source_method: Optional[str] = None # ahdsourcemethod
    ahd_pos_uncertainty_label: Optional[str] = None  # ahdposuncertainty_label
    ahd_loc_uncertainty_label: Optional[str] = None  # ahdlocuncertainty_label

    # AUSGeoid2020 separation
    ausgeoid2020: Optional[float] = None        # ausgeoid2020
    ausgeoid2020_label: Optional[str] = None    # ausgeoid2020_label

    # ── GDA2020 ellipsoidal height ────────────────────────────────────────────
    gda_height: Optional[float] = None              # gdaheight
    gda_height_label: Optional[str] = None          # gdaheight_label
    gda_height_date: Optional[date] = None          # gdaheightdate
    gda_height_class: Optional[str] = None          # gdaheightclass
    gda_height_order: Optional[str] = None          # gdaheightorder
    gda_height_pos_uncertainty: Optional[float] = None  # gdaheightposuncertainty
    gda_height_loc_uncertainty: Optional[float] = None  # gdaheightlocuncertainty
    gda_height_source: Optional[int] = None         # gdaheightsource
    gda_height_source_type: Optional[str] = None    # gdaheightsourcetype
    gda_height_source_method: Optional[str] = None  # gdaheightsourcemethod

    # ── Data currency ─────────────────────────────────────────────────────────
    retrieved_at: Optional[datetime] = None
    # When this record was fetched from the API.
    # If more than 6 months old, discard and re-fetch before use.
    # Check: (datetime.now() - mark.retrieved_at).days > 180


    # From [ELEV] — DEM surface level at this mark's location (Web Mercator input required)
    # Compare with ahd_height (SCIMS): a significant difference (>0.5m) may indicate a
    # disturbed mark, significant cut/fill, or data quality issue worth checking in the field.
    surface_level_ahd: Optional[float] = None

    # Set by api/survey_marks.py during full pipeline (/full-search only, not /search)
    local_sketch_path: Optional[Path] = None   # downloaded LSP PDF
    


# ── SearchResult ──────────────────────────────────────────────────────────────

@dataclass
class SearchResult:
    """
    The complete output of a single search operation.
    Built by search.py. Consumed by export.py, drive.py, and server.py.
    """

    address: Address
    subject_lot: Lot                        # the lot at the searched address
    nearby_lots: list[Lot]                  # all lots within search_radius_m (includes subject_lot)
    plans: list[Plan]                       # unique plans referenced by nearby_lots
    survey_marks: list[SurveyMark]          # all marks within marks_radius_m
    search_radius_m: int
    marks_radius_m: int                     # radius used for survey marks (may differ from search_radius_m)

    epsg: int
    datum: str
    mga_zone: int                           # 54, 55, or 56
    
    search_mode: str = "address"            # "address", "folio", or "polygon"
    cre_map_image: Optional[Path] = None    # PNG saved from CRE MapServer export
    roads: list = field(default_factory=list)
    road_centrelines: list = field(default_factory=list)
    elevation_grid: Optional[ElevationGrid] = None


