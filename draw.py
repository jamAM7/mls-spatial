"""
draw.py — MLS Spatial Search Service Client
PNG drawing script that consumes the /search API endpoint.

This script does not import anything from the service codebase.
It only speaks HTTP and GeoJSON.

Dependencies:
    pip install requests shapely matplotlib

Usage:
    import requests
    from draw import draw

    response = requests.get(
        "http://localhost:8000/search",
        params={"address": "483 GEORGE STREET SYDNEY", "radius_m": 200}
    )
    draw(response.json(), output_path="search_plan.png")
"""

import requests
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
from matplotlib.patches import Polygon as MplPolygon
from shapely.geometry import Polygon
from datetime import datetime


# ── SCIMS mark colour mapping ─────────────────────────────────────────────────
# Colour determined by mark_symbol_label field

MARK_COLOURS = {
    "established gda2020 and accurate ahd71": "#ff1e28",
    "established gda2020 only":               "#d200ed",
    "accurate ahd71 only":                    "#69ff03",
    "accurate ahd71 + approx. gda2020":       "#27ac72",
    "approx. gda2020 only":                   "#0048e5",
    "unknown":                                "#11c6ff",
}

def _get_mark_colour(mark_symbol_label: str) -> str:
    """Map mark_symbol_label to a hex colour."""
    if not mark_symbol_label:
        return "#11c6ff"  # default unknown
    label_lower = mark_symbol_label.lower()
    for key, colour in MARK_COLOURS.items():
        if key in label_lower:
            return colour
    return "#11c6ff"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_year(date_str: str) -> int | None:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").year
    except ValueError:
        return None


def _get_lots(features: list) -> list:
    return [f for f in features if f["properties"].get("feature_type") == "lot"]


def _get_marks(features: list) -> list:
    return [f for f in features if f["properties"].get("feature_type") == "survey_mark"]


def _draw_label_in_polygon(ax, coords, lot_number, plan_label, fontsize=4):
    """Draw lot number and plan label inside a polygon at its centroid."""
    try:
        poly = Polygon(coords)
        if not poly.is_valid or poly.area == 0:
            return
        cx, cy = poly.centroid.x, poly.centroid.y
        label = f"{lot_number}\n{plan_label}" if lot_number else plan_label
        ax.text(
            cx, cy, label,
            ha="center", va="center",
            fontsize=fontsize,
            color="black",
            clip_on=True,
            zorder=3,
        )
    except Exception:
        pass


# ── Main draw function ────────────────────────────────────────────────────────

def draw(geojson: dict, output_path: str = "search_plan.png") -> None:
    """
    Takes a GeoJSON FeatureCollection from the /search endpoint.
    Draws all lots and survey marks and saves as PNG.
    """
    features = geojson.get("features", [])
    lots     = _get_lots(features)
    marks    = _get_marks(features)

    fig, ax = plt.subplots(1, 1, figsize=(16, 16))
    ax.set_aspect("equal")
    ax.axis("off")

    # ── Age shading setup ─────────────────────────────────────────────────────
    surveyed_years = []
    for lot in lots:
        props = lot["properties"]
        if props.get("is_surveyed") is True:
            year = _parse_year(props.get("registration_date"))
            if year:
                surveyed_years.append(year)

    if surveyed_years:
        year_min = min(surveyed_years)
        year_max = max(surveyed_years)
        norm = mcolors.Normalize(vmin=year_min, vmax=year_max)
        cmap = plt.cm.RdPu
    else:
        norm = None
        cmap = None

    # ── Draw lots ─────────────────────────────────────────────────────────────
    subject_centroid = None

    for lot in lots:
        props      = lot["properties"]
        coords     = lot["geometry"]["coordinates"][0]
        lot_number = props.get("lot_number", "")
        plan_label = props.get("plan_label", "")
        is_surveyed = props.get("is_surveyed")
        is_subject  = props.get("is_subject", False)
        reg_date    = props.get("registration_date")

        if len(coords) < 3:
            continue

        # Determine fill colour
        if is_surveyed is True and norm is not None:
            year = _parse_year(reg_date)
            color     = cmap(norm(year)) if year else "grey"
            edgecolor = "darkred"
        elif is_surveyed is False:
            color     = "steelblue"
            edgecolor = "navy"
        else:
            color     = "grey"
            edgecolor = "dimgrey"

        patch = MplPolygon(
            coords, closed=True,
            facecolor=color, edgecolor=edgecolor,
            linewidth=0.5, alpha=0.7
        )
        ax.add_patch(patch)

        # Draw label inside polygon
        _draw_label_in_polygon(ax, coords, lot_number, plan_label)

        # Track subject lot centroid
        if is_subject:
            try:
                poly = Polygon(coords)
                subject_centroid = (poly.centroid.x, poly.centroid.y)
            except Exception:
                pass

    # ── Subject lot pin ───────────────────────────────────────────────────────
    if subject_centroid:
        ax.plot(
            subject_centroid[0], subject_centroid[1],
            marker="*", color="gold", markersize=18,
            markeredgecolor="black", markeredgewidth=0.8,
            zorder=5
        )

    # ── Draw survey marks ─────────────────────────────────────────────────────
    for mark in marks:
        props             = mark["properties"]
        x, y              = mark["geometry"]["coordinates"]
        mark_number       = props.get("mark_number", "")
        mark_type         = props.get("mark_type", "")
        mark_status       = props.get("mark_status", "")
        mark_symbol_label = props.get("mark_symbol_label", "")

        colour = _get_mark_colour(mark_symbol_label)

        # Label: mark type + number + status
        status_str = f"{mark_status}" if mark_status else ""
        label = f"{mark_type}\n{mark_number}{status_str}"

        ax.plot(
            x, y,
            marker="*", color=colour, markersize=8,
            markeredgecolor="black", markeredgewidth=0.3,
            zorder=4
        )
        ax.annotate(
            label,
            xy=(x, y),
            xytext=(4, 4),
            textcoords="offset points",
            fontsize=4,
            color=colour,
            zorder=4
        )

    # ── Auto scale ────────────────────────────────────────────────────────────
    ax.autoscale()

    # ── Legend ────────────────────────────────────────────────────────────────
    legend_handles = [
        mpatches.Patch(facecolor="steelblue", edgecolor="navy",    label="Compiled lot"),
        mpatches.Patch(facecolor="lightpink", edgecolor="darkred", label="Surveyed lot (old)"),
        mpatches.Patch(facecolor="darkred",   edgecolor="darkred", label="Surveyed lot (recent)"),
        mpatches.Patch(facecolor="grey",      edgecolor="dimgrey", label="Unknown/unresearched"),
        plt.Line2D([0], [0], marker="*", color="w", markerfacecolor="gold",    markersize=12, label="Subject lot"),
        plt.Line2D([0], [0], marker="*", color="w", markerfacecolor="#ff1e28", markersize=8,  label="Mark: GDA2020 + AHD71"),
        plt.Line2D([0], [0], marker="*", color="w", markerfacecolor="#d200ed", markersize=8,  label="Mark: GDA2020 Only"),
        plt.Line2D([0], [0], marker="*", color="w", markerfacecolor="#69ff03", markersize=8,  label="Mark: AHD71 Only"),
        plt.Line2D([0], [0], marker="*", color="w", markerfacecolor="#27ac72", markersize=8,  label="Mark: AHD71 + Approx GDA2020"),
        plt.Line2D([0], [0], marker="*", color="w", markerfacecolor="#0048e5", markersize=8,  label="Mark: Approx GDA2020 Only"),
        plt.Line2D([0], [0], marker="*", color="w", markerfacecolor="#11c6ff", markersize=8,  label="Mark: Unknown"),
    ]

    search   = geojson.get("search", {})
    title    = f"{search.get('address_resolved', '')}  |  r={search.get('radius_m', '')}m"
    subtitle = f"Lots: {search.get('lot_count', 0)}  Plans: {search.get('plan_count', 0)}  Marks: {search.get('mark_count', 0)}"

    ax.set_title(f"{title}\n{subtitle}", fontsize=10, pad=12)
    ax.legend(handles=legend_handles, loc="lower left", fontsize=7, framealpha=0.8)

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Saved to {output_path}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    response = requests.get(
        "http://localhost:8000/search",
        params={"address": "483 GEORGE STREET SYDNEY", "radius_m": 150}
    )
    draw(response.json(), output_path="search_plan.png")




































# """
# draw.py — MLS Spatial Search Service Client
# PNG drawing script that consumes the /search API endpoint.

# This script does not import anything from the service codebase.
# It only speaks HTTP and GeoJSON.

# Dependencies:
#     pip install requests shapely matplotlib

# Usage:
#     import requests
#     from draw import draw

#     response = requests.get(
#         "http://localhost:8000/search",
#         params={"address": "483 GEORGE STREET SYDNEY", "radius_m": 200}
#     )
#     draw(response.json(), output_path="search_plan.png")
# """

# import requests
# import matplotlib.pyplot as plt
# import matplotlib.patches as mpatches
# import matplotlib.colors as mcolors
# from matplotlib.patches import Polygon as MplPolygon
# from matplotlib.collections import PatchCollection
# from shapely.geometry import shape, Point, Polygon
# from datetime import datetime


# # ── Helpers ───────────────────────────────────────────────────────────────────

# def _parse_year(date_str: str) -> int | None:
#     """Extract year from a date string like '1996-01-19'."""
#     if not date_str:
#         return None
#     try:
#         return datetime.strptime(date_str, "%Y-%m-%d").year
#     except ValueError:
#         return None


# def _get_lots(features: list) -> list:
#     return [f for f in features if f["properties"].get("feature_type") == "lot"]


# def _get_marks(features: list) -> list:
#     return [f for f in features if f["properties"].get("feature_type") == "survey_mark"]


# # ── Main draw function ────────────────────────────────────────────────────────

# def draw(geojson: dict, output_path: str = "search_plan.png") -> None:
#     """
#     Takes a GeoJSON FeatureCollection from the /search endpoint.
#     Draws all lots and survey marks and saves as PNG.
#     """
#     features = geojson.get("features", [])
#     lots     = _get_lots(features)
#     marks    = _get_marks(features)

#     fig, ax = plt.subplots(1, 1, figsize=(14, 14))
#     ax.set_aspect("equal")
#     ax.axis("off")

#     # ── Age shading setup ─────────────────────────────────────────────────────
#     # Collect years from all surveyed lots for normalisation
#     surveyed_years = []
#     for lot in lots:
#         props = lot["properties"]
#         if props.get("is_surveyed") is True:
#             year = _parse_year(props.get("registration_date"))
#             if year:
#                 surveyed_years.append(year)

#     if surveyed_years:
#         year_min = min(surveyed_years)
#         year_max = max(surveyed_years)
#         norm = mcolors.Normalize(vmin=year_min, vmax=year_max)
#         cmap = plt.cm.RdPu  # light pink (old) → dark red (new)
#     else:
#         norm = None
#         cmap = None

#     # ── Draw lots ─────────────────────────────────────────────────────────────
#     subject_centroid = None

#     for lot in lots:
#         props = lot["properties"]
#         coords = lot["geometry"]["coordinates"][0]  # outer ring

#         if len(coords) < 3:
#             continue

#         polygon = MplPolygon(coords, closed=True)
#         is_surveyed = props.get("is_surveyed")
#         is_subject  = props.get("is_subject", False)
#         reg_date    = props.get("registration_date")

#         if is_surveyed is True and norm is not None:
#             year = _parse_year(reg_date)
#             if year:
#                 color = cmap(norm(year))
#             else:
#                 color = "grey"
#             edgecolor = "darkred"
#         elif is_surveyed is False:
#             color     = "steelblue"
#             edgecolor = "navy"
#         else:
#             # None = unknown/unresearched
#             color     = "grey"
#             edgecolor = "dimgrey"

#         patch = MplPolygon(coords, closed=True, facecolor=color, edgecolor=edgecolor, linewidth=0.5, alpha=0.7)
#         ax.add_patch(patch)

#         # Track subject lot centroid for pin
#         if is_subject:
#             try:
#                 shapely_poly = Polygon(coords)
#                 c = shapely_poly.centroid
#                 subject_centroid = (c.x, c.y)
#             except Exception:
#                 pass

#     # ── Subject lot pin ───────────────────────────────────────────────────────
#     if subject_centroid:
#         ax.plot(
#             subject_centroid[0], subject_centroid[1],
#             marker="*", color="gold", markersize=18,
#             markeredgecolor="black", markeredgewidth=0.8,
#             zorder=5
#         )

#     # ── Draw survey marks ─────────────────────────────────────────────────────
#     for mark in marks:
#         props = mark["properties"]
#         x, y  = mark["geometry"]["coordinates"]
#         mark_number = props.get("mark_number", "")
#         gda_class   = props.get("gda_class", "")

#         ax.plot(
#             x, y,
#             marker="^", color="lime", markersize=6,
#             markeredgecolor="darkgreen", markeredgewidth=0.5,
#             zorder=4
#         )
#         ax.annotate(
#             f"{mark_number} ({gda_class})",
#             xy=(x, y),
#             xytext=(3, 3),
#             textcoords="offset points",
#             fontsize=4,
#             color="darkgreen",
#             zorder=4
#         )

#     # ── Auto scale to content ─────────────────────────────────────────────────
#     ax.autoscale()

#     # ── Legend ────────────────────────────────────────────────────────────────
#     legend_handles = [
#         mpatches.Patch(facecolor="steelblue",  edgecolor="navy",     label="Compiled lot"),
#         mpatches.Patch(facecolor="lightpink",  edgecolor="darkred",  label="Surveyed lot (old)"),
#         mpatches.Patch(facecolor="darkred",    edgecolor="darkred",  label="Surveyed lot (recent)"),
#         mpatches.Patch(facecolor="grey",       edgecolor="dimgrey",  label="Unknown/unresearched"),
#         plt.Line2D([0], [0], marker="*",  color="w", markerfacecolor="gold",  markersize=12, label="Subject lot"),
#         plt.Line2D([0], [0], marker="^",  color="w", markerfacecolor="lime",  markersize=8,  label="Survey mark"),
#     ]

#     search = geojson.get("search", {})
#     title  = f"{search.get('address_resolved', '')}  |  r={search.get('radius_m', '')}m"
#     subtitle = f"Lots: {search.get('lot_count', 0)}  Plans: {search.get('plan_count', 0)}  Marks: {search.get('mark_count', 0)}"

#     ax.set_title(f"{title}\n{subtitle}", fontsize=10, pad=12)
#     ax.legend(handles=legend_handles, loc="lower left", fontsize=7, framealpha=0.8)

#     plt.tight_layout()
#     plt.savefig(output_path, dpi=200, bbox_inches="tight")
#     plt.close()
#     print(f"Saved to {output_path}")


# # ── Entry point ───────────────────────────────────────────────────────────────

# if __name__ == "__main__":
#     response = requests.get(
#         "http://localhost:8000/search",
#         params={"address": "483 GEORGE STREET SYDNEY", "radius_m": 150}
#     )
#     draw(response.json(), output_path="search_plan.png")