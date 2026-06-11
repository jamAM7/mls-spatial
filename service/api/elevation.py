import requests
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from pyproj import Transformer

from service.utils import to_web_mercator

ELEV_URL = "https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_5M_Elevation/ImageServer/identify"

# Hard cap on grid points to prevent runaway API calls on large lots
MAX_GRID_POINTS = 200


def _fetch_elevation_at_point(easting: float, northing: float, epsg: int) -> float | None:
    """
    Fetch AHD surface level at a single MGA point.
    Projects MGA → Web Mercator in one step (no WGS84 intermediate).
    """
    try:
        transformer = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:3857", always_xy=True)
        x_wm, y_wm = transformer.transform(easting, northing)
        params = {
            "geometry":     f"{x_wm},{y_wm}",
            "geometryType": "esriGeometryPoint",
            "inSR":         "3857",
            "f":            "json",
        }
        response = requests.get(ELEV_URL, params=params, timeout=10)
        value = response.json().get("value")
        if value is None or value == "NoData":
            return None
        return round(float(value), 3)
    except Exception:
        return None


def fetch_elevation_grid(
    lot_geometry: list,
    epsg: int,
    grid_spacing_m: int = 5,
    padding_pct: float = 50.0,
) -> dict | None:
    """
    Computes a grid of AHD surface elevations over the subject lot's bounding box.

    Args:
        lot_geometry:   list of rings, each ring a list of [easting, northing] pairs
        epsg:           MGA zone EPSG code (e.g. 7856 for zone 56)
        grid_spacing_m: distance between grid points in metres (default 5)
        padding_pct:    padding around bounding box as a percentage of bbox dimensions
                        (default 50.0 = 50% padding on each side → 2× coverage)

    Returns dict with keys:
        grid_spacing_m, padding_pct, bbox_padded, rows, cols, points
        points: list of {row, col, easting, northing, ahd}

    Returns None if lot_geometry is empty.
    Caps grid at MAX_GRID_POINTS — if the lot/spacing combination would exceed this,
    grid_spacing_m is increased automatically and a warning is included in the result.
    """
    if not lot_geometry:
        return None

    # ── Compute bounding box across all rings ─────────────────────────────────
    all_coords = [coord for ring in lot_geometry for coord in ring]
    if not all_coords:
        return None

    min_e = min(c[0] for c in all_coords)
    max_e = max(c[0] for c in all_coords)
    min_n = min(c[1] for c in all_coords)
    max_n = max(c[1] for c in all_coords)

    width  = max_e - min_e
    height = max_n - min_n

    # ── Apply padding ─────────────────────────────────────────────────────────
    pad_e = width  * (padding_pct / 100.0)
    pad_n = height * (padding_pct / 100.0)

    bbox = {
        "min_e": round(min_e - pad_e, 3),
        "max_e": round(max_e + pad_e, 3),
        "min_n": round(min_n - pad_n, 3),
        "max_n": round(max_n + pad_n, 3),
    }

    padded_width  = bbox["max_e"] - bbox["min_e"]
    padded_height = bbox["max_n"] - bbox["min_n"]

    # ── Derive rows and cols, apply hard cap ──────────────────────────────────
    spacing      = grid_spacing_m
    cols         = max(2, math.ceil(padded_width  / spacing) + 1)
    rows         = max(2, math.ceil(padded_height / spacing) + 1)
    capped       = False

    if rows * cols > MAX_GRID_POINTS:
        # Scale up spacing to fit within cap
        spacing = math.ceil(math.sqrt((padded_width * padded_height) / MAX_GRID_POINTS))
        cols    = max(2, math.ceil(padded_width  / spacing) + 1)
        rows    = max(2, math.ceil(padded_height / spacing) + 1)
        capped  = True

    # ── Generate grid points ──────────────────────────────────────────────────
    e_values = [bbox["min_e"] + col * spacing for col in range(cols)]
    n_values = [bbox["min_n"] + row * spacing for row in range(rows)]

    grid_points = [
        {"row": row, "col": col, "easting": round(e, 3), "northing": round(n, 3)}
        for row, n in enumerate(n_values)
        for col, e in enumerate(e_values)
    ]

    # ── Fetch elevations in parallel ──────────────────────────────────────────
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(_fetch_elevation_at_point, pt["easting"], pt["northing"], epsg): pt
            for pt in grid_points
        }
        for future, pt in futures.items():
            pt["ahd"] = future.result()

    return {
        "grid_spacing_m":    spacing,
        "padding_pct":       padding_pct,
        "bbox_padded":       bbox,
        "rows":              rows,
        "cols":              cols,
        "point_count":       len(grid_points),
        "capped":            capped,
        "capped_spacing_m":  spacing if capped else None,
        "points":            grid_points,
    }
