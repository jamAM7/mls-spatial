"""
draw.py — MLS Spatial Search Service Client
PNG drawing script that consumes the /search API endpoint.

This script does not import anything from the service codebase.
It only speaks HTTP and GeoJSON.

Dependencies:
    pip install requests shapely matplotlib pillow

Usage:
    import requests
    from draw import draw

    response = requests.get(
        "http://localhost:8000/search",
        params={"address": "483 GEORGE STREET SYDNEY", "radius_m": 200}
    )
    draw(response.json(), output_path="search_plan.png")
"""
import matplotlib
matplotlib.use("Agg")   # non-interactive backend — required when called from a thread
import matplotlib.pyplot as plt

import base64
import io
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.patches import Polygon as MplPolygon
from PIL import Image
from shapely.geometry import Polygon, Point


# ── SCIMS symbol data (hardcoded) ─────────────────────────────────────────────
# Generated once by fetch_scims_symbols.py — no network call at runtime.
# Key: `marksymbol` field value from the GeoJSON mark properties (e.g. "SSR").
# Value: base64-encoded PNG imageData string from the NSW MapServer renderer.
#
# To regenerate (only needed if NSW ever change their symbology):
#     python fetch_scims_symbols.py
#
# --- paste _SYMBOL_DATA here after running fetch_scims_symbols.py ---
_SYMBOL_DATA: dict[str, str] = {}
# --- end paste ---


# ── Decode and upscale PNGs at module load ────────────────────────────────────
# Source icons are 14×14px. Upscale 4× with NEAREST so edges stay crisp.
_MARK_IMAGES: dict[str, Image.Image] = {
    key: Image.open(io.BytesIO(base64.b64decode(b64)))
             .convert("RGBA")
             .resize((56, 56), Image.Resampling.NEAREST)
    for key, b64 in _SYMBOL_DATA.items()
}


# ── Fallback replica markers (used when _SYMBOL_DATA is empty) ────────────────

_FALLBACK_COLOURS = {
    "established gda2020 and accurate ahd71": "#ff1e28",
    "established gda2020 only":               "#d200ed",
    "accurate ahd71 only":                    "#69ff03",
    "accurate ahd71 + approx. gda2020":       "#27ac72",
    "approx. gda2020 only":                   "#0048e5",
    "unknown":                                "#11c6ff",
}

_FALLBACK_SYMBOLS = {
    "SS": r"$\odot$",
    "PM": "s",
    "TS": "^",
    "CR": "v",
    "MM": "P",
    "CP": r"$\oplus$",
    "GB": "*",
}

def _fallback_colour(mark_symbol_label: str) -> str:
    label_lower = (mark_symbol_label or "").lower()
    for key, colour in _FALLBACK_COLOURS.items():
        if key in label_lower:
            return colour
    return "#11c6ff"

def _fallback_symbol(mark_type: str) -> str:
    return _FALLBACK_SYMBOLS.get((mark_type or "").upper(), "*")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_lots(features: list) -> list:
    return [f for f in features if f["properties"].get("feature_type") == "lot"]

def _get_marks(features: list) -> list:
    return [f for f in features if f["properties"].get("feature_type") == "survey_mark"]

def _draw_label_in_polygon(ax, coords, lot_number, plan_label, fontsize=4, is_subject=False):
    """
    Draws the lot number and plan label inside the polygon.
    For the subject lot, positions the text in the lower portion so it
    doesn't overlap with the star drawn in the upper portion.
    """
    try:
        from shapely.geometry import box as shapely_box
        poly = Polygon(coords)
        if not poly.is_valid or poly.area == 0:
            return

        if is_subject:
            # Mirror of _star_position — erode inward then take lower half centroid
            minx, miny, maxx, maxy = poly.bounds
            height = maxy - miny
            inner  = poly.buffer(-height * 0.10)
            if not inner.is_empty and inner.is_valid:
                ib_minx, ib_miny, ib_maxx, ib_maxy = inner.bounds
                mid_y = (ib_miny + ib_maxy) / 2
                lower = inner.intersection(shapely_box(ib_minx - 1, ib_miny - 1, ib_maxx + 1, mid_y))
                cx, cy = (lower.centroid.x, lower.centroid.y) if not lower.is_empty else (poly.centroid.x, poly.centroid.y)
            else:
                cx, cy = poly.centroid.x, poly.centroid.y
        else:
            cx, cy = poly.centroid.x, poly.centroid.y

        label = f"{lot_number}\n{plan_label}" if lot_number else plan_label
        ax.text(cx, cy, label, ha="center", va="center",
                fontsize=fontsize, color="black", clip_on=True, zorder=3)
    except Exception:
        pass

def _star_position(coords) -> tuple[float, float] | None:
    """
    Returns a point in the upper portion of the polygon that is guaranteed
    to sit inside it, so the subject lot star never drifts into a neighbouring lot.

    Strategy:
      1. Erode the polygon inward by 10% of its height — creates a safe inner zone
      2. Clip that inner zone to its upper half
      3. Return the centroid of the clipped shape
      4. Fall back to polygon centroid if any step fails (very thin/irregular lots)
    """
    try:
        from shapely.geometry import box as shapely_box
        poly = Polygon(coords)
        if not poly.is_valid or poly.area == 0:
            return None

        minx, miny, maxx, maxy = poly.bounds
        height = maxy - miny

        # Erode inward — keeps star safely away from lot boundaries
        margin = height * 0.10
        inner  = poly.buffer(-margin)
        if inner.is_empty or not inner.is_valid:
            return tuple(poly.centroid.coords[0])

        # Clip to upper half of the eroded polygon
        ib_minx, ib_miny, ib_maxx, ib_maxy = inner.bounds
        mid_y  = (ib_miny + ib_maxy) / 2
        upper  = inner.intersection(shapely_box(ib_minx - 1, mid_y, ib_maxx + 1, ib_maxy + 1))

        if upper.is_empty:
            return tuple(inner.centroid.coords[0])

        return tuple(upper.centroid.coords[0])
    except Exception:
        return None
    

def _get_roads(features: list) -> list:
    return [f for f in features if f["properties"].get("feature_type") == "road"]

def _get_centrelines(features: list) -> list:
    return [f for f in features if f["properties"].get("feature_type") == "road_centreline"]


# ── Main draw function ────────────────────────────────────────────────────────

def draw(geojson: dict, output_path: str = "search_plan.png") -> None:
    """
    Takes a GeoJSON FeatureCollection from the /search endpoint.
    Draws all lots and survey marks and saves as PNG.

    Mark symbols use real SCIMS PNGs (hardcoded from NSW MapServer renderer),
    keyed by the `marksymbol` property on each mark feature in the GeoJSON.
    Falls back to matplotlib replica markers if _SYMBOL_DATA is empty.

    Lot colours:
        - Compiled lot  → steelblue
        - Surveyed lot  → pink
        - Unknown       → grey
    """
    features           = geojson.get("features", [])
    lots               = _get_lots(features)
    marks              = _get_marks(features)
    using_real_symbols = bool(_MARK_IMAGES)

    fig, ax = plt.subplots(1, 1, figsize=(16, 16))
    ax.set_aspect("equal")
    ax.axis("off")

    # ── Draw roads ────────────────────────────────────────────────────────────
    # Drawn before lots so lot edges win at shared boundaries
    roads = _get_roads(features)
    for road in roads:
        valid_rings = [r for r in road["geometry"]["coordinates"] if len(r) >= 3]
        if not valid_rings:
            continue

        for ring in valid_rings:
            ax.add_patch(MplPolygon(
                ring, closed=True,
                facecolor="#e8e0d0", edgecolor="#a09880",
                linewidth=0.5, alpha=0.9, zorder=1,
            ))

        # Label on largest ring
        largest = max(valid_rings, key=lambda r: Polygon(r).area)
        name    = road["properties"].get("road_name_label", "")
        rtype   = road["properties"].get("road_type_label", "")
        label   = f"{name}\n{rtype}" if name and rtype else name
        if label.strip():
            _draw_label_in_polygon(ax, largest, label, "", fontsize=3.5)

    # ── Draw road centrelines ─────────────────────────────────────────────────────
    centrelines = _get_centrelines(features)
    for cl in centrelines:
        coords = cl["geometry"]["coordinates"]   # [[x,y], [x,y], ...] — already one path
        if len(coords) < 2:
            continue
        xs = [p[0] for p in coords]
        ys = [p[1] for p in coords]
        ax.plot(xs, ys, color="#888880", linewidth=0.8, zorder=2, solid_capstyle="round")

    # ── Draw lots ─────────────────────────────────────────────────────────────
    subject_star_pos = None

    for lot in lots:
        props       = lot["properties"]
        rings       = lot["geometry"]["coordinates"]  # list of rings — may be >1 for part lots
        lot_number  = props.get("lot_number", "")
        plan_label  = props.get("plan_label", "")
        is_surveyed = props.get("is_surveyed")
        is_subject  = props.get("is_subject", False)

        if is_surveyed is True:
            facecolor, edgecolor = "#ffb6c1", "#c2185b"
        elif is_surveyed is False:
            facecolor, edgecolor = "steelblue", "navy"
        else:
            facecolor, edgecolor = "grey", "dimgrey"

        valid_rings = [r for r in rings if len(r) >= 3]
        if not valid_rings:
            continue

        # Draw every ring — part lots have multiple separate polygon parts
        for ring in valid_rings:
            ax.add_patch(MplPolygon(
                ring, closed=True,
                facecolor=facecolor, edgecolor=edgecolor,
                linewidth=0.5, alpha=0.7,
            ))

        # Label and star on the largest ring only
        largest = max(valid_rings, key=lambda r: Polygon(r).area if len(r) >= 3 else 0)
        _draw_label_in_polygon(ax, largest, lot_number, plan_label, is_subject=is_subject)

        if is_subject:
            subject_star_pos = _star_position(largest)

    # ── Subject lot star — positioned above the centroid label ───────────────
    if subject_star_pos:
        ax.plot(*subject_star_pos, marker="*", color="gold", markersize=18,
                markeredgecolor="black", markeredgewidth=0.8, zorder=4)

    # ── Draw survey marks ─────────────────────────────────────────────────────
    seen_symbols: dict[str, str] = {}

    for mark in marks:
        props             = mark["properties"]
        x, y              = mark["geometry"]["coordinates"]
        mark_number       = props.get("mark_number", "")
        mark_type         = props.get("mark_type", "")
        mark_status       = props.get("mark_status", "")
        marksymbol        = props.get("marksymbol", "")
        mark_symbol_label = props.get("mark_symbol_label", "")

        status_suffix = f" ({mark_status})" if mark_status else ""
        annotation    = f"{mark_type} {mark_number}{status_suffix}"

        if using_real_symbols and marksymbol in _MARK_IMAGES:
            img      = _MARK_IMAGES[marksymbol]
            imagebox = OffsetImage(img, zoom=0.45, resample=False)
            imagebox.image.axes = ax
            ax.add_artist(AnnotationBbox(
                imagebox, (x, y),
                frameon=False, zorder=5,
                box_alignment=(0.5, 0.5),
            ))
            seen_symbols[marksymbol] = mark_symbol_label or marksymbol
        else:
            colour = _fallback_colour(mark_symbol_label)
            symbol = _fallback_symbol(mark_type)
            msize  = 14 if symbol.startswith("$") else 9
            ax.plot(x, y, marker=symbol, color=colour, markersize=msize,
                    markeredgecolor="black", markeredgewidth=0.3,
                    linestyle="None", zorder=5)

        ax.annotate(annotation, xy=(x, y), xytext=(5, 5),
                    textcoords="offset points", fontsize=4,
                    color="black" if using_real_symbols else _fallback_colour(mark_symbol_label),
                    zorder=5)

    # ── Auto scale ────────────────────────────────────────────────────────────
    ax.autoscale()

    # ── Title ─────────────────────────────────────────────────────────────────
    search       = geojson.get("search", {})
    address_line = search.get("address_resolved", "")
    subject_lot  = search.get("subject_lot", "")
    radius_line  = f"r={search.get('radius_m', '')}m"
    counts_line  = (
        f"Lots: {search.get('lot_count', 0)}  "
        f"Plans: {search.get('plan_count', 0)}  "
        f"Marks: {search.get('mark_count', 0)}"
    )

    title_parts = [f"{address_line}  |  {radius_line}"]
    if subject_lot:
        title_parts.append(f"Subject lot: {subject_lot}")
    title_parts.append(counts_line)

    ax.set_title("\n".join(title_parts), fontsize=10, pad=12)

    # ── Legend ────────────────────────────────────────────────────────────────
    legend_handles = [
        mpatches.Patch(facecolor="steelblue", edgecolor="navy",    label="Compiled lot"),
        mpatches.Patch(facecolor="#ffb6c1",   edgecolor="#c2185b", label="Surveyed lot"),
        mpatches.Patch(facecolor="grey",      edgecolor="dimgrey", label="Unknown/unresearched"),
        mlines.Line2D([0], [0], marker="*", color="w", markerfacecolor="gold",
                      markeredgecolor="black", markersize=12, label="Subject lot"),
    ]

    if not using_real_symbols:
        for colour, label in [
            ("#ff1e28", "Established GDA2020 + Accurate AHD71"),
            ("#d200ed", "Established GDA2020 Only"),
            ("#69ff03", "Accurate AHD71 Only"),
            ("#27ac72", "Accurate AHD71 + Approx. GDA2020"),
            ("#0048e5", "Approx. GDA2020 Only"),
            ("#11c6ff", "Unknown accuracy"),
        ]:
            legend_handles.append(
                mlines.Line2D([0], [0], marker="o", color="w",
                              markerfacecolor=colour, markeredgecolor="black",
                              markersize=8, label=label)
            )

    ax.legend(handles=legend_handles, loc="lower left", fontsize=7, framealpha=0.9)

    if using_real_symbols and seen_symbols:
        _draw_symbol_reference(ax, seen_symbols)

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Saved to {output_path}")


# ── Symbol reference grid (bottom-right) ─────────────────────────────────────

def _draw_symbol_reference(ax, seen_symbols: dict[str, str]) -> None:
    """
    Renders a small reference grid in the bottom-right corner showing
    the real SCIMS PNG icons alongside their labels for mark types
    present in this result set.
    """
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes

    items = [(k, v) for k, v in seen_symbols.items() if k in _MARK_IMAGES]
    if not items:
        return

    n   = len(items)
    iax = inset_axes(ax, width="32%", height=f"{n * 4 + 2}%",
                     loc="lower right", borderpad=1)
    iax.set_xlim(0, 1)
    iax.set_ylim(0, n)
    iax.axis("off")
    iax.patch.set_facecolor("white")
    iax.patch.set_alpha(0.88)

    for i, (sym_value, sym_label) in enumerate(items):
        img      = _MARK_IMAGES[sym_value]
        imagebox = OffsetImage(img, zoom=0.32, resample=False)
        imagebox.image.axes = iax
        iax.add_artist(AnnotationBbox(
            imagebox, (0.06, i + 0.5),
            frameon=False, zorder=5,
            box_alignment=(0.5, 0.5),
            xycoords="data",
        ))
        iax.text(0.14, i + 0.5, sym_label, va="center", ha="left",
                 fontsize=6, transform=iax.transData)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    response = requests.get(
        "http://localhost:8000/search",
        params={"address": "483 GEORGE STREET SYDNEY", "radius_m": 150}
    )
    draw(response.json(), output_path="search_plan.png")