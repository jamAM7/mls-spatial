from pathlib import Path
import json
from datetime import datetime

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

styles = getSampleStyleSheet()

TITLE_STYLE = ParagraphStyle(
    "TitleStyle",
    parent=styles["Title"],
    fontSize=18,
    leading=22,
    alignment=1,
    spaceAfter=12,
)

HEADER_STYLE = ParagraphStyle(
    "HeaderStyle",
    parent=styles["Heading2"],
    fontSize=12,
    spaceAfter=6,
    textColor=colors.HexColor("#1f3a5f"),
)


def load_json(path: Path):
    with open(path, "r") as f:
        return json.load(f)


def safe(v):
    return v if v not in (None, "") else "-"


# ─────────────────────────────────────────────────────────────────────────────
# Main entry
# ─────────────────────────────────────────────────────────────────────────────

def generate_report(output_folder: Path) -> Path:
    summary = load_json(output_folder / "summary.json")
    geojson = load_json(output_folder / "search_result.geojson")

    pdf_path = output_folder / "report.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)

    story = []

    # ─────────────────────────────────────────────────────────────────────
    # PAGE 1 — COVER
    # ─────────────────────────────────────────────────────────────────────
    story.append(Paragraph("MITCHELL LAND SURVEYORS PTY LTD", TITLE_STYLE))
    story.append(Paragraph("Proposal Search Report", HEADER_STYLE))
    story.append(Spacer(1, 10))

    crs_label = f'{summary.get("datum")} MGA Zone {summary.get("mga_zone")} (EPSG:{summary.get("epsg")})'

    cover_data = [
        ["Address", summary["address_resolved"]],
        ["Suburb", safe(summary.get("suburb"))],
        ["LGA", safe(summary.get("lga"))],
        ["Parish", safe(summary.get("parish"))],
        ["County", safe(summary.get("county"))],
        ["Subject Lot", safe(summary.get("subject_lot"))],
        ["Search Radius", f'{summary["search_radius_m"]} m'],
        ["Coordinate System", crs_label], 
        ["Lots Found", summary["lot_count"]],
        ["Plans Found", summary["plan_count"]],
        ["Survey Marks", summary["mark_count"]],
        ["Searched", summary["searched_at"]],
        ["Prepared By", "Mitchell Land Surveyors Pty Ltd"],
    ]

    table = Table(cover_data, colWidths=[80 * mm, 90 * mm])
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4c8fed")),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ])
    )

    story.append(table)
    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────
    # PAGE 2 — CRE MAP
    # ─────────────────────────────────────────────────────────────────────
    story.append(Paragraph("CADASTRAL REFERENCE MAP", HEADER_STYLE))
    story.append(Spacer(1, 10))

    cre_map = output_folder / "cre_map.png"
    if cre_map.exists():
        img = Image(str(cre_map))
        img.drawHeight = 180 * mm
        img.drawWidth = 180 * mm
        story.append(img)
    else:
        story.append(Paragraph("CRE map not available", styles["Normal"]))

    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            f"Source: NSW SIX Maps CRE MapServer. Coordinate system: {crs_label}.",
            styles["Normal"],
        )
    )

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────
    # PAGE 3 — SUBJECT LOT DETAIL
    # ─────────────────────────────────────────────────────────────────────
    story.append(Paragraph("SUBJECT LOT", HEADER_STYLE))

    subject = None
    for f in geojson["features"]:
        if f["properties"].get("is_subject"):
            subject = f["properties"]
            break

    subject_data = [
        ["Lot Number", safe(subject.get("lot_number")) if subject else "-"],
        ["Plan Label", safe(subject.get("plan_label")) if subject else "-"],
        ["Title Status", safe(subject.get("its_title_status_label")) if subject else "-"],
        ["Has Stratum", safe(subject.get("has_stratum")) if subject else "-"],
        ["Stratum Level", safe(subject.get("stratum_level_label")) if subject else "-"],
        ["Plan Area", f'{safe(subject.get("plan_lot_area"))} {safe(subject.get("plan_lot_area_units"))}' if subject else "-"],
    ]

    t = Table(subject_data, colWidths=[80 * mm, 90 * mm])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))

    story.append(t)
    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────
    # PAGE 4 — NEARBY LOTS TABLE
    # ─────────────────────────────────────────────────────────────────────
    story.append(Paragraph("NEARBY LOTS", HEADER_STYLE))

    headers = [
        "Lot", "Section", "Plan", "Title Status",
        "Area", "Surveyed", "Registered", "Plan Loaded"
    ]

    rows = [headers]

    for f in geojson["features"]:
        p = f["properties"]

        rows.append([
            p.get("lot_number"),
            p.get("section_number"),
            p.get("plan_label"),
            p.get("its_title_status_label"),
            f'{p.get("plan_lot_area") or "-"} {p.get("plan_lot_area_units") or ""}',
            "Yes" if p.get("is_surveyed") else "No",
            safe(p.get("registration_date")),
            "Yes" if p.get("plan_label") else "No",
        ])

    table = Table(rows, repeatRows=1)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))

    story.append(table)
    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────
    # PAGE 5 — SURVEY MARKS
    # ─────────────────────────────────────────────────────────────────────
    story.append(Paragraph("SURVEY MARKS", HEADER_STYLE))

    zone = summary.get("mga_zone", 56)

    mark_headers = [
        "Mark No", "Type", "Status", "Symbol",
        "Class", "AHD Height", "MGA Zone", f"MGA{zone} Easting", f"MGA{zone} Northing"
    ]
    # mark_headers = [
    #     "Mark No", "Type", "Status", "Symbol",
    #     "Class", "AHD Height", "Easting", "Northing"
    # ]

    mark_rows = [mark_headers]

    for f in geojson.get("features", []):
        if f["properties"].get("feature_type") != "survey_mark":
            continue

        p = f["properties"]

        mark_rows.append([
            p.get("mark_number"),
            p.get("mark_type"),
            p.get("mark_status"),
            p.get("mark_symbol_label"),
            p.get("gda_class"),
            p.get("ahd_height_label"),
            p.get("mga_zone"), # This is a test
            p.get("mga_easting_label"),
            p.get("mga_northing_label"),
        ])

    table = Table(mark_rows, repeatRows=1)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
    ]))

    story.append(table)
    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────
    # PAGE 6 — PLANS LIST
    # ─────────────────────────────────────────────────────────────────────
    story.append(Paragraph("PLANS REFERENCED", HEADER_STYLE))

    plans = []
    seen = set()

    for f in geojson["features"]:
        p = f["properties"]
        plan = p.get("plan_label")

        if plan and plan not in seen:
            seen.add(plan)
            plans.append([
                plan,
                p.get("plan_type", "-"),
                "Yes" if p.get("is_surveyed") else "No",
                safe(p.get("registration_date")),
                "Yes",
                f"{plan}.pdf"
            ])

    plans.insert(0, ["Plan", "Type", "Surveyed", "Registered", "Downloaded", "File"])

    table = Table(plans, repeatRows=1)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))

    story.append(table)

    # ─────────────────────────────────────────────────────────────────────
    # BUILD PDF
    # ─────────────────────────────────────────────────────────────────────
    doc.build(story)

    return pdf_path