![CI](https://github.com/jamAM7/mls-spatial/actions/workflows/ci.yml/badge.svg)

# MLS Spatial Search

NSW cadastral search tool — queries Spatial Services APIs to return lots, survey plans and survey marks for a given address. Generates cadastral drawings, CRE map images and downloads plan documents from Google Drive.

<img width="800" height="450" alt="Image" src="https://github.com/user-attachments/assets/b207a83e-a027-48a0-a022-bf34d3fe87e1" />

## Requirements
- Python 3.11
- `credentials.json` — Google OAuth credentials (provided separately, never committed to git)
- `token.json` — created automatically on first run after authenticating with Google

## Setup

1. Clone the repository
```
git clone https://github.com/jamAM7/mls-spatial.git
cd mls-spatial
```

2. Place `credentials.json` in the project root (obtain from project administrator)

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

5. Authenticate with Google Drive (first time only)

Run the console app once:
```
python console/run.py
```

A browser window will open asking you to authorise Google Drive access. Complete it and `token.json` will be created in the project root. You only need to do this once — the token is reused and auto-refreshed on every subsequent run.

## Running with Docker (recommended)

Docker runs the FastAPI service in an isolated container with no local Python environment required. The console app still runs locally against the service over HTTP.

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- `credentials.json` and `token.json` in the project root

`token.json` must exist before starting Docker — the container cannot run the interactive browser auth flow. Complete step 5 of [Setup](#setup) first if you haven't already.

### First run

Create an empty database file so Docker mounts it correctly:
```
touch mls_spatial.db
```

Then start the service:
```
docker compose up --build
```

The `--build` flag builds the image from the Dockerfile. The first run takes a minute or two to download the base image and install dependencies — subsequent starts are fast.

The FastAPI service will be available at `http://localhost:8000`.

### Day-to-day usage

Start the service:
```
docker compose up
```

Once you see this in the terminal, the service is running:
```
mls-spatial-mls-spatial-1  | INFO:     Application startup complete.
mls-spatial-mls-spatial-1  | INFO:     Uvicorn running on http://0.0.0.0:8000
```

The FastAPI service is now running at `http://localhost:8000`. You can verify it's working by opening `http://localhost:8000/docs` in your browser — this shows the interactive API documentation where you can test endpoints directly.

To run the console app, open a separate terminal and run:
```
python console/run.py
```

To start the service in the background (no terminal output):
```
docker compose up -d
```

To stop the service:
```
docker compose down
```

Rebuild after code changes:
```
docker compose up --build
```

### What gets mounted

The container shares these paths with your local machine — no rebuild needed when these files change:

| Host path | Container path | Purpose |
|---|---|---|
| `./credentials.json` | `/app/credentials.json` | Google OAuth credentials |
| `./token.json` | `/app/token.json` | Google OAuth token (auto-refreshed) |
| `./output/` | `/app/output/` | Search results and generated files |
| `./mls_spatial.db` | `/app/mls_spatial.db` | Search history database |

## Usage

With either the local server or Docker running, start the console app:
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

## FastAPI Service

For programmatic access or the AutoCAD add-in, the service can also be run locally without Docker:
```
uvicorn service.server:app --port 8000
```

Interactive API documentation: `http://localhost:8000/docs`

### Endpoints
- `GET /health` — confirms the service is running
- `GET /search?address={address}&radius_m={radius_m}&marks_radius_m={marks_radius_m}` — returns GeoJSON FeatureCollection
- `GET /full-search?address={address}&radius_m={radius_m}&output_folder={path}` — full pipeline: search, CRE map, plan downloads, PDF report
- `GET /cre_map?address={address}&radius_m={radius_m}` — returns CRE map PNG
- `GET /plan/{plan_label}` — returns plan metadata e.g. `/plan/DP574558`
- `GET /mark/{mark_type}/{mark_number}` — returns survey mark metadata e.g. `/mark/PM/12345`
- `GET /mark/{mark_type}/{mark_number}/sketch` — returns mark sketch PDF

## Testing

Run the full test suite:
```
pytest tests/ -v
```

To save output to a file:
```
pytest tests/ -v > test_results.txt 2>&1
```

Tests use mocked HTTP via the `responses` library — no internet connection or running server required. All NSW Spatial Services API calls are intercepted using fixture JSON files in `tests/fixtures/`.

CI runs automatically on every push via GitHub Actions.

## Data Sources
- NSW Spatial Services: https://portal.spatial.nsw.gov.au
- NSW SIX Maps: https://maps.six.nsw.gov.au
- Google Drive: plan PDF storage (requires credentials.json)
