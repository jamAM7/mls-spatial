# MLS Spatial — Project Status

*Last updated: June 2026*

---

## Open Bugs

| # | Where | Issue |
|---|---|---|
| #1 | `server.py`, `search.py` | `marks_radius_m` param missing — marks always use same radius as lots |
| #2 | `export.py` | GeoJSON mark output missing `gda_loc_uncertainty_label`, `mga_csf_2020`, `mga_csf_2020_label` |
| #3 | `export.py:70`, `server.py:106`, `server.py:150`, `spatialsearch.py:43` | Subject lot label drops section number — `1//DP45424` instead of `1/A/DP45424` |

### Other known issues
- `search.py` — full-search pipeline not wired (no plan downloads, no SCIMS sketch download, no elevation calls)
- `search.py` — all NSW API calls are synchronous (`requests`); needs async conversion (`httpx` + `asyncio`)
- `search.py` — dead commented-out code lines 36–51, remove ----------------DONE
- `server.py` — no `/full-search`, `/mark`, `/history` endpoints
- `server.py` — `search()` called synchronously inside async FastAPI
- `export.py` — `fetch_cre_map_image` uses `requests` (sync), has stray `print()`, `output_path` param unused
- `export.py` — `search` block missing `search_mode`, `surface_level_ahd`, `marks_radius_m`
- `spatialsearch.py` — missing `if __name__ == "__main__"` guard
- `tests/test_survey_marks.py` — broken imports, no tests actually run
- `report.py` — reads from flat `summary.json` + `search_result.geojson` files; needs to accept `SearchResult` directly and integrate into pipeline properly. Needs surveyor review for field accuracy.

---

## Design Rules

- `server.py` — endpoint definitions only. No business logic, no API calls.
- `api/` modules and `search.py` — no `print()` statements. Print only in CLI entry points or `__main__` blocks.
- `models.py` — single source of truth for all dataclasses. No imports from other project files.
- All NSW API calls use `httpx` (async). No `requests` anywhere in the service.
- All tests use mocked HTTP (`pytest-httpx`). No live API calls in tests.
- Search mode priority: `geometry` > `folio` > `address`. At least one must be supplied.
- `marks_radius_m` defaults to `radius_m` if not supplied.
- EPSG/zone derived from real WGS84 longitude (two-pass address resolution already implemented).
- `[ELEV]` API requires Web Mercator (EPSG:3857) input — convert with `to_web_mercator()` in `utils.py`.
- Fixture data for tests lives in `tests/fixtures/` as JSON files.

---

## System Structure

```
mls-spatial/
├── service/
│   ├── models.py           ✓ done — all dataclasses, single source of truth
│   ├── config.py           ✓ done — constants, API base URLs, EPSG_CODES
│   ├── utils.py            ✓ done — sanitise_address, zone/EPSG helpers
│   │                               TODO: add to_web_mercator() for [ELEV] calls
│   ├── server.py           ~ partial — /health, /search, /cre_map, /plan work
│   │                               TODO: add marks_radius_m to /search
│   │                               TODO: add /full-search, /mark, /mark/sketch, /history
│   ├── search.py           ~ partial — main pipeline runs, plans fetched in parallel
│   │                               TODO: marks_radius_m param
│   │                               TODO: surface level calls (address + each mark)
│   │                               TODO: folio and geometry search modes
│   │                               TODO: convert to async (httpx)
│   │                               TODO: clean dead commented code
│   ├── export.py           ~ partial — GeoJSON output works
│   │                               TODO: fix bug #2 (missing mark fields)
│   │                               TODO: fix bug #3 (subject lot label)
│   │                               TODO: add search_mode, surface_level_ahd, marks_radius_m to search block
│   │                               TODO: convert fetch_cre_map_image to httpx, remove print()
│   ├── history.py          ✗ not built — SQLite search history
│   ├── report.py           ~ exists — generates PDF from summary.json + geojson files
│   │                               TODO: refactor to accept SearchResult directly
│   │                               TODO: surveyor review of field accuracy
│   │                               TODO: add bearing/distance column to marks table
│   └── api/
│       ├── address.py      ~ partial — geocoding + admin boundaries work
│       │                               TODO: add surface_level_ahd fetch ([ELEV])
│       │                               TODO: convert to async
│       ├── lot.py          ~ partial — spatial lot query works
│       │                               TODO: add get_lot_by_folio() for folio search
│       │                               TODO: convert to async
│       ├── plan.py         ✓ works
│       │                               TODO: convert to async
│       └── survey_marks.py ~ partial — spatial mark query works
│                                       TODO: add get_mark_by_reference() (attribute query)
│                                       TODO: add download_sketch() for SCIMS PDFs
│                                       TODO: add surface_level_ahd fetch per mark
│                                       TODO: convert to async
│
├── clients/
│   ├── draw.py             ~ exists — draws PNG from /search output. Needs surveyor review.
│   └── SPEC.md             ✓ done
│
├── console/
│   ├── run.py              ✓ done
│   └── search_console.py   ✓ done
│
├── tests/
│   ├── test_address.py     ✗ not written
│   ├── test_lot.py         ✗ not written
│   ├── test_plan.py        ✗ not written
│   └── test_survey_marks.py ✗ broken imports, effectively empty
│
├── Dockerfile              ✗ not built
├── docker-compose.yml      ✗ not built
├── .github/workflows/
│   └── test.yml            ✗ not built
└── README.md               ✗ needs update
```

**Downstream projects (not yet started):**
```
mls-infotrack/              ✗ not started — InfoTrack API wrapper (Week 2)
MLSSurveyManager/           ~ exists (C#) — InfoTrack integration to be added (Week 3)
mls-assistant/              ~ exists (HTML) — RAG upgrade (Week 4)
mls-spatial-viewer/         ✗ not started — Leaflet web map (Week 5)
AutoCAD add-in/             ✗ not started — C# Civil 3D add-in (Week 6)
```

---

## Build Queue

Fix bugs first, then new features, then hygiene. Rough order:

**Bug fixes (do first)**
1. Bug #3 — fix subject lot label (4-line find/replace in export.py, server.py, spatialsearch.py)
2. Bug #2 — add missing mark fields to export.py
3. Bug #1 — add `marks_radius_m` param through server.py → search.py

**New features — service layer**
4. `utils.py` — add `to_web_mercator()`
5. `api/address.py` — add surface level AHD fetch at address point
6. `api/survey_marks.py` — add surface level fetch per mark (parallel)
7. `api/survey_marks.py` — add `get_mark_by_reference()` (single mark attribute query)
8. `api/survey_marks.py` — add `download_sketch()` (SCIMS PDF download)
9. `api/lot.py` — add `get_lot_by_folio()`
10. `search.py` — wire folio search mode
11. `search.py` — wire surface level calls
12. `service/history.py` — SQLite search history (new file)
13. `server.py` — add `/mark/{type}/{number}` endpoint
14. `server.py` — add `/mark/{type}/{number}/sketch` endpoint
15. `server.py` — add `/full-search` endpoint
16. `server.py` — add `/history` endpoint
17. `export.py` — add search_mode, surface_level_ahd, marks_radius_m to search block
18. `report.py` — refactor to accept SearchResult directly, add bearing/distance to marks

**Engineering hygiene (can be done alongside features)**
19. Convert all `api/` modules from `requests` to `httpx` (async)
20. Rewrite all tests with mocked HTTP (`pytest-httpx`)
21. Add `Dockerfile` + `docker-compose.yml`
22. Add GitHub Actions `test.yml`
23. Clean dead code from `search.py`
24. Fix `spatialsearch.py` `__main__` guard
25. Update README


































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
