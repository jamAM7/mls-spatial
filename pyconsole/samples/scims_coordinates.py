import json
import requests
import pathlib


API_URL = "https://portal.spatial.nsw.gov.au/server/rest/services/SurveyMarkGDA2020/MapServer/0/query"
SURVEY_MARKS = [
    'TS2761',
    'SS2331',
    'BM2331',  # Not found
]
# populate with desired output path
OUTPUT_DIR = pathlib.Path(r'')


def fetch_survey_mark(mark_type: str, mark_number: str) -> dict|None:
    """
    Fetch a survey mark feature from the NSW Spatial Services API.

    :param mark_type: Mark type (e.g. 'TS')
    :param mark_number: Mark number (e.g. '2761')
    :return: Feature dictionary or None if no result
    """
    params = {
        "where": f"marknumber = {mark_number} AND marktype = '{mark_type}'",
        "outFields": "*",
        "f": "json",
    }

    response = requests.get(API_URL, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    features = data.get("features", [])

    if not features:
        return None

    return features[0]['attributes']


def save_feature_to_file(feature: dict, filename: str | pathlib.Path) -> None:
    """
    Save a JSON feature to disk.
    """
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(feature, f, indent=4)


if __name__ == "__main__":
    results = {}
    for mark in SURVEY_MARKS:
        mark_type = mark[:2]
        mark_number = mark[2:]

        feature = fetch_survey_mark(mark_type, mark_number)
        results[mark] = feature

    output_file = OUTPUT_DIR / f"scims_coordinates.json"
    save_feature_to_file(results, output_file)