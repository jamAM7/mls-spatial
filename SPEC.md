# MLS Spatial Search Service — Build Specification

**Project:** mls-spatial
**Developer:** James Mitchell — Software Internship, Mitchell Land Surveyors Pty Ltd
**Purpose:** A local HTTP API service that, given a street address (or survey mark reference, folio identifier, or drawn geometry), returns cadastral lots, survey plans, survey marks, and surface levels — structured for consumption by the MLS web viewer, AutoCAD add-in, and MLSSurveyManager.

*Specification Version: 04 | Updated: June 2026*

---

## Roadmap

```
PHASE 1 — Foundation                              STATUS: COMPLETE
├── models.py                                     ✓
├── api/ refactor (return objects, no print)      ✓
├── search.py                                     ✓
├── export.py                                     ✓
├── drive.py                                      ✓
└── server.py                                     ✓

PHASE 2 — Clients                                 STATUS: IN PROGRESS
├── draw.py        PNG drawing script             ✓ (clients/draw.py)
├── PDF report     reportlab A4 search report     ~ basic version working (report.py)
│                                                   TODO: refactor to accept SearchResult directly
│                                                   TODO: add bearing/distance column to marks table
│                                                   TODO: surveyor review of field accuracy
├── Web viewer     Leaflet.js browser map         Week 5
└── AutoCAD add-in C# add-in draws in Civil 3D   Week 6

PHASE 3 — Quality and Robustness                  STATUS: NOT STARTED
├── pytest         Mocked HTTP unit tests         ✓ first version
├── GitHub Actions Run tests on every commit      TODO
└── Async calls    httpx + asyncio parallel       TODO

PHASE 4 — Expand the Service                      STATUS: IN PROGRESS
├── Dual radius    marks_radius_m parameter       ✓ (Bug #1 fixed)
├── /full-search   Full pipeline endpoint         ✓
├── SQLite history Store all searches locally     TODO
├── /mark endpoint Fetch single mark by type+no  TODO
├── SCIMS sketches Download LSP PDFs per mark     TODO
├── Surface levels AHD spot heights in search area TODO
├── Folio search   Search by lot/plan reference   Week 5
├── Polygon search Search by drawn geometry       Week 5
│              (AutoCAD polyline and KML files)
├── Roads layer    NSW road boundaries in output  Future
└── Caching        Avoid repeat API calls         Future

PHASE 5 — Deploy and Share                        STATUS: NOT STARTED
├── Docker         Dockerfile + docker-compose    TODO
├── Web viewer     see Phase 2                    Week 5
├── Authentication API key middleware             Future
└── QGIS plugin    Load results into QGIS         Future
```

---

## Known Bugs (GitHub Issues)

All three original bugs fixed. Additional bugs found and fixed during full-search pipeline work.

| Issue | Description | Files affected | Status |
|---|---|---|---|
| **#1** | No separate radius for survey marks — `marks_radius_m` missing | `server.py`, `search.py`, `export.py` | ✓ Fixed |
| **#2** | GeoJSON output missing mark fields: `gda_loc_uncertainty_label`, `mga_csf_2020`, `mga_csf_2020_label` | `export.py` | ✓ Fixed |
| **#3** | `subject_lot` label drops section number — `1//DP45424` instead of `1/A/DP45424` | `export.py`, `server.py`, `spatialsearch.py` | ✓ Fixed |
| **#4** | `search_plan.png` not generated in `/full-search` pipeline | `server.py` | ✓ Fixed — added `draw_png()` call |
| **#5** | `summary.json` never written to output folder | `server.py` | ✓ Fixed — written before `generate_report()` |
| **#6** | `generate_report()` crashes with `FileNotFoundError` — called before `summary.json` exists | `server.py` | ✓ Fixed — ordering corrected |
| **#7** | `report_path` referenced in `summary` dict before it is defined | `server.py` | ✓ Fixed — moved to post-report assignment |
| **#8** | `survey_marks.py` crashes on Windows with `OSError` for epoch 0 dates (`gdadate`, `ahddate`, `gdaheightdate`) | `api/survey_marks.py` | ✓ Fixed — `_epoch_ms_to_date()` helper added |

---

## Build Queue

Bugs all resolved. New feature work in order:

**Service layer (do next)**
1. `utils.py` — add `to_web_mercator()` ← prerequisite for all elevation calls
2. `api/address.py` — add surface level AHD fetch at address point using `[ELEV]`
3. `api/survey_marks.py` — add surface level fetch per mark (parallel, `[ELEV]`)
4. `export.py` — add `search_mode`, `surface_level_ahd`, `marks_radius_m` to GeoJSON search block
5. `api/survey_marks.py` — add `get_mark_by_reference()` (single mark attribute query)
6. `api/survey_marks.py` — add `download_sketch()` (SCIMS PDF per mark)
7. `api/lot.py` — add `get_lot_by_folio()`
8. `search.py` — wire folio search mode
9. `search.py` — wire surface level calls (address + marks)
10. `service/history.py` — SQLite search history (new file)
11. `server.py` — add `/mark/{type}/{number}` endpoint
12. `server.py` — add `/mark/{type}/{number}/sketch` endpoint
13. `server.py` — add `/history` endpoint
14. `report.py` — add bearing/distance to marks table; refactor to accept SearchResult directly

**Engineering hygiene (can be done alongside)**
15. Convert all `api/` modules from `requests` to `httpx` (async)
16. Rewrite all tests with mocked HTTP (`pytest-httpx`)
17. Add `Dockerfile` + `docker-compose.yml`
18. Add GitHub Actions `test.yml`
19. Update README

---

## Vision

The surveyor types an address (or mark reference, folio, or draws a polygon) into their tool of choice. The service queries NSW Spatial Services, downloads relevant plans and SCIMS locality sketches, and returns a single GeoJSON response. Each client — the web viewer, AutoCAD add-in, or MLSSurveyManager — consumes the GeoJSON in its own way.

```
Surveyor provides: address / mark / folio / drawn polygon
        |
        |  GET http://localhost:8000/search?address=87 Bunarba Rd Gymea Bay&radius_m=150&marks_radius_m=600
        v
This Python service (FastAPI, localhost:8000)
        |
        +-- NSW Spatial Services APIs  (lots, plans, marks, admin boundaries)
        +-- NSW 5M Elevation API       (AHD spot heights: address + each survey mark)
        +-- SIX Maps SketchPlans API   (locality sketch PDFs per mark)
        +-- Google Drive API           (download matching plan PDFs)
        |
        v
Returns GeoJSON FeatureCollection
        |
        +-- MLSSurveyManager (C# Razor Pages)  calls /full-search
        +-- Web viewer (Leaflet.js)             calls /search
        +-- AutoCAD C# add-in                  calls /search, draws entities
        +-- PDF report (reportlab)             reads GeoJSON, builds A4 report
```

---

## File Structure

```
mls-spatial/
├── service/
│   ├── server.py           ✓ FastAPI app — /health, /search, /cre_map, /plan, /full-search
│   │                         TODO: /mark, /mark/sketch, /history endpoints
│   ├── search.py           ✓ Main pipeline: search() -> SearchResult, marks_radius_m supported
│   │                         TODO: folio + geometry search modes, surface level calls, async conversion
│   ├── export.py           ✓ to_geojson() with all mark fields, subject lot label fixed
│   │                         TODO: add search_mode, surface_level_ahd, marks_radius_m to search block
│   │                         TODO: convert fetch_cre_map_image to httpx, remove stray print()
│   ├── drive.py            ✓ Google Drive plan download
│   ├── report.py           ~ Basic PDF pipeline working (cover, CRE map, lots, marks, plans)
│   │                         TODO: refactor to accept SearchResult directly
│   │                         TODO: add bearing/distance column to marks table
│   │                         TODO: surveyor review of field accuracy
│   ├── history.py          ✗ not built — SQLite search history
│   ├── models.py           ✓ All dataclasses — single source of truth
│   ├── config.py           ✓ Constants and API base URLs
│   ├── utils.py            ✓ sanitise_address, coordinate helpers
│   │                         TODO: add to_web_mercator() for [ELEV] calls
│   └── api/
│       ├── address.py      ✓ Geocoding + admin boundaries
│       │                     TODO: surface_level_ahd fetch, async conversion
│       ├── lot.py          ✓ Lot polygons + attributes
│       │                     TODO: get_lot_by_folio(), async conversion
│       ├── plan.py         ✓ Plan metadata
│       │                     TODO: async conversion
│       └── survey_marks.py ✓ Spatial mark query, Windows epoch date fix
│                             TODO: get_mark_by_reference(), download_sketch(),
│                                   surface_level_ahd per mark, async conversion
├── clients/
│   ├── draw.py             ✓ PNG drawing script (consumes /search GeoJSON)
│   └── SPEC.md             ✓ Client-side integration notes
├── console/
│   ├── run.py              ✓ Interactive CLI entry point
│   └── search_console.py   ✓
├── tests/
│   ├── test_address.py     ✗ not written
│   ├── test_lot.py         ✗ not written
│   ├── test_plan.py        ✗ not written
│   └── test_survey_marks.py ✗ broken imports, effectively empty
├── samples/                Original proof-of-concept scripts — reference only
├── output/                 Local search output (gitignored)
├── Dockerfile              ✗ not built
├── docker-compose.yml      ✗ not built
├── .github/
│   └── workflows/
│       └── test.yml        ✗ not built
├── requirements.txt
├── .gitignore
├── README.md               ✗ needs update
├── SPEC.md                 This file
└── PLAN.md                 6-week internship plan
```

**Rule:** No `print()` in any `api/` module or `search.py`. Print only in CLI entry points or `if __name__ == "__main__"` blocks.

---

## API Sources

| Label | Service | Base URL | Used for |
|---|---|---|---|
| `[ADDR]` | NSW Geocoded Addressing | `https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Geocoded_Addressing_Theme/FeatureServer/1` | Address string -> coordinates |
| `[ADMIN]` | NSW Administrative Boundaries | `https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Administrative_Boundaries_Theme/FeatureServer` | Address point -> suburb, LGA, parish, county |
| `[LOT]` | NSW Land Parcel Property | `https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Land_Parcel_Property_Theme_multiCRS/FeatureServer/8` | Coordinates -> lots with polygons; folio -> lot |
| `[MARKS]` | Survey Marks GDA2020 (spatial) | `https://portal.spatial.nsw.gov.au/server/rest/services/SurveyMarkGDA2020_multiCRS/FeatureServer/0` | Coordinates + radius -> nearby marks |
| `[MARK_ATTR]` | Survey Marks GDA2020 (attribute) | `https://portal.spatial.nsw.gov.au/server/rest/services/SurveyMarkGDA2020/MapServer/0` | Mark type + number -> single mark record |
| `[PLAN]` | SIX Maps Boundaries | `https://maps.six.nsw.gov.au/arcgis/rest/services/sixmaps/Boundaries/MapServer/2` | Plan label -> plan metadata |
| `[CREMAP]` | SIX Maps CRE export | `https://maps.six.nsw.gov.au/arcgis/rest/services/sixmaps/CRE/MapServer/export` | Bounding box -> PNG cadastral map image |
| `[ELEV]` | NSW 5M Elevation ImageServer | `https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_5M_Elevation/ImageServer/identify` | Point -> AHD spot height from 5m DEM (Web Mercator input required). Called once for address + once per survey mark. |
| `[SKETCH]` | SIX Maps SketchPlans | `http://maps.six.nsw.gov.au/SketchPlansWS/rest/getSketchPlans` | Mark reference -> locality sketch PDF |

**Coordinate systems:**
- All spatial queries use WKID **7856** (GDA2020 MGA Zone 56) for NSW Zone 56 addresses
- `[ELEV]` requires **EPSG:3857** (Web Mercator) — convert using `pyproj` before calling
- Zone is detected from longitude and EPSG derived from `config.py EPSG_CODES` dict

---

## Data Model — models.py

`models.py` is the single source of truth. Every other module imports from it. No imports from other project files — standard library only.

### Address
```python
@dataclass
class Address:
    input_string: str           # as typed by user
    resolved_string: str        # normalised e.g. "87 BUNARBA ROAD GYMEA BAY NSW 2227"
    longitude: float            # WGS84
    latitude: float             # WGS84
    easting: float              # GDA2020 MGA
    northing: float             # GDA2020 MGA

    # From [ADMIN] — populated in parallel with other admin calls
    suburb: Optional[str] = None
    lga: Optional[str] = None
    parish: Optional[str] = None
    county: Optional[str] = None

    # From [ELEV] — AHD surface level (DEM) at this address point
    surface_level_ahd: Optional[float] = None
    # Note: each SurveyMark also carries its own surface_level_ahd (DEM at mark location)
    # allowing comparison with the SCIMS AHD height to detect disturbed marks or significant cut/fill
```

### Lot
No changes from existing models.py. Key fields: `lot_number`, `plan_label`, `section_number`, `geometry` (polygon rings), `is_subject`, `its_title_status_label`, `plan_lot_area`.

### Plan
No changes. Key fields: `plan_label`, `plan_type`, `is_surveyed`, `registration_date`, `local_file`.

### SurveyMark
Two new fields added to existing model:
```python
    # From [ELEV] — DEM surface level at this mark's location (Web Mercator input required)
    # Compare with ahd_height (SCIMS): a significant difference (>0.5m) may indicate a
    # disturbed mark, significant cut/fill, or data quality issue worth checking in the field.
    surface_level_ahd: Optional[float] = None

    # Set by api/survey_marks.py during full pipeline (/full-search only, not /search)
    local_sketch_path: Optional[Path] = None   # downloaded LSP PDF
```

All other fields unchanged — `mga_csf_2020`, `mga_csf_2020_label`, and `gda_loc_uncertainty_label` are already defined and fetched; they just need to be included in `export.py` output (Issue #2).

### SearchResult
```python
@dataclass
class SearchResult:
    address: Address
    subject_lot: Lot
    nearby_lots: list[Lot]
    plans: list[Plan]
    survey_marks: list[SurveyMark]
    search_radius_m: int            # radius for lots, plans, admin boundaries
    marks_radius_m: int             # radius for survey marks (NEW — may equal search_radius_m)
    epsg: int
    datum: str
    mga_zone: int
    cre_map_image: Optional[Path] = None
```

---

## API Endpoints — server.py

`server.py` contains endpoint definitions only. No API calls, no data processing.

### Updated existing endpoints

```
GET /health
    Response: {"status": "ok"}

GET /search?address={address}&radius_m={radius_m}&marks_radius_m={marks_radius_m}
    radius_m default: 200
    marks_radius_m default: radius_m (if not supplied, marks use same radius as lots)
    Response: GeoJSON FeatureCollection

GET /search?folio={folio}&radius_m={radius_m}&marks_radius_m={marks_radius_m}
    Example: /search?folio=102/DP574558&radius_m=150&marks_radius_m=500
    Resolves lot centroid from folio reference, then runs standard search
    Response: GeoJSON FeatureCollection (same format)

GET /search?geometry={geojson}&radius_m={radius_m}&marks_radius_m={marks_radius_m}
    geometry: URL-encoded GeoJSON polygon string
    Lots and plans bounded by polygon intersection (radius_m ignored for lots)
    marks_radius_m still applies as distance from polygon centroid for marks
    Response: GeoJSON FeatureCollection (same format)

GET /cre_map?address={address}&radius_m={radius_m}&map_radius_m={map_radius_m}
    Response: PNG image

GET /full-search?address={address}&radius_m={radius_m}&marks_radius_m={marks_radius_m}&output_folder={path}
    Full pipeline: search + CRE map + drawn PNG + plan downloads + SCIMS sketches + PDF report
    Response: flat summary dict (consumed by MLSSurveyManager)

GET /plan/{plan_label}
    Example: /plan/DP574558
    Response: single Plan object as JSON
```

### New endpoints

```
GET /mark/{mark_type}/{mark_number}
    Example: /mark/TS/2761  or  /mark/PM/12345
    Queries [MARK_ATTR] by attribute (not spatial)
    Response: single SurveyMark object as JSON

GET /mark/{mark_type}/{mark_number}/sketch
    Example: /mark/TS/2761/sketch
    Fetches locality sketch PDF from [SKETCH]
    Response: PDF file download
```

**Search mode priority:** `geometry` > `folio` > `address`. At least one must be supplied to `/search`.

---

## Search Pipeline — search.py

Function signature after updates:

```python
def search(
    address_input: str = None,
    folio: str = None,
    geometry: dict = None,
    radius_m: int = 200,
    marks_radius_m: int = None,
    datum: str = "GDA2020"
) -> SearchResult | None:
```

- If `marks_radius_m` is `None`, default to `radius_m`
- If `folio` supplied: call `api/lot.get_lot_by_folio()`, compute centroid, use as search origin
- If `geometry` supplied: use polygon for lot/plan queries; derive centroid for admin and mark queries
- Plans fetched in parallel using `ThreadPoolExecutor` (already implemented)
- All NSW API calls converted to async using `httpx` + `asyncio` (Week 1)

---

## Surface Levels — api/address.py and api/survey_marks.py

Surface levels are returned at two sets of locations:

1. **Subject address** — a single DEM spot height at the search origin (set on `Address.surface_level_ahd`)
2. **Each survey mark** — a DEM spot height at the mark's MGA location (set on `SurveyMark.surface_level_ahd`)

Comparing a mark's `surface_level_ahd` (DEM) with its `ahd_height` (SCIMS measured value) gives a useful indicator. A significant difference (>0.5m) may suggest the mark is in a cut/fill area, has been disturbed, or the DEM is unreliable at that location.

### Shared coordinate conversion — service/utils.py

```python
from pyproj import Transformer

_to_web_mercator = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

def to_web_mercator(longitude: float, latitude: float) -> tuple[float, float]:
    """Convert WGS84 lon/lat to Web Mercator (EPSG:3857) for the [ELEV] API."""
    return _to_web_mercator.transform(longitude, latitude)
```

### At the address — api/address.py

Five calls run concurrently in `ThreadPoolExecutor`: four `[ADMIN]` boundary queries (suburb, LGA, parish, county) plus one `[ELEV]` elevation query.

```python
x, y = to_web_mercator(address.longitude, address.latitude)
# GET [ELEV]/identify?geometry={x},{y}&geometryType=esriGeometryPoint&f=json
# data["value"] -> float, or "NoData" for ocean / outside coverage
address.surface_level_ahd = float(data["value"]) if data.get("value") not in (None, "NoData") else None
```

### At each survey mark — api/survey_marks.py

After building the `list[SurveyMark]`, fetch elevation for all marks in parallel:

```python
def _fetch_elevation(longitude: float, latitude: float) -> float | None:
    x, y = to_web_mercator(longitude, latitude)
    # GET [ELEV]/identify ... return float or None

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(_fetch_elevation, m.longitude, m.latitude): m for m in marks}
    for future, mark in futures.items():
        mark.surface_level_ahd = future.result()
```

`longitude` and `latitude` are already populated from the `[MARKS]` API response.

**Performance note:** for a typical search returning 6–10 marks, 10 parallel elevation calls add ~2–4 seconds. Acceptable. If `marks_radius_m` is large and returns >20 marks, consider skipping elevation for marks with no `ahd_height` (they are likely non-functional).

---

## Administrative Boundaries — api/address.py

---

## Survey Marks — api/survey_marks.py

### Spatial search (existing, updated)
`get_survey_mark_info(x, y, epsg, distance)` — unchanged except `distance` parameter is now passed `marks_radius_m` from `search.py` rather than `radius_m`.

### Single mark lookup (new)
```python
def get_mark_by_reference(mark_type: str, mark_number: int) -> SurveyMark | None:
    """
    Attribute query to [MARK_ATTR].
    where=marknumber={mark_number} AND marktype='{mark_type}'
    Returns a single SurveyMark or None.
    """
```

### SCIMS sketch download (new)
```python
def download_sketch(mark: SurveyMark, dest_folder: Path) -> Path | None:
    """
    Fetches locality sketch PDF from [SKETCH] for this mark.
    Saves to dest_folder/marks/{mark_type}{mark_number}.pdf
    Returns path if downloaded, None if not found.
    Only called during full pipeline (/full-search), not /search.
    """
```

Mark reference format: `f"{mark.mark_type}{mark.mark_number}"` e.g. `"TS2761"`, `"PM12345"`

### Surface level fetch (new)
See **Surface Levels** section above. Called after spatial search returns the mark list; runs in parallel across all marks.

---

## Folio Search — api/lot.py

```python
def get_lot_by_folio(lot_number: str, section_number: str, plan_label: str, epsg: int) -> Lot | None:
    """
    Fetches a specific lot by folio reference.
    Query [LOT] with: LotNumber='{lot_number}' AND PlanLabel='{plan_label}'
    If section_number is non-empty, also filter: SectionNumber='{section_number}'
    Returns Lot with geometry (returnGeometry=true), or None.
    """
```

Folio string parsing (in `server.py` or `search.py`):
- Input: `"102/DP574558"` -> lot_number=`"102"`, section=`""`, plan=`"DP574558"`
- Input: `"1/A/DP45424"` -> lot_number=`"1"`, section=`"A"`, plan=`"DP45424"`

Centroid calculation from geometry rings: average of all ring coordinates.

---

## Polygon/Polyline Search

When `geometry` is supplied to `/search`:

- Lot query: `geometryType=esriGeometryPolygon`, `geometry={"rings": [...]}`, `spatialRel=esriSpatialRelIntersects`
- Mark query: derive centroid from polygon, use centroid + `marks_radius_m` as normal
- Admin boundary query: derive centroid from polygon, use point intersection as normal
- `radius_m` is ignored for lot/plan queries (polygon is the boundary)
- GeoJSON `search` block records `"search_mode": "polygon"` instead of `"address"` or `"folio"`

### Geometry input formats

The service always receives a GeoJSON polygon in the `geometry` parameter. The conversion from source format to GeoJSON happens in the client:

**Web viewer (`leaflet-draw`):** The Leaflet draw plugin produces GeoJSON natively. Pass the polygon feature geometry directly.

**KML file upload:** User uploads a `.kml` file in the web viewer. The viewer parses the KML (XML) client-side using `DOMParser` and extracts the `<coordinates>` element from the first `<Polygon>`. Converts to GeoJSON rings and passes to `/search`.

The typical surveyor workflow is: open **Google My Maps** (maps.google.com/mymaps), draw a polygon over the search area, export via **KML download**, and upload the file into the web viewer. Google My Maps exports standard KML and is compatible with this parser with no modification required.

```javascript
// KML coordinate format: "lon,lat,alt lon,lat,alt ..."
// Convert to GeoJSON rings: [[lon, lat], ...]
```

**AutoCAD polyline:** The C# add-in prompts the user to select a polyline. It iterates the polyline vertices, converts from MGA easting/northing to WGS84 longitude/latitude (using the AutoCAD coordinate system), and serialises as a GeoJSON polygon string passed to `/search`.

In all cases the service receives a standard GeoJSON polygon — it has no knowledge of how it was drawn.

---

## GeoJSON Output Format — export.py

### Updated `search` block
```json
{
  "type": "FeatureCollection",
  "search": {
    "address_input": "87 Bunarba Rd Gymea Bay",
    "address_resolved": "87 BUNARBA ROAD GYMEA BAY NSW 2227",
    "search_mode": "address",
    "suburb": "GYMEA BAY",
    "lga": "SUTHERLAND SHIRE",
    "parish": "WORONORA",
    "county": "CUMBERLAND",
    "surface_level_ahd": 34.2,
    "radius_m": 150,
    "marks_radius_m": 600,
    "subject_lot": "102//DP574558",
    "lot_count": 14,
    "plan_count": 8,
    "mark_count": 6,
    "datum": "GDA2020",
    "mga_zone": 56,
    "coordinate_system": "GDA2020 MGA Zone 56 (EPSG:7856)"
  },
  "features": [...]
}
```

`search_mode` values: `"address"`, `"folio"`, `"polygon"`

### Subject lot label — section number fix (Issue #3)

Replace all four instances of:
```python
f"{lot.lot_number}//{lot.plan_label}"
```
With:
```python
section = f"/{lot.section_number}" if lot.section_number else ""
f"{lot.lot_number}{section}/{lot.plan_label}"
```

### Updated survey mark feature properties (Issue #2 + surface levels)

Add these four fields to the mark properties dict in `to_geojson()`:
```json
"gda_loc_uncertainty_label": "0.01",
"mga_csf_2020": 0.999945,
"mga_csf_2020_label": "0.999945",
"surface_level_ahd": 33.8
```

`surface_level_ahd` on a mark is the DEM value at the mark's location. Compare with `ahd_height` (the SCIMS measured value) to assess mark reliability. A difference >0.5m is worth noting in the field.

---

## SQLite Search History

New file: `service/history.py`

Store every completed search in a local SQLite database using `sqlite3` (standard library — no SQLAlchemy needed at this stage).

```sql
CREATE TABLE IF NOT EXISTS search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    searched_at TEXT,
    search_mode TEXT,
    address_input TEXT,
    address_resolved TEXT,
    subject_lot TEXT,
    suburb TEXT,
    lga TEXT,
    radius_m INTEGER,
    marks_radius_m INTEGER,
    lot_count INTEGER,
    plan_count INTEGER,
    mark_count INTEGER,
    surface_level_ahd REAL
);
```

New endpoint:
```
GET /history?limit={n}
    Returns the last n searches (default 20) as JSON array
```

---

## PDF Search Report — service/report.py

A print-ready A4 PDF generated from a `SearchResult`. Called during `/full-search`, saved to `output_folder/search_report.pdf`.

Sections:
1. Header: address, date, subject lot, suburb/LGA/parish/county, surface level AHD
2. CRE map image (if available)
3. Lot table: lot number, plan label, title status, area, registration date
4. Survey mark table: mark type+number, GDA class, AHD height, easting, northing, bearing and distance from subject lot centroid
5. Plan list: plan label, type (surveyed/compiled), registration date, downloaded (yes/no)

Bearing and distance from subject lot centroid to each mark — compute in `report.py` from coordinates. Formula is standard polar to rectangular conversion.

Library: `reportlab` (already in requirements from earlier work).

---

## Unit Tests — tests/

All tests use mocked HTTP — no live API calls. Use `pytest-httpx` to intercept `httpx` requests (after async conversion) or `responses` library for `requests`.

Each test file follows this pattern:
```python
def test_returns_correct_type(httpx_mock):
    httpx_mock.add_response(url="...", json={...})  # fixture data
    result = get_address_coordinates("87 Bunarba Rd Gymea Bay", out_sr=7856)
    assert isinstance(result, Address)
```

Fixture data (sample API responses) stored in `tests/fixtures/` as JSON files.

Tests must pass in CI without internet access.

---

## Docker

`Dockerfile`:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "service.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

Note: `credentials.json` and `token.json` are gitignored and must be mounted as volumes for Google Drive integration to work in Docker.

---

## GitHub Actions — .github/workflows/test.yml

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: pytest tests/
```

---

## Running the Service

```bash
# Setup
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt

# Development (auto-reloads on code changes)
uvicorn service.server:app --reload --port 8000

# Production
uvicorn service.server:app --port 8000

# Docker
docker build -t mls-spatial .
docker run -p 8000:8000 mls-spatial

# Tests
pytest tests/
```

Interactive API docs: `http://localhost:8000/docs`

---

## Dependencies — requirements.txt

```
requests
httpx
fastapi
uvicorn
pyproj
reportlab
google-api-python-client
google-auth-oauthlib
google-auth-httplib2
pytest
pytest-httpx
```

---

## .gitignore — required entries

```
credentials.json
token.json
output/
__pycache__/
*.pyc
venv/
.env
*.db
```

---

## What the C# AutoCAD Add-in Needs

Outside the scope of this Python project but documented for alignment:

- Call `/health` on add-in load — warn if service is not running
- Call `/search?address={address}&radius_m={radius_m}&marks_radius_m={marks_radius_m}`
- Parse GeoJSON FeatureCollection
- For `feature_type == "lot"`:
  - Draw closed polyline from polygon coordinates
  - Colour by: `is_surveyed == false` -> blue; `is_surveyed == true` -> red shaded by `registration_date`
  - `is_subject == true` -> add marker at centroid
- For `feature_type == "survey_mark"`:
  - Insert block at `[easting, northing]`
  - Label with `mark_number`, `gda_class`, `ahd_height_label`
  - Show `mga_easting_label`, `mga_northing_label` as coordinate annotation
  - Show `mga_csf_2020` as annotation (useful for field computations)
- Zoom to extents of all drawn features

---

*Specification: MLS Spatial Search Service | Version 03 | June 2026 | Developer: James Mitchell*

































# OLD FROM MAY 
# OLD FROM MAY
# OLD FROM MAY



# MLS Spatial Search Service — Build Specification - OLD from MAY

**Project:** py-spatialservices-starter
**Developer:** James Mitchell — Software Internship, Mitchell Land Surveyors Pty Ltd
**Purpose:** A local HTTP API service that, given a street address and search radius, returns all cadastral lots, survey plans, and survey marks in that area — structured for consumption by the MLS AutoCAD add-in.

---

## Roadmap

A high-level view of where this project is headed. Each phase builds on the last.

```
PHASE 1 — Foundation (current)
├── models.py           Data model defined ✓
├── SPEC.md             Build specification written ✓
├── api/ refactor       Return objects instead of printing
├── search.py           Single pipeline function
├── export.py           GeoJSON output + CRE map image
├── drive.py            Google Drive plan download
└── server.py           FastAPI service running locally

PHASE 2 — Clients
├── draw.py             PNG drawing script (consumes the API)
├── AutoCAD add-in      C# add-in calls /search, draws in AutoCAD (Stephen)
└── PDF report          Formatted proposal search report (reportlab/weasyprint)

PHASE 3 — Quality and Robustness
├── pytest              Unit tests for all api/ modules (mocked HTTP)
├── GitHub Actions      Run tests automatically on every commit (CI/CD)
└── Async calls         Parallel NSW API calls using asyncio/httpx (faster responses)

PHASE 4 — Expand the Service
├── Roads layer         Add NSW road boundaries to GeoJSON output
├── Caching             Store recent results — avoid repeat API calls
├── New endpoints       /mark/{mark_number}, /lot/{plan_label}/{lot_number}
└── SQLite history      Store all searches locally for audit and replay

PHASE 5 — Deploy and Share
├── Web viewer          Browser map (Leaflet.js) — show anyone without AutoCAD
├── Docker              Package as a container — runs anywhere
├── QGIS plugin         Load search results directly into QGIS as vector layers
└── Authentication      API key — safe to expose on a local network
```

**Current position:** End of Phase 1 — data model and spec complete, build work starting.

---

## Vision

The surveyor types an address and radius into the AutoCAD add-in. The add-in calls this Python service running locally on the same machine. The service queries NSW Spatial Services, downloads relevant plans from Google Drive, and returns a single GeoJSON response. The add-in draws everything in AutoCAD — lots colour-coded by plan type and age, survey mark locations, and a pin on the subject lot.

---

## How It Will Be Used

```
Surveyor types address in AutoCAD add-in
        │
        │  GET http://localhost:8000/search?address=87 Bunarba Rd Gymea Bay&radius_m=200
        ▼
This Python service (FastAPI, localhost)
        │
        ├── NSW Spatial Services APIs  (lots, plans, survey marks, CRE map image)
        └── Google Drive API           (download matching plans to proposal folder)
        │
        ▼
Returns GeoJSON FeatureCollection
        │
        ▼
C# AutoCAD add-in draws entities from the GeoJSON
```

The Python service and the C# add-in are fully decoupled. Python does not know anything about AutoCAD. C# does not know anything about NSW APIs. They communicate only via GeoJSON over HTTP.

---

## File Structure

Refactor the existing codebase into this structure. Do not delete existing files until their replacement is tested.

```
py-spatialservices-starter/
├── models.py           NEW — all dataclasses (Address, Lot, Plan, SurveyMark, SearchResult)
├── search.py           NEW — single pipeline function: search(address, radius_m) → SearchResult
├── export.py           NEW — to_geojson(result) → dict; fetch_cre_map_image(result) → Path
├── drive.py            NEW — Google Drive search and download (port from Stephen's code)
├── server.py           NEW — FastAPI app, endpoint definitions only, no business logic
├── config.py           EXISTING — add any new constants here
├── utils.py            EXISTING — keep as-is
├── api/
│   ├── address.py      REFACTOR — return Address object (+ admin boundaries), no print statements
│   ├── lot.py          REFACTOR — return list[Lot] with full fields and geometry
│   ├── plan.py         REFACTOR — return Plan object, no print statements
│   ├── survey_marks.py REFACTOR — return list[SurveyMark] with all fields, set retrieved_at
│   └── cre.py          DELETE — title status and area come from [LOT] directly; this file is no longer needed
├── requirements.txt    UPDATE — add fastapi, uvicorn, google-api-python-client, google-auth-oauthlib
└── SPEC.md             THIS FILE
```

**Rule:** No `print()` calls inside any `api/` module or `search.py`. Printing is only allowed in the CLI (`spatialsearch.py`) or in `__main__` blocks used for testing. API functions return data — they do not display it.

---

## Data Model — models.py

**The complete data model is defined in `models.py` in the root of the project. Read that file.**

`models.py` is the single source of truth for all data shapes. Every other file imports from it. It has no imports from other project files — it only uses Python standard library (`dataclasses`, `datetime`, `pathlib`, `typing`).

Key points for each class:

### Address
- Coordinates come from `api/address.py` via the NSW Geocoded Addressing API `[ADDR]`
- `suburb`, `lga`, `parish`, and `county` come from a **separate** spatial query to the NSW Administrative Boundaries API `[ADMIN]` — see below
- All four boundary fields are `Optional` — populate them in `api/address.py` after resolving the coordinates

### Lot
- Full field set from NSW Land Parcel Property API `[LOT]`
- `its_title_status`, `stratum_level`, and `has_stratum` are coded integer values from the API — they must be decoded using layer metadata, the same way `plan.py` already decodes plan attributes
- Store both the raw integer (e.g. `its_title_status = 1`) and the decoded string (e.g. `its_title_status_label = "Torrens Title"`)
- `geometry` must be populated — set `returnGeometry=true` in the API query and capture the polygon rings as a list of `[easting, northing]` pairs
- `is_subject` is not from the API — set it to `True` in `search.py` for the lot that contains the searched address

### Plan
- Source: SIX Maps Boundaries MapServer `[PLAN]`
- `is_surveyed` from SIX Maps is **unreliable for older DPs** — treat with caution, CRE is authoritative for title status
- `local_file` is `None` until `drive.py` downloads the file and sets the path

### SurveyMark
- Full field set from Survey Marks GDA2020 API `[MARKS]`
- The API returns many pre-formatted label fields (e.g. `mgaeasting_label = "334521.456 E"`) — capture all of them, they are useful for display and reporting
- **`retrieved_at` must always be set** to `datetime.now()` at the time of the API call
- Data currency check: `(datetime.now() - mark.retrieved_at).days > 180` — if True, the data is stale and must be re-fetched before use in a survey

### SearchResult
- Built by `search.py` — it calls all `api/` modules and assembles one `SearchResult`
- `nearby_lots` includes the subject lot
- `plans` is a deduplicated list — many lots share a plan, only include each plan once

---

## API Sources

| Label | Service | Base URL | Used for |
|---|---|---|---|
| `[ADDR]` | NSW Geocoded Addressing | `https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Geocoded_Addressing_Theme/FeatureServer/1` | Address → coordinates |
| `[ADMIN]` | NSW Administrative Boundaries | `https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Administrative_Boundaries_Theme/FeatureServer` | Address → suburb, LGA, parish, county |
| `[LOT]` | NSW Land Parcel Property | `https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Land_Parcel_Property_Theme_multiCRS/FeatureServer/8` | Coordinates → lots with polygons |
| `[MARKS]` | Survey Marks GDA2020 | `https://portal.spatial.nsw.gov.au/server/rest/services/SurveyMarkGDA2020_multiCRS/FeatureServer/0` | Coordinates → survey marks |
| `[PLAN]` | SIX Maps Boundaries | `https://maps.six.nsw.gov.au/arcgis/rest/services/sixmaps/Boundaries/MapServer/2` | Plan label → plan metadata |
| `[CREMAP]` | SIX Maps CRE export | `https://maps.six.nsw.gov.au/arcgis/rest/services/sixmaps/CRE/MapServer/export` | Bounding box → PNG map image |

All spatial queries use WKID **7856** (GDA2020 MGA Zone 56).

---

## Administrative Boundaries — api/address.py

After resolving the address coordinates, make four additional spatial queries to `[ADMIN]` to populate `suburb`, `lga`, `parish`, and `county` on the `Address` object.

The NSW Administrative Boundaries FeatureServer has multiple layers. Query each with `esriSpatialRelIntersects` using the address point:

```
GET [ADMIN]/{layer_id}/query
    ?geometry={easting},{northing}
    &geometryType=esriGeometryPoint
    &inSR=7856
    &spatialRel=esriSpatialRelIntersects
    &outFields=*
    &f=json
```

Find the correct layer IDs by browsing:
`https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Administrative_Boundaries_Theme/FeatureServer`

Look for layers named Suburb/Locality, LGA, Parish, County. Return the relevant name field from each.

These four calls can be made in parallel using `concurrent.futures.ThreadPoolExecutor` to avoid adding significant latency.

---

## Survey Marks — api/survey_marks.py

Capture **all fields** from the `[MARKS]` API response. The full field list is defined in `models.py` with comments mapping each Python field name to its API field name.

Key points:
- Set `retrieved_at = datetime.now()` on every `SurveyMark` before returning it
- The API returns many `_label` fields (pre-formatted strings) alongside raw numeric fields — capture both
- `easting` and `northing` come from the feature **geometry**, not from attribute fields
- `longitude` and `latitude` are available as attribute fields (GDA2020 geographic coordinates)
- `mark_number` is an integer in the API (`esriFieldTypeInteger`) — store as `int`

Data currency rule: if `(datetime.now() - mark.retrieved_at).days > 180`, the cached data must not be used. Re-call the API.

---

## Lot Fields — api/lot.py

The lot query must include `returnGeometry=true`. The polygon rings from the geometry response must be stored in `Lot.geometry` as a list of `[easting, northing]` pairs.

Coded value fields that require decoding (fetch domain lookup from layer metadata — same pattern as `plan.py`):

| Field | Type | Example decoded value |
|---|---|---|
| `its_title_status` | SmallInteger | `"Torrens Title"`, `"Old System"`, `"Crown"` |
| `stratum_level` | SmallInteger | `"Surface"`, `"Above Surface"`, `"Below Surface"` |
| `has_stratum` | SmallInteger | `True` / `False` |

Store raw integer in the main field and decoded string in the `_label` field.

---

## GeoJSON Output Format — export.py

`to_geojson(result: SearchResult) -> dict` must return a valid GeoJSON FeatureCollection.

Every feature must have a `feature_type` property so the C# add-in knows what to draw.

**Lot feature:**
```json
{
  "type": "Feature",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[easting, northing], ...]]
  },
  "properties": {
    "feature_type": "lot",
    "lot_number": "102",
    "plan_label": "DP574558",
    "plan_number": 574558,
    "section_number": "",
    "is_subject": true,
    "is_surveyed": true,
    "registration_date": "1996-01-19",
    "its_title_status_label": "Torrens Title",
    "has_stratum": false,
    "stratum_level_label": null,
    "plan_lot_area": 651.4,
    "plan_lot_area_units": "m2"
  }
}
```

**Survey mark feature:**
```json
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [easting, northing]
  },
  "properties": {
    "feature_type": "survey_mark",
    "mark_number": 12345,
    "mark_type": "PM",
    "mark_status": "EX",
    "mark_symbol_label": "Permanent Mark",
    "gda_class": "B",
    "gda_date": "2018-04-12",
    "gda_pos_uncertainty_label": "0.01",
    "ahd_height": 34.21,
    "ahd_height_label": "34.210",
    "ahd_class": "LC",
    "mga_easting_label": "334521.456 E",
    "mga_northing_label": "6243871.234 N",
    "retrieved_at": "2026-03-20T09:14:00"
  }
}
```

**Top-level FeatureCollection:**
```json
{
  "type": "FeatureCollection",
  "search": {
    "address_input": "87 Bunarba Rd Gymea Bay",
    "address_resolved": "87 BUNARBA ROAD GYMEA BAY NSW 2227",
    "suburb": "GYMEA BAY",
    "lga": "SUTHERLAND SHIRE",
    "parish": "WORONORA",
    "county": "CUMBERLAND",
    "radius_m": 200,
    "subject_lot": "102//DP574558",
    "lot_count": 14,
    "plan_count": 8,
    "mark_count": 3
  },
  "features": [...]
}
```

---

## API Endpoints — server.py

```
GET  /health
     Response: {"status": "ok"}
     Purpose:  C# add-in checks this on startup to confirm the service is running.

GET  /search?address={address}&radius_m={radius_m}
     Default:  radius_m=200
     Response: GeoJSON FeatureCollection (see above)
     Purpose:  Main endpoint. Returns all lots, plans, marks for the address.

GET  /plan/{plan_label}
     Example:  /plan/DP574558
     Response: Single Plan object as JSON
     Purpose:  Detail lookup — C# add-in can call this when user clicks a lot in AutoCAD.
```

`server.py` contains endpoint definitions only. No API calls, no data processing. All logic lives in `search.py`, `export.py`, and `drive.py`.

---

## Google Drive Integration — drive.py

Port the logic from Stephen's `MLS_Plan_Searcher` project (`drive_plans_fetch.py`). Function signature:

```python
def download_plans(result: SearchResult, dest_folder: Path) -> SearchResult:
    """
    For each Plan in result.plans, search Google Drive for a matching PDF or image.
    Download the best match to dest_folder/plans/.
    Return the same SearchResult with local_file set on each Plan that was found.
    Downloads both surveyed and compiled plans.
    """
```

Authentication: OAuth 2.0. `credentials.json` must be present in the project root (never committed to git — add to `.gitignore`). `token.json` is created on first run and cached.

Output folder structure:

```
output/
  {sanitised-address}-{YYYY-MM-DD}/
    summary.json          ← key SearchResult fields as plain JSON (not GeoJSON)
    search_result.geojson ← full GeoJSON FeatureCollection
    cre_map.png           ← raster map image from CRE MapServer export
    plans/
      DP574558.pdf
      DP532685.tiff
      ...
```

---

## CRE Map Image — export.py

The CRE MapServer can export a raster PNG of the cadastral map for any bounding box:

```
GET https://maps.six.nsw.gov.au/arcgis/rest/services/sixmaps/CRE/MapServer/export
    ?bbox={xmin},{ymin},{xmax},{ymax}
    &bboxSR=7856
    &size=1200,900
    &format=png
    &f=image
```

Calculate the bounding box from the extents of all `result.nearby_lots` geometries plus a 10% buffer. Save the PNG to the output folder and set `result.cre_map_image`.

Note: this is a raster rendering of NSW's own cadastral map — it is not the same as the formal LRS CRE report. It is a quick visual reference only.

---

## Build Order

Work strictly in this order. Do not start a step until the previous one is tested against a real address.

| Step | File | Task |
|---|---|---|
| 1 | `models.py` | Already written — read it, understand every field before proceeding |
| 2 | `api/address.py` | Refactor to return `Address`; add 4 admin boundary calls for suburb/LGA/parish/county |
| 3 | `api/lot.py` | Refactor to return `list[Lot]`; enable `returnGeometry=true`; capture all fields; decode coded values |
| 4 | `api/survey_marks.py` | Refactor to return `list[SurveyMark]`; capture all fields; set `retrieved_at` |
| 5 | `api/plan.py` | Refactor to return `Plan` object |
| 6 | `api/cre.py` | Delete this file — title status (`ITSTitleStatus`) and area (`PlanLotArea`) are already returned by `[LOT]` and decoded in Step 3 |
| 7 | `search.py` | Build `search(address, radius_m) → SearchResult`; assemble all objects; deduplicate plans |
| 8 | `export.py` | Build `to_geojson()` and `fetch_cre_map_image()` |
| 9 | `drive.py` | Port Google Drive logic; implement `download_plans()` |
| 10 | `server.py` | FastAPI wrapper — 3 endpoints, no business logic |

After Step 7, test from a Python shell:
```python
from search import search
result = search("87 Bunarba Rd Gymea Bay", radius_m=200)
print(result.address.suburb)          # "GYMEA BAY"
print(result.address.lga)             # "SUTHERLAND SHIRE"
print(result.subject_lot.plan_label)  # "DP574558"
print(len(result.nearby_lots))        # e.g. 14
print(len(result.survey_marks))       # e.g. 3
print(result.survey_marks[0].gda_class)       # "B"
print(result.survey_marks[0].retrieved_at)    # datetime object
```

After Step 10, test every endpoint at `http://localhost:8000/docs` — FastAPI generates interactive documentation automatically.

---

## Running the Service

```bash
# Install dependencies
pip install -r requirements.txt

# Run in development (auto-reloads on code changes)
uvicorn server:app --reload --port 8000

# Run in production
uvicorn server:app --port 8000
```

The C# add-in should call `GET http://localhost:8000/health` on startup. If it fails, show a warning: "MLS Search Service is not running. Please start the service before searching."

---

## Dependencies — requirements.txt

```
requests
fastapi
uvicorn
google-api-python-client
google-auth-oauthlib
google-auth-httplib2
```

---

## .gitignore — required entries

```
credentials.json
token.json
output/
__pycache__/
*.pyc
venv/
```

---

## What the C# AutoCAD Add-in Needs to Handle

Outside the scope of this Python project but documented here for alignment:

- Call `/health` on add-in load — warn user if service is not running
- Call `/search` with address and radius from user input
- Parse GeoJSON FeatureCollection response
- For each `feature_type == "lot"`:
  - Draw closed polyline from polygon coordinates
  - Colour by: `is_surveyed == false` → blue (compiled); `is_surveyed == true` → red shaded by `registration_date` (dark = recent, light = old)
  - `is_subject == true` → add pin/marker symbol at centroid
- For each `feature_type == "survey_mark"`:
  - Insert block/point at `[easting, northing]` coordinates
  - Label with `mark_number` and `gda_class`
  - Use `mga_easting_label` and `mga_northing_label` for coordinate annotation if needed
- Zoom to extents of all drawn features

---

---

## Example Client: PNG Drawing Script — draw.py

This is a separate project that **consumes** the API — it does not live inside the service codebase. It calls the `/search` endpoint like any other client and draws the result as a PNG image.

This is a deliberate exercise in separation of concerns. `draw.py` does not import anything from the service. It only speaks HTTP and GeoJSON.

**Additional dependencies (for this script only):**
```
shapely
matplotlib
```

**What it does:**
1. Calls `GET http://localhost:8000/search?address={address}&radius_m={radius_m}`
2. Parses the GeoJSON FeatureCollection response
3. Draws the result using `shapely` (geometry handling) and `matplotlib` (rendering)
4. Saves a PNG to the current directory or a specified output path

**Drawing rules:**

| Feature | Rule |
|---|---|
| Compiled lot (`is_surveyed == false`) | Blue fill, thin border |
| Surveyed lot (`is_surveyed == true`) | Red fill, shaded by `registration_date` — dark red = recent, light red/pink = old |
| Subject lot (`is_subject == true`) | Add a pin/marker symbol at the polygon centroid |
| Survey mark | Point symbol at coordinates, labelled with `mark_number` and `gda_class` |
| No `registration_date` | Grey fill (unknown age) |

**Age shading:** calculate the year range across all surveyed lots in the result, then interpolate each lot's colour between light pink (oldest) and dark red (newest). Use `matplotlib.colors.Normalize` and a red colormap.

**Function signature:**
```python
def draw(geojson: dict, output_path: str = "search_plan.png") -> None:
    """
    Takes a GeoJSON FeatureCollection from the /search endpoint.
    Draws all lots and survey marks and saves as PNG.
    """
```

**Usage:**
```python
import requests
from draw import draw

response = requests.get(
    "http://localhost:8000/search",
    params={"address": "87 Bunarba Rd Gymea Bay", "radius_m": 200}
)
draw(response.json(), output_path="search_plan.png")
```

---

## Future Development Ideas

The following are potential extensions to this project. They are not part of the current scope but are listed here as possible directions.

**Enhancements to the service:**
- Caching — store recent `SearchResult` objects so repeated searches for the same address don't re-call all APIs
- Async API calls — use `asyncio` / `httpx` to call NSW Spatial Services endpoints in parallel, reducing response time significantly
- Roads layer — add NSW road centrelines/boundaries from Spatial Services to the GeoJSON output for context
- Confidence scoring — flag lots where `is_surveyed` may be unreliable (older DPs) so the C# add-in can display a warning

**New endpoints:**
- `GET /mark/{mark_number}` — full SCIMS data for a single survey mark
- `GET /lot/{plan_label}/{lot_number}` — full lot detail including CRE
- `POST /batch` — accept a list of addresses and return results for all of them

**New clients:**
- Web viewer — a simple browser-based map using Leaflet.js or MapLibre that calls the API and displays results interactively; no AutoCAD required
- PDF summary report — generate a formatted PDF proposal search report using `reportlab` or `weasyprint`; include the PNG drawing, mark table, plan list, and lot summary
- QGIS plugin — QGIS is open-source GIS software; a plugin could call the API and load results directly as vector layers

**Broader skills to build:**
- Unit testing with `pytest` — write tests for each `api/` module using mocked HTTP responses so the code can be tested without live API calls
- CI/CD — set up GitHub Actions to run tests automatically on every commit
- Docker — package the service as a Docker container so it can be deployed anywhere, not just on Stephen's machine
- Database — store search history in a local SQLite database using `SQLAlchemy`; useful for auditing and re-running past searches
- Authentication — add an API key to the service so it can be exposed on a local network without being open to everyone

---

*Specification: MLS Spatial Search Service | Version: 02 | Date: 20/03/2026 | Developer: James Mitchell*
