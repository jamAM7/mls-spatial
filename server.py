"""
server.py — MLS Spatial Search Service
FastAPI endpoint definitions only. No business logic here.
All logic lives in search.py, export.py, and drive.py.

Run with:
    uvicorn server:app --reload --port 8000
"""

import tempfile
from pathlib import Path
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse

from service.search import search
from service.export import to_geojson, fetch_cre_map_image
from service.api.plan import get_plan_info

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
    marks_radius_m: int | None = Query(None, description="Search radius for survey marks in metres. Defaults to radius_m when omitted."),
):
    """
    Main endpoint. Returns all lots, plans, and survey marks near the address as GeoJSON.
    """
    result = search(address, radius_m, marks_radius_m=marks_radius_m)

    if result is None:
        raise HTTPException(status_code=404, detail="Address not found")

    return JSONResponse(content=to_geojson(result))


@app.get("/cre_map")
def cre_map_endpoint(
    address: str = Query(..., description="Full street address e.g. '483 GEORGE STREET SYDNEY'"),
    radius_m: int = Query(200, description="Search radius in metres"),
    map_radius_m: int = Query(500, description="Map image radius in metres — controls how much area the PNG covers"),
):
    """
    Returns a PNG raster image of the CRE cadastral map for the given address.
    """
    result = search(address, radius_m)

    if result is None:
        raise HTTPException(status_code=404, detail="Address not found")

    tmp = tempfile.mkdtemp()
    image_path = fetch_cre_map_image(result, Path(tmp), map_radius_m=map_radius_m)

    if not image_path:
        raise HTTPException(status_code=500, detail="CRE map generation failed")

    return FileResponse(image_path, media_type="image/png", filename="cre_map.png")


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
