# py-spatialservices-starter

A Python console app for querying NSW Spatial Services APIs to retrieve 
address, lot, and survey mark information.

## Requirements
- Python 3.x

## Setup

1. Clone the repository
```
git clone https://github.com/jamAM7/py-spatialservices-starter.git
```

2. Create and activate a virtual environment
```
python -m venv venv
```
Windows:
```
venv\Scripts\activate
```
Mac/Linux:
```
source venv/bin/activate
```

3. Install dependencies
```
pip install -r requirements.txt
```

## Usage

Run the main script:
```
python spatialsearch.py
```

Enter a full address when prompted, for example:
```
1 PACIFIC HIGHWAY NORTH SYDNEY
```

The tool will return:
- Address coordinates
- Lot and plan number
- Nearby survey marks within 500m

Enter 'x' to exit.

## Data Sources
- NSW Spatial Services: https://portal.spatial.nsw.gov.au


## Running the Service

### Navigate to the project directory and activate the virtual environment:

cd path/to/pyconsole

venv\Scripts\activate

### Start the FastAPI server:

uvicorn server:app --reload --port 8000

The service will be available at `http://localhost:8000`

Interactive API documentation is available at `http://localhost:8000/docs`

The server runs until you press `Ctrl+C`. Use `--reload` during development 
to automatically restart when code changes are saved.

Example search:

http://localhost:8000/search?address=483 GEORGE STREET SYDNEY&radius_m=150

## Endpoints

- `GET /health` — confirms the service is running
- `GET /search?address={address}&radius_m={radius_m}` — returns GeoJSON FeatureCollection for an address (default radius 200m)
- `GET /plan/{plan_label}` — returns metadata for a single plan e.g. `/plan/DP574558`