"""
server.py — MLS Spatial Search Service
FastAPI endpoint definitions only. No business logic here.
All logic lives in search.py, export.py, and drive.py.

Run with:
    uvicorn server:app --reload --port 8000
"""

import json
import tempfile
from datetime import date, datetime
from pathlib import Path
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse

from service.search import search
from service.export import to_geojson, fetch_cre_map_image
from service.api.plan import get_plan_info
from service.api.survey_marks import get_survey_mark_info, get_mark_by_reference, download_sketch
from service.drive import download_plans
from service.report import generate_report
from service.utils import lot_label

def _asdict_json(obj) -> dict:
    """asdict() with date/datetime values converted to isoformat strings."""
    def _convert(v):
        if isinstance(v, datetime):  # datetime before date — datetime is a subclass of date
            return v.isoformat()
        if isinstance(v, date):
            return v.isoformat()
        if isinstance(v, dict):
            return {k: _convert(val) for k, val in v.items()}
        if isinstance(v, list):
            return [_convert(i) for i in v]
        return v
    return {k: _convert(v) for k, v in asdict(obj).items()}


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


@app.get("/full-search")
def full_search_endpoint(
    address: str = Query(..., description="Full street address e.g. '483 GEORGE STREET SYDNEY'"),
    radius_m: int = Query(200, description="Search radius in metres"),
    marks_radius_m: int | None = Query(None, description="Search radius for survey marks in metres. Defaults to radius_m when omitted."),
    output_folder: str = Query(..., description="Absolute path to the folder where output files will be written"),
):
    """
    Full search pipeline: search, CRE map, plan downloads, and PDF report.
    Writes all output to output_folder and returns a flat summary dict.
    """
    result = search(address, radius_m, marks_radius_m=marks_radius_m)

    if result is None:
        raise HTTPException(status_code=404, detail="Address not found")

    folder = Path(output_folder)
    folder.mkdir(parents=True, exist_ok=True)

    geojson = to_geojson(result)
    (folder / "search_result.geojson").write_text(json.dumps(geojson, indent=2))

    result.cre_map_image = fetch_cre_map_image(result, folder, map_radius_m=radius_m)
    result = download_plans(result, folder)
    report_path = generate_report(folder)

    crs_label = f"{result.datum} MGA Zone {result.mga_zone} (EPSG:{result.epsg})"
    summary = {
        "address_input":     result.address.input_string,
        "address_resolved":  result.address.resolved_string,
        "suburb":            result.address.suburb,
        "lga":               result.address.lga,
        "parish":            result.address.parish,
        "county":            result.address.county,
        "datum":             result.datum,
        "epsg":              result.epsg,
        "coordinate_system": crs_label,
        "search_radius_m":   result.search_radius_m,
        "marks_radius_m":    result.marks_radius_m,
        "subject_lot":       lot_label(result.subject_lot),
        "lot_count":         len(result.nearby_lots),
        "plan_count":        len(result.plans),
        "mark_count":        len(result.survey_marks),
        "report_path":       str(report_path),
        "output_folder":     str(folder),
    }
    return JSONResponse(content=summary)


@app.get("/plan/{plan_label}")
def plan_endpoint(plan_label: str):
    """
    Detail lookup for a single plan.
    C# add-in calls this when the user clicks a lot in AutoCAD.
    """
    plan = get_plan_info(plan_label)

    if plan is None:
        raise HTTPException(status_code=404, detail=f"Plan {plan_label} not found")

    return JSONResponse(content=_asdict_json(plan))


@app.get("/mark/{mark_type}/{mark_number}")
def mark_endpoint(mark_type: str, mark_number: str):
    """
    Detail lookup for a single survey mark by type and number.
    """
    mark = get_mark_by_reference(mark_type, mark_number)

    if mark is None:
        raise HTTPException(status_code=404, detail=f"Mark {mark_type} {mark_number} not found")

    return JSONResponse(content=_asdict_json(mark))


@app.get("/mark/{mark_type}/{mark_number}/sketch")
def mark_sketch_endpoint(mark_type: str, mark_number: str):
    """
    Returns the sketch PDF for a survey mark.
    """
    mark = get_mark_by_reference(mark_type, mark_number)

    if mark is None:
        raise HTTPException(status_code=404, detail=f"Mark {mark_type} {mark_number} not found")

    tmp = tempfile.mkdtemp()
    sketch_path = download_sketch(mark, Path(tmp))

    if not sketch_path:
        raise HTTPException(status_code=404, detail=f"No sketch available for {mark_type} {mark_number}")

    return FileResponse(sketch_path, media_type="application/pdf", filename=sketch_path.name)
