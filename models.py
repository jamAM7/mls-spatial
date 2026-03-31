from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from pathlib import Path

@dataclass
class Address:
    address: str
    x: float
    y: float
    suburb: Optional[str] = None
    lga: Optional[str] = None
    parish: Optional[str] = None
    county: Optional[str] = None

@dataclass
class Lot:
    # Required — a lot without these isn't useful
    lotidstring: str
    lotnumber: str
    plannumber: int
    plan_label: str

    # Optional from API
    sectionnumber: Optional[str] = None
    lot_area: Optional[float] = None
    lot_area_units: Optional[str] = None
    startdate: Optional[str] = None
    enddate: Optional[str] = None

    # Coded values
    its_title_status: Optional[int] = None
    its_title_status_label: Optional[str] = None
    stratum_level: Optional[int] = None
    stratum_level_label: Optional[str] = None
    has_stratum: Optional[int] = None
    has_stratum_label: Optional[str] = None

    # Geometry
    geometry: Optional[list] = None

    # Set manually in search.py — must come last since it has a default
    is_subject: bool = False

@dataclass
class Plan:
    plan_label: str
    subtype: Optional[str]
    is_current: Optional[str]
    is_surveyed: Optional[str]
    has_stratum: Optional[str]
    purpose: Optional[str]
    extent_status: Optional[str]
    registration_date: Optional[str]
    survey_date: Optional[str]
    process_state: Optional[str]            # required — must be provided, errors if missing (Either passes in str, or None, but cant pass nothing in)
    local_file: Optional[Path] = None       # defaults to None if not provided — no error

@dataclass
class SurveyMark:
    marknumber: int
    marktype: Optional[str]
    markstatus: Optional[str]
    marksymbol: Optional[str]
    easting: float
    northing: float
    zone: Optional[int]
    gda_class: Optional[str]
    pos_uncertainty: Optional[str]
    loc_uncertainty: Optional[str]
    source: Optional[int]
    csf: Optional[float]
    convergence: Optional[str]
    ahd_height: Optional[str]
    ahd_class: Optional[str]
    ausgeoid2020: Optional[float] 
    retrieved_at: datetime = field(default_factory=datetime.now)

@dataclass
class SearchResult:
    address: Address
    subject_lot: Optional[Lot]

    # This is needed instead of = [] This is because field(default_factory=list) 
    # tells python to create a new instance of this list every time. 
    # Otherwise would be appending to the same list every time class is called
    nearby_lots: list[Lot] = field(default_factory=list)

    survey_marks: list[SurveyMark] = field(default_factory=list)
    plans: list[Plan] = field(default_factory=list)