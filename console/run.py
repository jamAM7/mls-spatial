"""
run.py — MLS Spatial Search Console
Interactive console for the surveyor to search cadastral data.

Usage:
    python console/run.py

Requirements:
    - venv activated
    - credentials.json in project root (for Google Drive plan download)
"""

import sys
import os
import re
import json
from pathlib import Path
from datetime import date


# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "clients"))

from service.search import search
from service.export import to_geojson, fetch_cre_map_image
from service.drive import download_plans
from service.report import generate_report
from clients.draw import draw
# from draw import draw  # type: ignore


# ── Helpers ───────────────────────────────────────────────────────────────────

def sanitise_address(address: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", address.lower()).strip("-")


def make_output_folder(resolved_address: str) -> Path:
    folder_name = f"{sanitise_address(resolved_address)}-{date.today().isoformat()}"
    folder = ROOT / "output" / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def print_header():
    print("\n" + "=" * 50)
    print("  MLS Spatial Search")
    print("=" * 50)


def print_help():
    print("""
HOW TO USE
----------
1. Enter a full NSW address when prompted
   Example: 483 George Street Sydney

2. Enter a search radius in metres
   Default is 200m if you press Enter

3. Choose what output you want

COMMANDS
--------
  q or quit  → exit
  h or help  → show this help
""")


def get_output_choice() -> str:
    print("\nWhat would you like? (all include pdf report)")
    print("  1. Drawn PNG only           (~15 seconds)")
    print("  2. CRE map only             (~20 seconds)")
    print("  3. Full output              (~3 minutes - includes plan downloads)")
    print("  4. Drawn PNG + CRE map      (~30 seconds)")
    choice = input("\nEnter choice [4]: ").strip()
    return choice if choice in ("1", "2", "3", "4") else "4"


def print_summary(result):
    print(f"\n✓ {result.address.resolved_string}")
    print(f"  Suburb:  {result.address.suburb or '-'}")
    print(f"  LGA:     {result.address.lga or '-'}")
    print(f"  Parish:  {result.address.parish or '-'}")
    print(f"  County:  {result.address.county or '-'}")
    print(f"  Datum:   {result.datum}")
    print(f"  EPSG:    {result.epsg}")
    if result.subject_lot:
        print(f"  Subject: {result.subject_lot.lot_number}//{result.subject_lot.plan_label}")
    print(f"  Lots:    {len(result.nearby_lots)}")
    print(f"  Plans:   {len(result.plans)}")
    print(f"  Marks:   {len(result.survey_marks)}")


def run_search(address: str, radius_m: int, datum: str):
    choice = get_output_choice()

    print(f"\nSearching '{address}' within {radius_m}m...")
    result = search(address, radius_m, datum=datum)

    if result is None:
        print("Address not found. Check the address and try again.")
        return

    print_summary(result)
    output_folder = make_output_folder(result.address.resolved_string)

    # Always save GeoJSON and summary
    geojson = to_geojson(result)
    with open(output_folder / "search_result.geojson", "w") as f:
        json.dump(geojson, f, indent=2)

    summary = {
        "address_input":    result.address.input_string,
        "address_resolved": result.address.resolved_string,
        "suburb":           result.address.suburb,
        "lga":              result.address.lga,
        "parish":           result.address.parish,
        "county":           result.address.county,
        "datum":            result.datum,
        "epsg":             result.epsg,
        "search_radius_m":  result.search_radius_m,
        "subject_lot":      f"{result.subject_lot.lot_number}//{result.subject_lot.plan_label}" if result.subject_lot else None,
        "lot_count":        len(result.nearby_lots),
        "plan_count":       len(result.plans),
        "mark_count":       len(result.survey_marks),
        "searched_at":      date.today().isoformat(),
    }
    with open(output_folder / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # Drawn PNG
    if choice in ("1", "4"):
        print("  Generating drawn PNG...")
        draw(geojson, output_path=str(output_folder / "search_plan.png"))

    # CRE map
    if choice in ("2", "4"):
        print("  Fetching CRE map...")
        result.cre_map_image = fetch_cre_map_image(result, output_folder, map_radius_m=radius_m, output_path=str(output_folder / "cre_map.png"))
        # if result.cre_map_image:
        #     print(f"  CRE map saved")

    # Full output including plan downloads
    if choice == "3":
        print("  Generating drawn PNG...")
        draw(geojson, output_path=str(output_folder / "search_plan.png"))
        print("  Fetching CRE map...")
        result.cre_map_image = fetch_cre_map_image(result, output_folder, map_radius_m=radius_m, output_path=str(output_folder / "cre_map.png"))
        print("  Downloading plans from Google Drive...")
        result = download_plans(result, output_folder)

    print("  Generating PDF report...")
    report_path = generate_report(output_folder)
    print(f"  Report saved to: {report_path}")
    print(f"\n  Output saved to: {output_folder}")


def main():
    print_header()
    print("\nType 'h' for help or 'q' to quit\n")

    while True:
        try:
            address = input("Enter address: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye.")
            break

        if not address:
            continue
        if address.lower() in ("q", "quit"):
            print("Goodbye.")
            break
        if address.lower() in ("h", "help"):
            print_help()
            continue

        try:
            radius_input = input("Enter radius in metres [200]: ").strip()
            radius_m = int(radius_input) if radius_input else 200
        except ValueError:
            print("Invalid radius — using 200m")
            radius_m = 200

        datum = input("Datum [GDA2020]: ").strip().upper() or "GDA2020"

        if datum not in ("GDA2020", "GDA94"):
            print("Invalid datum. Use GDA2020 or GDA94.")
            continue

        run_search(address, radius_m, datum)
        print()


if __name__ == "__main__":
    main()