"""
fetch_scims_symbols.py — ONE-TIME UTILITY
==========================================
Reads upscaled SCIMS symbol PNGs from symbol_dump_2/ and prints a hardcoded
Python dict ready to paste into draw.py as _SYMBOL_DATA.

Run once after inspect_scims_symbols.py has populated symbol_dump_2/.

Copy the printed output and replace the _SYMBOL_DATA = {} block in draw.py.
"""

import base64
from pathlib import Path

LABEL_TO_SUFFIX = {
    "Established_GDA_+_Accurate_AHD": "R",
    "Established_GDA_Only":           "P",
    "Accurate_AHD_Only":              "G",
    "Approx_GDA_+_Accurate_AHD":      "C",
    "Approx_GDA_Only":                "B",
    "Unknown_GDA_+_AHD":              "U",
}

def filename_to_key(stem: str) -> str | None:
    """
    Convert filename stem to drawingInfo key e.g.
    'SS_Established_GDA_+_Accurate_AHD' → 'SSR'
    """
    for label, suffix in LABEL_TO_SUFFIX.items():
        if stem.endswith(label):
            mark_type = stem[: -(len(label) + 1)]  # strip '_<label>'
            return f"{mark_type}{suffix}"
    return None

def main():
    dump = Path("symbol_dump_2")
    if not dump.exists():
        print("ERROR: symbol_dump_2/ not found — run inspect_scims_symbols.py first.")
        return

    symbols = {}
    for path in sorted(dump.glob("*.png")):
        key = filename_to_key(path.stem)
        if key is None:
            print(f"# WARNING: could not map filename {path.name!r} to a key")
            continue
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        symbols[key] = b64

    print("# --- paste this block into draw.py ---")
    print("_SYMBOL_DATA = {")
    for key, b64 in symbols.items():
        print(f"    {key!r}: {b64!r},")
    print("}")
    print(f"\n# {len(symbols)} symbols total")

if __name__ == "__main__":
    main()





















# """
# fetch_scims_symbols.py — ONE-TIME UTILITY
# ==========================================
# Fetches the SCIMS mark symbol PNGs from the NSW MapServer renderer and prints
# a hardcoded Python dict ready to paste into draw.py as _SYMBOL_DATA.

# Run once:
#     python fetch_scims_symbols.py

# Copy the printed output and replace the _SYMBOL_DATA = {} block in draw.py.
# Never needs to be run again unless NSW change their symbology (they won't).
# """

# import json
# import requests

# URL = (
#     "https://portal.spatial.nsw.gov.au/server/rest/services/"
#     "SurveyMarkGDA2020/MapServer/0?f=json"
# )

# def main():
#     resp = requests.get(URL, timeout=10)
#     resp.raise_for_status()
#     infos = resp.json()["drawingInfo"]["renderer"]["uniqueValueInfos"]

#     print("# --- paste this block into draw.py ---")
#     print("_SYMBOL_DATA = {")
#     for info in infos:
#         value    = info["value"]
#         label    = info.get("label", value)
#         img_b64  = info["symbol"]["imageData"]
#         w        = info["symbol"]["width"]
#         h        = info["symbol"]["height"]
#         print(f'    # {label}')
#         print(f'    {value!r}: {img_b64!r},')
#     print("}")
#     print(f"\n# {len(infos)} symbols total")

# if __name__ == "__main__":
#     main()
