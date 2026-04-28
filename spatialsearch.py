import json
import re
from pathlib import Path
from datetime import date

from search import search
from export import to_geojson, fetch_cre_map_image
from drive import download_plans


def sanitise_address(address: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", address.lower()).strip("-")


# Run search
result = search("483 GEORGE STREET SYDNEY", 200)

# Create output folder with sanitised address and date
folder_name = f"{sanitise_address(result.address.resolved_string)}-{date.today().isoformat()}"
output_folder = Path("output") / folder_name
output_folder.mkdir(parents=True, exist_ok=True)

# Save GeoJSON
geojson = to_geojson(result)
with open(output_folder / "search_result.geojson", "w") as f:
    json.dump(geojson, f, indent=2)
print(f"Saved to {output_folder / 'search_result.geojson'}")

# Save summary.json
summary = {
    "address_input":    result.address.input_string,
    "address_resolved": result.address.resolved_string,
    "suburb":           result.address.suburb,
    "lga":              result.address.lga,
    "parish":           result.address.parish,
    "county":           result.address.county,
    "search_radius_m":  result.search_radius_m,
    "subject_lot":      f"{result.subject_lot.lot_number}//{result.subject_lot.plan_label}" if result.subject_lot else None,
    "lot_count":        len(result.nearby_lots),
    "plan_count":       len(result.plans),
    "mark_count":       len(result.survey_marks),
    "searched_at":      date.today().isoformat(),
}

with open(output_folder / "summary.json", "w") as f:
    json.dump(summary, f, indent=2)
print(f"Saved to {output_folder / 'summary.json'}")

# Save CRE map image
result.cre_map_image = fetch_cre_map_image(result, output_folder, map_radius_m=70)
if result.cre_map_image:
    print(f"Saved to {result.cre_map_image}")
else:
    print("CRE map image failed")

# Download plans from Google Drive
result = download_plans(result, output_folder)



















# from search import search
# import json
# from pathlib import Path
# # from search import search
# from export import to_geojson, fetch_cre_map_image
# import re 
# from datetime import date


# result = search("483 GEORGE STREET SYDNEY", 150)

# # Save GeoJSON
# output_folder = Path("output")
# output_folder.mkdir(parents=True, exist_ok=True)

# geojson = to_geojson(result)
# with open(output_folder / "output.json", "w") as f:
#     json.dump(geojson, f, indent=2)
# print("Saved to output/output.json")

# # Save CRE map image
# result.cre_map_image = fetch_cre_map_image(result, output_folder, map_radius_m=70)
# if result.cre_map_image:
#     print(f"Saved to {result.cre_map_image}")
# else:
#     print("CRE map image failed")




# #   STILL IN TESTING
# def sanitise_address(address: str) -> str:
#     return re.sub(r"[^a-z0-9]+", "-", address.lower()).strip("-")

# folder_name = f"{sanitise_address(result.address.resolved_string)}-{date.today().isoformat()}"
# output_folder = Path("output") / folder_name
# output_folder.mkdir(parents=True, exist_ok=True)

# from drive import download_plans
# result = download_plans(result, output_folder)