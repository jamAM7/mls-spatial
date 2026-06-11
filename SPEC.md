# MLS Spatial Search Service — Build Specification

**Project:** mls-spatial
**Developer:** James Mitchell — Software Internship, Mitchell Land Surveyors Pty Ltd
**Purpose:** A local HTTP API service that, given a street address (or survey mark reference, folio identifier, or drawn geometry), returns cadastral lots, survey plans, survey marks, and surface levels — structured for consumption by the MLS web viewer, AutoCAD add-in, and MLSSurveyManager.

*Specification Version: 05 | Updated: June 2026*

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
├── PDF report     reportlab A4 search report     ~ basic version working
│                                                   TODO: refactor to accept SearchResult directly
│                                                   TODO: add bearing/distance column to marks table
│                                                   TODO: surveyor review of field accuracy
├── Web viewer     Leaflet.js browser map         Week 5
└── AutoCAD add-in C# add-in draws in Civil 3D   Week 6

PHASE 3 — Quality and Robustness                  STATUS: IN PROGRESS
├── pytest         Mocked HTTP unit tests         ✓ first version written
├── GitHub Actions Run tests on every commit      TODO
└── Async calls    httpx + asyncio parallel       TODO

PHASE 4 — Expand the Service                      STATUS: IN PROGRESS
├── Dual radius    marks_radius_m parameter       ✓ (Bug #1 fixed)
├── /full-search   Full pipeline endpoint         ✓
├── Surface levels AHD spot heights               ✓ (address + per mark)
├── /mark endpoint Fetch single mark by type+no  ✓ (server.py)
├── /mark/sketch   SCIMS sketch PDF download      ~ endpoint wired, download_sketch() TODO
├── SQLite history Store all searches locally     TODO
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

All bugs fixed.

| Issue | Description | Files affected | Status |
|---|---|---|---|
| **#1** | No separate radius for survey marks — `marks_radius_m` missing | `server.py`, `search.py`, `export.py` | ✓ Fixed |
| **#2** | GeoJSON output missing mark fields: `gda_loc_uncertainty_label`, `mga_csf_2020`, `mga_csf_2020_label` | `export.py` | ✓ Fixed |
| **#3** | `subject_lot` label drops section number — `1//DP45424` instead of `1/A/DP45424` | `export.py`, `server.py`, `spatialsearch.py` | ✓ Fixed |
| **#4** | `search_plan.png` not generated in `/full-search` pipeline | `server.py` | ✓ Fixed — added `draw_png()` call |
| **#5** | `summary.json` never written to output folder | `server.py` | ✓ Fixed — written before `generate_report()` |
| **#6** | `generate_report()` crashes with `FileNotFoundError` — called before `summary.json` exists | `server.py` | ✓ Fixed — ordering corrected |
| **#7** | `report_path` referenced in `summary` dict before it is defined | `server.py` | ✓ Fixed — moved to post-report assignment |
| **#8** | `survey_marks.py` crashes on Windows with `OSError` for epoch 0 dates | `api/survey_marks.py` | ✓ Fixed — `_epoch_ms_to_date()` helper added |

---

## Build Queue

All bugs resolved. Remaining work in order:

**Next up**
1. `service/history.py` — SQLite search history (new file)
2. `server.py` — add `/history` endpoint
3. `api/survey_marks.py` — `download_sketch()` (needs API research with surveyor first)
4. `report.py` — add bearing/distance to marks table; refactor to accept SearchResult directly
5. `api/lot.py` — add `get_lot_by_folio()`
6. `search.py` — wire folio search mode

**Engineering hygiene (can be done alongside)**
7. Convert all `api/` modules from `requests` to `httpx` (async)
8. Add `Dockerfile` + `docker-compose.yml`
9. Add GitHub Actions `test.yml`
10. Update README

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
│   ├── server.py           ✓ /health, /search, /cre_map, /plan, /full-search, /mark, /mark/sketch
│   │                         TODO: /history endpoint
│   ├── search.py           ✓ address search, marks_radius_m supported
│   │                         TODO: folio + geometry search modes, async conversion
│   ├── export.py           ✓ to_geojson() — all fields, search_mode, surface_level_ahd
│   │                         TODO: convert fetch_cre_map_image to httpx
│   ├── drive.py            ✓ Google Drive plan download
│   ├── report.py           ~ Basic PDF working (cover, CRE map, lots, marks, plans)
│   │                         TODO: refactor to accept SearchResult directly
│   │                         TODO: add bearing/distance column to marks table
│   ├── history.py          ✓ built — SQLite search history
│   ├── models.py           ✓ All dataclasses — search_mode, surface_level_ahd fields added
│   ├── config.py           ✓ Constants and API base URLs
│   ├── utils.py            ✓ sanitise_address, coordinate helpers, to_web_mercator()
│   └── api/
│       ├── address.py      ✓ Geocoding + admin boundaries + surface_level_ahd
│       │                     TODO: async conversion
│       ├── lot.py          ✓ Lot polygons + attributes
│       │                     TODO: get_lot_by_folio(), async conversion
│       ├── plan.py         ✓ Plan metadata
│       │                     TODO: async conversion
│       └── survey_marks.py ✓ Spatial query, get_mark_by_reference(), surface_level_ahd per mark
│                             TODO: download_sketch() (might need API research with surveyor)
│                             TODO: async conversion
├── clients/
│   ├── draw.py             ✓ PNG drawing script (consumes /search endpoint)
│   └── SPEC.md             ✓ Client-side integration notes
├── console/
│   ├── run.py              ✓ Interactive CLI entry point
│   └── search_console.py
├── tests/
│   ├── test_address.py     ✓ first version
│   ├── test_lot.py         ✓ first version
│   ├── test_plan.py        ✓ first version
│   └── test_survey_marks.py ✓ first version
├── samples/                Original proof-of-concept scripts — reference only
├── output/                 Local search output (gitignored)
├── Dockerfile              ✓ 
├── docker-compose.yml      ✓ 
├── .github/
│   └── workflows/
│       └── test.yml        Run pytest on every push
├── requirements.txt        ✓ 
├── .gitignore              ✓ 
├── README.md               ✓ 
├── SPEC.md                 ✓ This file
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
There is only address implemented in search.py currently

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

*Specification: MLS Spatial Search Service | Version 05 | June 2026 | Developer: James Mitchell*