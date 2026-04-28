# MLS Spatial Search

NSW cadastral search tool — queries Spatial Services APIs to return lots, survey plans and survey marks for a given address. Generates cadastral drawings, CRE map images and downloads plan documents from Google Drive.

## Requirements
- Python 3.x
- `credentials.json` — Google OAuth credentials (provided separately, never committed to git)
- `token.json` — created automatically on first run after authenticating with Google

## Setup

1. Clone the repository
```
git clone https://github.com/jamAM7/mls-spatial.git
cd mls-spatial
```

2. Place `credentials.json` and `token.json` in the project root (obtain from project administrator)

3. Create and activate a virtual environment

Windows:
```
python -m venv venv
venv\Scripts\activate
```
Mac/Linux:
```
python -m venv venv
source venv/bin/activate
```

4. Install dependencies
```
pip install -r requirements.txt
```

## Usage

Run the console app:
```
python console/run.py
```

Enter a full NSW address when prompted:
```
483 GEORGE STREET SYDNEY
```

Enter a search radius in metres (default 200m), then choose output:
```
1. Drawn PNG only           (~15 seconds)
2. CRE map only             (~20 seconds)
3. Full output              (~3 minutes - includes plan downloads)
4. Drawn PNG + CRE map      (~30 seconds)
```

Results are saved to `output/{address}-{date}/` containing:
- `search_result.geojson` — full GeoJSON FeatureCollection
- `summary.json` — key search result fields
- `search_plan.png` — colour coded cadastral drawing (options 1, 3, 4)
- `cre_map.png` — CRE raster map image (options 2, 3, 4)
- `plans/` — downloaded plan PDFs from Google Drive (option 3)

## Running the FastAPI Service (optional)

For programmatic access or the AutoCAD add-in:
```
uvicorn service.server:app --port 8000
```

Interactive API documentation: `http://localhost:8000/docs`

### Endpoints
- `GET /health` — confirms the service is running
- `GET /search?address={address}&radius_m={radius_m}` — returns GeoJSON FeatureCollection
- `GET /cre_map?address={address}&radius_m={radius_m}` — returns CRE map PNG
- `GET /plan/{plan_label}` — returns plan metadata e.g. `/plan/DP574558`

## Data Sources
- NSW Spatial Services: https://portal.spatial.nsw.gov.au
- NSW SIX Maps: https://maps.six.nsw.gov.au
- Google Drive: plan PDF storage (requires credentials.json)