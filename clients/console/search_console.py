"""
search_console.py — MLS Spatial Search Console
Interactive console for searching cadastral data via the MLS Spatial Search Service.

Requires the service to be running at http://localhost:8000
To start the service:
    cd pyconsole
    venv\\Scripts\\activate
    uvicorn server:app --port 8000
"""

import requests
import sys
import os
import re
from pathlib import Path
from datetime import date

SERVICE_URL = "http://localhost:8000"


def check_service() -> bool:
    """Check if the service is running."""
    try:
        response = requests.get(f"{SERVICE_URL}/health", timeout=3)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


def print_header():
    print("\n" + "=" * 50)
    print("  MLS Spatial Search")
    print("=" * 50)


def print_help():
    print("""
HOW TO USE
----------
1. Make sure the service is running first:
   - Open a terminal in the pyconsole folder
   - Activate venv: venv\\Scripts\\activate
   - Run: uvicorn server:app --port 8000
   - Leave that terminal open

2. Enter a full NSW address when prompted
   Example: 483 George Street Sydney

3. Enter a search radius in metres
   Default is 200m if you press Enter

4. Choose what output you want:
   1 - Quick drawn PNG only     (~15 seconds)
   2 - CRE map only             (~20 seconds)
   3 - Both drawn PNG + CRE map (~30 seconds)

COMMANDS
--------
  q or quit  → exit
  h or help  → show this help
""")


def sanitise_address(address: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", address.lower()).strip("-")


def make_output_folder(address: str) -> Path:
    folder_name = f"{sanitise_address(address)}-{date.today().isoformat()}"
    # Save output next to this script, not the working directory
    console_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    folder = console_dir / "output" / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def get_output_choice() -> str:
    print("\nWhat would you like?")
    print("  1. Quick drawn PNG only     (~15 seconds)")
    print("  2. CRE map only             (~20 seconds)")
    print("  3. Both drawn PNG + CRE map (~30 seconds)")
    choice = input("\nEnter choice: ").strip()
    return choice if choice in ("1", "2", "3") else "1"


def fetch_geojson(address: str, radius_m: int):
    """Call /search and return GeoJSON."""
    print(f"\nSearching '{address}' within {radius_m}m...")
    try:
        response = requests.get(
            f"{SERVICE_URL}/search",
            params={"address": address, "radius_m": radius_m},
            timeout=300
        )
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to service. Is it running?")
        return None

    if response.status_code == 404:
        print("Address not found. Check the address and try again.")
        return None

    if response.status_code != 200:
        print(f"Error: Service returned {response.status_code}")
        return None

    return response.json()


def print_summary(geojson: dict, address: str):
    search = geojson.get("search", {})
    print(f"\n✓ {search.get('address_resolved', address)}")
    print(f"  Suburb:  {search.get('suburb', '-')}")
    print(f"  LGA:     {search.get('lga', '-')}")
    print(f"  Parish:  {search.get('parish', '-')}")
    print(f"  County:  {search.get('county', '-')}")
    print(f"  Subject: {search.get('subject_lot', '-')}")
    print(f"  Lots:    {search.get('lot_count', 0)}")
    print(f"  Plans:   {search.get('plan_count', 0)}")
    print(f"  Marks:   {search.get('mark_count', 0)}")


def save_drawn_png(geojson: dict, output_folder: Path, address: str, radius_m: int):
    """Generate and save the drawn PNG via draw.py."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from draw import draw

        output_path = str(output_folder / "search_plan.png")
        draw(geojson, output_path=output_path)
        print(f"  Drawn PNG: {output_path}")
    except ImportError:
        print("  Note: draw.py not found — PNG drawing skipped")


def save_cre_map(address: str, radius_m: int, output_folder: Path):
    """Fetch CRE map PNG from /cre_map endpoint and save it."""
    print("  Fetching CRE map...")
    try:
        response = requests.get(
            f"{SERVICE_URL}/cre_map",
            params={"address": address, "radius_m": radius_m, "map_radius_m": 500},
            timeout=60
        )
    except requests.exceptions.ConnectionError:
        print("  Error: Cannot connect to service.")
        return

    if response.status_code != 200:
        print(f"  CRE map failed: {response.status_code}")
        return

    image_path = output_folder / "cre_map.png"
    image_path.write_bytes(response.content)
    print(f"  CRE map:   {image_path}")


def run_search(address: str, radius_m: int):
    """Run a search based on user's output choice."""
    choice = get_output_choice()

    # All options need the GeoJSON
    geojson = fetch_geojson(address, radius_m)
    if not geojson:
        return

    print_summary(geojson, address)

    output_folder = make_output_folder(geojson.get("search", {}).get("address_resolved", address))

    if choice in ("1", "3"):
        save_drawn_png(geojson, output_folder, address, radius_m)

    if choice in ("2", "3"):
        save_cre_map(address, radius_m, output_folder)

    print(f"\n  Output folder: {output_folder}")


def main():
    print_header()

    if not check_service():
        print("\n⚠ Service is not running at http://localhost:8000")
        print_help()
        print("Start the service then run this script again.")
        return

    print(f"\n✓ Service running at {SERVICE_URL}")
    print("Type 'h' for help or 'q' to quit\n")

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

        run_search(address, radius_m)
        print()


if __name__ == "__main__":
    main()




























# """
# search_console.py — MLS Spatial Search Console
# Interactive console for searching cadastral data via the MLS Spatial Search Service.

# Requires the service to be running at http://localhost:8000
# To start the service:
#     cd pyconsole
#     venv\\Scripts\\activate
#     uvicorn server:app --port 8000
# """

# import requests
# import sys
# import os

# SERVICE_URL = "http://localhost:8000"


# def check_service() -> bool:
#     """Check if the service is running."""
#     try:
#         response = requests.get(f"{SERVICE_URL}/health", timeout=3)
#         return response.status_code == 200
#     except requests.exceptions.ConnectionError:
#         return False


# def print_header():
#     print("\n" + "=" * 50)
#     print("  MLS Spatial Search")
#     print("=" * 50)


# def print_help():
#     print("""
# HOW TO USE
# ----------
# 1. Make sure the service is running first:
#    - Open a terminal in the pyconsole folder
#    - Activate venv: venv\\Scripts\\activate
#    - Run: uvicorn server:app --port 8000
#    - Leave that terminal open

# 2. Enter a full NSW address when prompted
#    Example: 483 George Street Sydney

# 3. Enter a search radius in metres
#    Default is 200m if you press Enter

# 4. Results will be saved as a PNG drawing

# COMMANDS
# --------
#   q or quit  → exit
#   h or help  → show this help
# """)


# def run_search(address: str, radius_m: int) -> bool:
#     """Run a search and save the PNG drawing."""
#     print(f"\nSearching '{address}' within {radius_m}m...")

#     try:
#         response = requests.get(
#             f"{SERVICE_URL}/search",
#             params={"address": address, "radius_m": radius_m},
#             timeout=300
#         )
#     except requests.exceptions.ConnectionError:
#         print("Error: Cannot connect to service. Is it running?")
#         return False

#     if response.status_code == 404:
#         print("Address not found. Check the address and try again.")
#         return False

#     if response.status_code != 200:
#         print(f"Error: Service returned {response.status_code}")
#         return False

#     geojson = response.json()
#     search  = geojson.get("search", {})

#     print(f"\n✓ {search.get('address_resolved', address)}")
#     print(f"  Suburb:  {search.get('suburb', '-')}")
#     print(f"  LGA:     {search.get('lga', '-')}")
#     print(f"  Parish:  {search.get('parish', '-')}")
#     print(f"  County:  {search.get('county', '-')}")
#     print(f"  Subject: {search.get('subject_lot', '-')}")
#     print(f"  Lots:    {search.get('lot_count', 0)}")
#     print(f"  Plans:   {search.get('plan_count', 0)}")
#     print(f"  Marks:   {search.get('mark_count', 0)}")

#     # Save PNG drawing
#     try:
#         sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
#         from draw import draw

#         safe_address = address.lower().replace(" ", "_")[:40]
#         output_path  = f"{safe_address}_{radius_m}m.png"
#         draw(geojson, output_path=output_path)
#         print(f"  Drawing: {output_path}")
#     except ImportError:
#         print("  Note: draw.py not found — PNG drawing skipped")

#     return True


# def main():
#     print_header()

#     # Check service is running
#     if not check_service():
#         print("\n⚠ Service is not running at http://localhost:8000")
#         print_help()
#         print("Start the service then run this script again.")
#         return

#     print(f"\n✓ Service running at {SERVICE_URL}")
#     print("Type 'h' for help or 'q' to quit\n")

#     while True:
#         # Address input
#         try:
#             address = input("Enter address: ").strip()
#         except (KeyboardInterrupt, EOFError):
#             print("\nGoodbye.")
#             break

#         if not address:
#             continue

#         if address.lower() in ("q", "quit"):
#             print("Goodbye.")
#             break

#         if address.lower() in ("h", "help"):
#             print_help()
#             continue

#         # Radius input
#         try:
#             radius_input = input("Enter radius in metres [200]: ").strip()
#             radius_m = int(radius_input) if radius_input else 200
#         except ValueError:
#             print("Invalid radius — using 200m")
#             radius_m = 200

#         run_search(address, radius_m)
#         print()


# if __name__ == "__main__":
#     main()