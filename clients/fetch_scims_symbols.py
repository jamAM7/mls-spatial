"""
fetch_scims_symbols.py — ONE-TIME UTILITY
==========================================
Fetches the SCIMS mark symbol PNGs from the NSW MapServer renderer and prints
a hardcoded Python dict ready to paste into draw.py as _SYMBOL_DATA.

Run once:
    python fetch_scims_symbols.py

Copy the printed output and replace the _SYMBOL_DATA = {} block in draw.py.
Never needs to be run again unless NSW change their symbology (they won't).
"""

import json
import requests

URL = (
    "https://portal.spatial.nsw.gov.au/server/rest/services/"
    "SurveyMarkGDA2020/MapServer/0?f=json"
)

def main():
    resp = requests.get(URL, timeout=10)
    resp.raise_for_status()
    infos = resp.json()["drawingInfo"]["renderer"]["uniqueValueInfos"]

    print("# --- paste this block into draw.py ---")
    print("_SYMBOL_DATA = {")
    for info in infos:
        value    = info["value"]
        label    = info.get("label", value)
        img_b64  = info["symbol"]["imageData"]
        w        = info["symbol"]["width"]
        h        = info["symbol"]["height"]
        print(f'    # {label}')
        print(f'    {value!r}: {img_b64!r},')
    print("}")
    print(f"\n# {len(infos)} symbols total")

if __name__ == "__main__":
    main()
