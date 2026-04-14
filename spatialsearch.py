from search import search
import json
from pathlib import Path
from search import search
from export import to_geojson, fetch_cre_map_image

result = search("483 GEORGE STREET SYDNEY", 150)

# Save GeoJSON
output_folder = Path("output")
output_folder.mkdir(parents=True, exist_ok=True)

geojson = to_geojson(result)
with open(output_folder / "output.json", "w") as f:
    json.dump(geojson, f, indent=2)
print("Saved to output/output.json")

# Save CRE map image
result.cre_map_image = fetch_cre_map_image(result, output_folder, map_radius_m=70)
if result.cre_map_image:
    print(f"Saved to {result.cre_map_image}")
else:
    print("CRE map image failed")