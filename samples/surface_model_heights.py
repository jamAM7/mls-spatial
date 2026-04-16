import datetime
import geodepy.constants as gc
import math
import requests


POINTS_OF_INTEREST = [
    # (name, latitude, longitude)
    ('TS2761', -36.4558204333, 148.2635020194),
    ('SS2331', -34.7374420851, 146.7816579835),
    ('OCEAN',  -34.7374420851, 156.7816579835)
]


def geographic_to_web_mercator(lat: float, lon: float, ellipsoid: gc.Ellipsoid = gc.grs80) -> tuple[float, float]:
    """
    Converts geodetic latitude and longitude to Web Mercator coordinates
    :param lat: latitude in decimal degrees
    :param lon: longitude in decimal degrees
    :param ellipsoid: reference ellipsoid details from GeodePy.constants
    :return: x, y tuple
    """
    radlat = math.radians(lat)
    radlon = math.radians(lon)

    x = ellipsoid.semimaj * radlon
    y = ellipsoid.semimaj * math.log(math.tan((math.pi / 4) + (radlat / 2)))

    return x, y


def get_nsw_surface_height(x: float, y: float) -> float | None:
    """
    Query the NSW 5m Elevation ImageServer for surface height.

    Parameters
    ----------
    x : coordinate in EPSG:3857 (Web Mercator)
    y : coordinate in EPSG:3857 (Web Mercator)

    Returns
    -------
    Elevation in metres, or None if no data is returned.
    """

    url = (
        "https://maps.six.nsw.gov.au/arcgis/rest/services/"
        "public/NSW_5M_Elevation/ImageServer/identify"
    )

    params = {
        "f": "json",
        "geometryType": "esriGeometryPoint",
        "geometry": f"{x},{y}",
        "returnGeometry": "false",
    }

    # Response can take some time!
    response = requests.get(url, params=params, timeout=120)
    response.raise_for_status()
    data = response.json()

    # Elevation value is returned in 'value', null values return as 'NoData'
    if "value" in data:
        if data["value"] == 'NoData':
            return None
        else:
            return float(data["value"])

    return None


if __name__ == "__main__":
    # Iterate through points of interest list, retrieve surface model heights where available, log in dictionary
    results = {}
    for name, lat, lon in POINTS_OF_INTEREST:
        print(f'{datetime.datetime.now()} querying height for ({name}, {lat}, {lon})')
        x, y  = geographic_to_web_mercator(lat, lon)
        ahd = get_nsw_surface_height(x, y)
        results[name] = {'name': name,
                         'lat': lat,
                         'lon': lon,
                         'ahd': ahd
                         }

    # Print results to screen
    print('\nResults:')
    for point in results.values():
        print(f'{point["name"]:10s} {point["ahd"]}')