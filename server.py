"""
server.py — MLS Spatial Search Service
FastAPI endpoint definitions only. No business logic here.
All logic lives in search.py, export.py, and drive.py.

Run with:
    uvicorn server:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from search import search
from export import to_geojson
from api.plan import get_plan_info
from dataclasses import asdict

app = FastAPI(
    title="MLS Spatial Search Service",
    description="Queries NSW Spatial Services APIs to return cadastral lots, survey plans, and survey marks.",
    version="1.0.0",
)


@app.get("/health")
def health():
    """C# add-in calls this on startup to confirm the service is running."""
    return {"status": "ok"}


@app.get("/search")
def search_endpoint(
    address: str = Query(..., description="Full street address e.g. '483 GEORGE STREET SYDNEY'"),
    radius_m: int = Query(200, description="Search radius in metres"),
):
    """
    Main endpoint. Returns all lots, plans, and survey marks near the address as GeoJSON.
    """
    result = search(address, radius_m)

    if result is None:
        raise HTTPException(status_code=404, detail="Address not found")

    return JSONResponse(content=to_geojson(result))


@app.get("/plan/{plan_label}")
def plan_endpoint(plan_label: str):
    """
    Detail lookup for a single plan.
    C# add-in calls this when the user clicks a lot in AutoCAD.
    """
    plan = get_plan_info(plan_label)

    if plan is None:
        raise HTTPException(status_code=404, detail=f"Plan {plan_label} not found")

    return JSONResponse(content=asdict(plan))