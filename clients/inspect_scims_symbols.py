"""
inspect_scims_symbols.py — DIAGNOSTIC
Hits both the drawingInfo and legend endpoints and reports what you actually have.
"""
import json, base64, requests
from pathlib import Path

BASE = "https://portal.spatial.nsw.gov.au/server/rest/services/SurveyMarkGDA2020/MapServer"

def fetch_drawing_info():
    resp = requests.get(f"{BASE}/0?f=json", timeout=10)
    resp.raise_for_status()
    infos = resp.json()["drawingInfo"]["renderer"]["uniqueValueInfos"]
    print(f"\n=== drawingInfo: {len(infos)} entries ===")
    for info in infos:
        sym = info["symbol"]
        print(f"  value={info['value']!r:30s}  type={sym['type']!r}  w={sym.get('width')}  h={sym.get('height')}")
    return infos

def fetch_legend():
    resp = requests.get(f"{BASE}/legend?f=json", timeout=10)
    resp.raise_for_status()
    layers = resp.json()["layers"]
    print(f"\n=== legend: {sum(len(l['legend']) for l in layers)} total entries across {len(layers)} layers ===")
    Path("symbol_dump").mkdir(exist_ok=True)
    for layer in layers:
        print(f"\n  Layer {layer['layerId']}: {layer['layerName']}")
        for entry in layer["legend"]:
            label = entry["label"]
            img   = entry.get("imageData", "")
            ct    = entry.get("contentType", "")
            print(f"    label={label!r:40s}  contentType={ct}  imgLen={len(img)}")
            if img:
                ext  = "png" if "png" in ct else "bin"
                safe = label.replace("/", "_").replace(" ", "_")
                Path(f"symbol_dump/{safe}.{ext}").write_bytes(base64.b64decode(img))

def upscale_symbols(target: int = 112):
    from PIL import Image

    Path("symbol_dump_2").mkdir(exist_ok=True)
    for path in Path("symbol_dump").glob("*.png"):
        img   = Image.open(path).convert("RGBA")
        r, g, b, a = img.split()
        rgb   = Image.merge("RGB", (r, g, b)).resize((target, target), Image.Resampling.LANCZOS)
        alpha = a.resize((target, target), Image.Resampling.NEAREST)
        rgb.putalpha(alpha)
        rgb.save(Path("symbol_dump_2") / path.name)
        print(f"  {path.name} → {target}x{target}")

if __name__ == "__main__":
    fetch_drawing_info()
    fetch_legend()
    print("\nUpscaling to symbol_dump_2 ...")
    upscale_symbols()
    print("Done.")