# MLS Spatial Search Service — Build Specification

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

```

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