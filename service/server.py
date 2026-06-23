"""
server.py — MLS Spatial Search Service
FastAPI endpoint definitions only. No business logic here.
All logic lives in search.py, export.py, and drive.py.

Run with:
    uvicorn server:app --reload --port 8000
"""

import json
import tempfile
import zipfile
import re
from datetime import date, datetime
from pathlib import Path
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse

from service.search import search, search_from_lot
from service.export import to_geojson, fetch_cre_map_image
from service.api.plan import get_plan_info
from service.api.survey_marks import get_survey_mark_info, get_mark_by_reference, download_sketch
from service.drive import download_plans, get_drive_service, download_single_plan
from service.report import generate_report
from service.utils import lot_label
from service.history import init_db, record_search, get_history
from service.models import Plan

from clients.draw import draw as draw_png

from pydantic import BaseModel, Field


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


class PolygonSearchRequest(BaseModel):
    coordinates: list[list[list[float]]] = Field(
        ...,
        description="Polygon rings as [[x, y], ...]. First ring is the exterior; remaining rings are holes.",
        example=[[[335000.0, 6251000.0], [335100.0, 6251000.0], [335100.0, 6251100.0], [335000.0, 6251100.0], [335000.0, 6251000.0]]],
    )
    epsg: int = Field(
        ...,
        description="EPSG code of the input coordinates e.g. 7856 for MGA Zone 56, 4326 for WGS84.",
    )
    marks_radius_m: int = Field(200, description="Survey mark search radius from polygon centroid in metres.")
    grid_spacing_m: int = Field(5, description="Elevation grid spacing in metres.")
    padding_pct: float  = Field(50.0, description="Padding around polygon bbox for elevation grid as a percentage.")


app = FastAPI(
    title="MLS Spatial Search Service",
    description="Queries NSW Spatial Services APIs to return cadastral lots, survey plans, and survey marks.",
    version="1.0.0",
)

init_db()


@app.get("/health")
def health():
    """C# add-in calls this on startup to confirm the service is running."""
    return {"status": "ok"}


@app.get("/search")
def search_endpoint(
    address: str = Query(..., description="Full street address e.g. '483 GEORGE STREET SYDNEY'"),
    radius_m: int = Query(200, description="Search radius in metres"),
    marks_radius_m: int | None = Query(None, description="Search radius for survey marks in metres. Defaults to radius_m when omitted."),
    grid_spacing_m: int = Query(5, description="Elevation grid spacing in metres"),
    padding_pct: float = Query(50.0, description="Padding around subject lot bbox as a percentage"),
):
    """
    Main endpoint. Returns lots, plans, survey marks, roads, centrelines, and
    AHD elevation grid over the subject lot bbox as GeoJSON.
    """
    result = search(
        address, radius_m,
        marks_radius_m = marks_radius_m,
        grid_spacing_m = grid_spacing_m,
        padding_pct    = padding_pct,
    )

    if result is None:
        raise HTTPException(status_code=404, detail="Address not found")

    record_search(result)
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

    return FileResponse(image_path, media_type="image/png", filename="ss_cre_map.png")


@app.get("/search/png")
def search_png_endpoint(
    address: str = Query(..., description="Full street address e.g. '483 GEORGE STREET SYDNEY'"),
    radius_m: int = Query(200, description="Search radius in metres"),
    marks_radius_m: int | None = Query(None, description="Search radius for survey marks in metres. Defaults to radius_m when omitted."),
):
    """
    Runs a search and returns the cadastral plan PNG directly.
    Lighter alternative to /full-search — no elevation grid, no plan downloads,
    no PDF report, no CRE map.
    """
    result = search(address, radius_m, marks_radius_m=marks_radius_m)

    if result is None:
        raise HTTPException(status_code=404, detail="Address not found")

    geojson  = to_geojson(result)
    tmp      = Path(tempfile.mkdtemp())
    png_path = tmp / "ss_search_plan.png"
    draw_png(geojson, output_path=str(png_path))

    return FileResponse(png_path, media_type="image/png", filename="ss_search_plan.png")


@app.get("/plans/zip")
def plans_zip_endpoint(
    address: str = Query(..., description="Full street address e.g. '483 GEORGE STREET SYDNEY'"),
    radius_m: int = Query(200, description="Search radius in metres"),
):
    """
    Returns a ZIP file containing all plan PDFs and XML sidecars found on Google Drive
    for the given address and radius.
    
    C# app downloads and extracts locally — no output_folder needed.
    """
    result = search(address, radius_m)

    if result is None:
        raise HTTPException(status_code=404, detail="Address not found")

    # Create temp folder for downloads
    tmp = Path(tempfile.mkdtemp())
    
    # Download all plans from Google Drive
    result = download_plans(result, tmp)
    
    # Create ZIP of all downloaded files
    zip_path = tmp / "plans.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in tmp.glob("*"):
            if file.is_file() and file.name != "plans.zip":
                zf.write(file, arcname=file.name)
    
    return FileResponse(zip_path, media_type="application/zip", filename="plans.zip")


@app.get("/report")
def report_endpoint(
    address: str = Query(..., description="Full street address e.g. '483 GEORGE STREET SYDNEY'"),
    radius_m: int = Query(200, description="Search radius in metres"),
    marks_radius_m: int | None = Query(None, description="Search radius for survey marks in metres. Defaults to radius_m when omitted."),
    grid_spacing_m: int = Query(5, description="Elevation grid spacing in metres"),
    padding_pct: float = Query(50.0, description="Padding around subject lot bbox as a percentage"),
):
    """
    Runs full search and returns the PDF report directly.
    C# app downloads and saves locally.
    
    Parameters mirror /full-search but no output_folder needed.
    """
    try:
        print(f"[/report] Starting search for: {address}")
        result = search(
            address, radius_m,
            marks_radius_m = marks_radius_m,
            grid_spacing_m = grid_spacing_m,
            padding_pct    = padding_pct,
        )

        if result is None:
            raise HTTPException(status_code=404, detail="Address not found")

        print(f"[/report] Search complete, found {len(result.plans)} plans")
        
        # Create temp folder for intermediate files
        tmp = Path(tempfile.mkdtemp())
        print(f"[/report] Using temp folder: {tmp}")
        
        # Generate GeoJSON
        print(f"[/report] Generating GeoJSON...")
        geojson = to_geojson(result)
        (tmp / "ss_search_result.geojson").write_text(json.dumps(geojson, indent=2))
        
        # Fetch CRE map
        print(f"[/report] Fetching CRE map...")
        result.cre_map_image = fetch_cre_map_image(result, tmp, map_radius_m=radius_m)
        
        # Generate cadastral plan PNG
        print(f"[/report] Drawing cadastral plan PNG...")
        draw_png(geojson, output_path=str(tmp / "ss_search_plan.png"))
        
        # Download plans from Google Drive
        print(f"[/report] Downloading {len(result.plans)} plans from Drive...")
        result = download_plans(result, tmp)
        print(f"[/report] Plans downloaded")
        
        # Create summary JSON (required by generate_report())
        print(f"[/report] Creating summary JSON...")
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
            "mga_zone":          result.mga_zone,
            "searched_at":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        (tmp / "ss_summary.json").write_text(json.dumps(summary, indent=2))
        
        # Generate and return PDF report
        print(f"[/report] Generating PDF report...")
        report_path = generate_report(tmp)
        print(f"[/report] Report path: {report_path}")
        
        if not report_path or not report_path.exists():
            raise HTTPException(status_code=500, detail="PDF report generation failed")

        print(f"[/report] Report ready, returning PDF")
        return FileResponse(report_path, media_type="application/pdf", filename="ss_report.pdf")
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[/report] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@app.get("/plan/{plan_label}/pdf")
def plan_pdf_endpoint(plan_label: str):
    """
    Downloads a single plan PDF from Google Drive by plan label.
    Returns the PDF directly.
    
    Example: /plan/DP574558/pdf
    """
    try:
        # Parse plan_label to extract plan_type and plan_number
        # Examples: "DP574558" -> ("DP", "574558"), "SP123456" -> ("SP", "123456")
        match = re.match(r'^([A-Z]{2})(\d+)$', plan_label.upper())
        if not match:
            raise HTTPException(status_code=400, detail=f"Invalid plan label format: {plan_label}")
        
        plan_type, plan_number = match.groups()
        plan_number = int(plan_number)
        
        # Create temp folder
        tmp = Path(tempfile.mkdtemp())
        
        # Create Plan object with required fields
        plan = Plan(
            plan_label=plan_label,
            plan_type=plan_type,
            plan_number=plan_number
        )
        
        # Get Drive service and download the plan
        service = get_drive_service()
        download_single_plan(service, plan, tmp)
        
        # Find the downloaded PDF
        pdf_files = list(tmp.glob("*.pdf"))
        if not pdf_files:
            raise HTTPException(status_code=404, detail=f"No PDF found for plan {plan_label}")
        
        pdf_path = pdf_files[0]
        return FileResponse(pdf_path, media_type="application/pdf", filename=pdf_path.name)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download plan {plan_label}: {str(e)}")


@app.get("/full-search")
def full_search_endpoint(
    address: str = Query(..., description="Full street address e.g. '483 GEORGE STREET SYDNEY'"),
    radius_m: int = Query(200, description="Search radius in metres"),
    marks_radius_m: int | None = Query(None, description="Search radius for survey marks in metres. Defaults to radius_m when omitted."),
    output_folder: str = Query(..., description="Absolute path to the folder where output files will be written"),
    grid_spacing_m: int = Query(5, description="Elevation grid spacing in metres"),
    padding_pct: float = Query(50.0, description="Padding around subject lot bbox as a percentage"),
):
    """
    Full search pipeline: search, elevation grid, CRE map, plan downloads, and PDF report.
    Writes all output to output_folder and returns a flat summary dict.
    """
    result = search(
        address, radius_m,
        marks_radius_m = marks_radius_m,
        grid_spacing_m = grid_spacing_m,
        padding_pct    = padding_pct,
    )

    if result is None:
        raise HTTPException(status_code=404, detail="Address not found")

    folder = Path(output_folder)
    folder.mkdir(parents=True, exist_ok=True)

    geojson = to_geojson(result)
    (folder / "ss_search_result.geojson").write_text(json.dumps(geojson, indent=2))

    result.cre_map_image = fetch_cre_map_image(result, folder, map_radius_m=radius_m)
    draw_png(geojson, output_path=str(folder / "ss_search_plan.png"))
    result = download_plans(result, folder)

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
        "output_folder":     str(folder),
        "mga_zone":          result.mga_zone,
        "searched_at":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    (folder / "ss_summary.json").write_text(json.dumps(summary, indent=2))
    report_path = generate_report(folder)

    summary["report_path"] = str(report_path)
    record_search(result)
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


@app.get("/history")
def history_endpoint(limit: int = Query(20, description="Number of recent searches to return")):
    """Returns the last n searches from local SQLite history."""
    return JSONResponse(content=get_history(limit=limit))


@app.get("/search/folio")
def search_folio_endpoint(
    folio: str = Query(..., description="Lot/section/plan reference e.g. '102/1/DP574558'"),
    marks_radius_m: int = Query(200, description="Search radius for survey marks in metres"),
    grid_spacing_m: int = Query(5, description="Elevation grid spacing in metres"),
    padding_pct: float = Query(50.0, description="Padding around subject lot bbox as a percentage"),
):
    """
    Search by folio (lot/section/plan) instead of address.
    
    Example: /search/folio?folio=102/1/DP574558
    
    Returns the same GeoJSON as /search, with the folio lot as the subject lot.
    """
    from service.api.lot import get_lot_by_folio
    from service.search import search_from_lot
    
    # Query the lot by folio
    lot = get_lot_by_folio(folio)
    
    if not lot or not lot.geometry:
        raise HTTPException(status_code=404, detail=f"Lot not found for folio {folio}")
    
    # Get lot centroid
    try:
        from shapely.geometry import Polygon, MultiPolygon
        
        if len(lot.geometry) == 1:
            polygon = Polygon(lot.geometry[0])
        else:
            polygons = [Polygon(ring) for ring in lot.geometry]
            polygon = MultiPolygon(polygons) if len(polygons) > 1 else polygons[0]
        
        centroid = polygon.representative_point()
        x, y = centroid.x, centroid.y
        epsg = 7856  # MGA Zone 56
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate lot centroid: {str(e)}")
    
    # Run search from the lot
    result = search_from_lot(
        lot=lot,
        x=x,
        y=y,
        epsg=epsg,
        marks_radius_m=marks_radius_m,
        grid_spacing_m=grid_spacing_m,
        padding_pct=padding_pct,
    )
    
    if result is None:
        raise HTTPException(status_code=500, detail=f"Search failed for folio {folio}")
    
    record_search(result)
    return JSONResponse(content=to_geojson(result))


@app.post("/search/polygon")
def search_polygon_endpoint(body: PolygonSearchRequest):
    """
    Search by drawn polygon instead of an address or folio.

    The lot query uses direct polygon intersection — all cadastral lots that
    intersect the polygon are returned. Survey marks, roads, and centrelines
    are queried from the polygon centroid using the standard radius approach.

    Returns the same GeoJSON as GET /search — no client changes needed.

    POST (not GET) because coordinate lists can be large.
    """
    from service.search import search_from_polygon

    result = search_from_polygon(
        rings          = body.coordinates,
        epsg           = body.epsg,
        marks_radius_m = body.marks_radius_m,
        grid_spacing_m = body.grid_spacing_m,
        padding_pct    = body.padding_pct,
    )

    if result is None:
        raise HTTPException(status_code=422, detail="Polygon search failed — check coordinate format and EPSG.")

    if not result.nearby_lots:
        raise HTTPException(status_code=404, detail="No cadastral lots found within the given polygon.")

    record_search(result)
    return JSONResponse(content=to_geojson(result))


@app.get("/address/suggest")
def address_suggest_endpoint(
    q: str = Query(..., description="Partial or full address to search for"),
    limit: int = Query(10, description="Maximum number of suggestions to return"),
):
    """
    Returns a list of matching addresses from NSW Spatial Services.
    
    Used for address autocomplete — user types a partial address,
    this returns candidates for dropdown selection.
    
    Example: /address/suggest?q=14 Dellview Tamarama
    Returns: ["14-16 DELLVIEW STREET TAMARAMA", "14 DELLVIEW STREET TAMARAMA", ...]
    """
    from service.api.address import get_address_suggestions
    
    suggestions = get_address_suggestions(q, limit=limit)
    
    if not suggestions:
        raise HTTPException(status_code=404, detail=f"No matching addresses found for '{q}'")
    
    return JSONResponse(content={"suggestions": suggestions})