# Built by search.py — it calls all api/ modules and assembles one SearchResult
# nearby_lots includes the subject lot
# plans is a deduplicated list — many lots share a plan, only include each plan once

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional

from shapely.geometry import Point, Polygon as ShapelyPolygon

from service.models import SearchResult, Address, Lot, Plan, SurveyMark, ElevationGrid
from service.utils import sanitise_address, mga_zone_from_longitude
from service.config import EPSG_CODES
from service.api.address import get_address_coordinates
from service.api.lot import get_lot_info
from service.api.plan import get_plan_info
from service.api.survey_marks import get_survey_mark_info
from service.api.road import get_road_info, get_road_centreline_info
from service.api.elevation import fetch_elevation_grid
from service.api.property import get_address_at_point


def _find_subject_lot(lots: list[Lot], x: float, y: float) -> Lot | None:
    pt = Point(x, y)
    for lot in lots:
        for ring in lot.geometry:
            try:
                if len(ring) >= 3 and ShapelyPolygon(ring).contains(pt):
                    return lot
            except Exception:
                pass
    return None


def _fetch_all_plans(
    seen_plan_labels: list[str],
    on_plan_found: Optional[Callable[[Plan], None]] = None,
) -> list[Plan]:
    """
    Fetches plan metadata for all labels in parallel.

    If on_plan_found is provided (e.g. a Drive download callback), it is called
    for each plan as soon as its metadata arrives — in a separate Drive thread pool
    running concurrently with the remaining metadata fetches.
    This means Drive downloads start immediately rather than waiting for all
    metadata to be collected first.
    """
    plans: list[Plan] = []

    with ThreadPoolExecutor(max_workers=10) as plan_executor:
        # Separate pool for Drive downloads so they don't block plan metadata fetches
        drive_executor = ThreadPoolExecutor(max_workers=4) if on_plan_found else None
        drive_futures = []

        try:
            plan_futures = {
                plan_executor.submit(get_plan_info, label): label
                for label in seen_plan_labels
            }
            for future in as_completed(plan_futures):
                plan = future.result()
                if plan:
                    plans.append(plan)
                    if on_plan_found and drive_executor:
                        drive_futures.append(drive_executor.submit(on_plan_found, plan))

            # Wait for all Drive downloads to finish before returning
            for df in as_completed(drive_futures):
                df.result()
        finally:
            if drive_executor:
                drive_executor.shutdown(wait=True)

    return plans


def search(
    address_input: str,
    radius_m: int,
    datum: str = "GDA2020",
    marks_radius_m: int | None = None,
    grid_spacing_m: int | None = 5,
    padding_pct: float = 50.0,
    on_plan_found: Optional[Callable[[Plan], None]] = None,
) -> SearchResult | None:
    """
    Main search pipeline. Assembles a SearchResult from all NSW Spatial Services APIs.

    on_plan_found: optional callback fired for each Plan as soon as its metadata
    arrives from the API. Used by /full-search to kick off Google Drive downloads
    incrementally rather than in a batch after all metadata is collected.

    grid_spacing_m: pass None to skip the elevation grid (used by /search/png).
    """
    address_input = sanitise_address(address_input)

    # Pass 1 — WGS84 only, to get longitude for zone detection
    address_geo = get_address_coordinates(address_input, out_sr=4326)
    if not address_geo:
        return None

    zone = mga_zone_from_longitude(address_geo.longitude)
    try:
        epsg = EPSG_CODES[(datum, zone)]
    except KeyError:
        raise ValueError(f"Unsupported datum/zone combination: {datum}, {zone}")

    # Pass 2 — authoritative projected coordinates + admin boundaries from NSW API
    address = get_address_coordinates(address_input, out_sr=epsg)
    if not address:
        return None

    _marks_radius = marks_radius_m if marks_radius_m is not None else radius_m

    # All spatial queries are independent — run in parallel
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_lots        = executor.submit(get_lot_info, address.easting, address.northing, epsg, radius_m)
        future_marks       = executor.submit(get_survey_mark_info, address.easting, address.northing, epsg, _marks_radius)
        future_roads       = executor.submit(get_road_info, address.easting, address.northing, epsg, radius_m)
        future_centrelines = executor.submit(get_road_centreline_info, address.easting, address.northing, epsg, radius_m)

    lots             = future_lots.result()        or []
    survey_marks     = future_marks.result()       or []
    roads            = future_roads.result()       or []
    road_centrelines = future_centrelines.result() or []

    # Query FS/12 at each lot's centroid in parallel to get property addresses
    def _get_lot_address(lot: Lot) -> tuple[Lot, str | None]:
        if not lot.geometry:
            return lot, None
        try:
            point = ShapelyPolygon(lot.geometry[0]).representative_point()
            return lot, get_address_at_point(point.x, point.y, epsg)
        except Exception:
            return lot, None

    with ThreadPoolExecutor(max_workers=10) as addr_executor:
        for future in as_completed([addr_executor.submit(_get_lot_address, lot) for lot in lots]):
            lot, addr = future.result()
            lot.address = addr

    # Find subject lot by point-in-polygon — no extra API call needed
    subject_lot = _find_subject_lot(lots, address.easting, address.northing)

    if subject_lot:
        for lot in lots:
            if lot.plan_label == subject_lot.plan_label and lot.lot_number == subject_lot.lot_number:
                lot.is_subject = True
                break

    # Plans and elevation grid are independent — run in parallel
    seen_plan_labels = list({lot.plan_label for lot in lots})

    def _run_elevation():
        if not (subject_lot and subject_lot.geometry and grid_spacing_m is not None):
            return None
        return fetch_elevation_grid(
            lot_geometry   = subject_lot.geometry,
            epsg           = epsg,
            grid_spacing_m = grid_spacing_m,
            padding_pct    = padding_pct,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_plans     = executor.submit(_fetch_all_plans, seen_plan_labels, on_plan_found)
        future_elevation = executor.submit(_run_elevation)

    plans              = future_plans.result()
    elevation_grid_raw = future_elevation.result()
    elevation_grid     = ElevationGrid(**elevation_grid_raw) if elevation_grid_raw else None

    return SearchResult(
        address          = address,
        subject_lot      = subject_lot,
        nearby_lots      = lots,
        plans            = plans,
        survey_marks     = survey_marks,
        search_radius_m  = radius_m,
        marks_radius_m   = _marks_radius,
        cre_map_image    = None,
        epsg             = epsg,
        datum            = datum,
        mga_zone         = zone,
        roads            = roads,
        road_centrelines = road_centrelines,
        elevation_grid   = elevation_grid,
    )