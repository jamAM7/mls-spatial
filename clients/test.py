import requests, pathlib

# The url field is a resource ID fetchable from the MapServer images endpoint
# We can request it at any pixel size
RESOURCE_ID = "96dd0c1ba1737ae625350dd1010c38e3"

# Fetch at 64x64
resp = requests.get(
    "https://portal.spatial.nsw.gov.au/server/rest/services/"
    "SurveyMarkGDA2020/MapServer/images/" + RESOURCE_ID,
    timeout=10
)
print(resp.status_code)
print(resp.headers.get("content-type"))
pathlib.Path("test_symbol.png").write_bytes(resp.content)
print(f"Saved {len(resp.content)} bytes")