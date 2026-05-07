import re

_NSW_STREET_ABBREVIATIONS = {
    "ST":   "STREET",
    "RD":   "ROAD",
    "AVE":  "AVENUE",
    "AV":   "AVENUE",
    "DR":   "DRIVE",
    "PL":   "PLACE",
    "CT":   "COURT",
    "CL":   "CLOSE",
    "CR":   "CRESCENT",
    "CRES": "CRESCENT",
    "HWY":  "HIGHWAY",
    "PDE":  "PARADE",
    "TCE":  "TERRACE",
    "LN":   "LANE",
    "BLVD": "BOULEVARD",
    "GR":   "GROVE",
    "ESP":  "ESPLANADE",
    "CCT":  "CIRCUIT",
    "CIRC": "CIRCUIT",
    "WAY":  "WAY",
    "SQ":   "SQUARE",
    "BVD":  "BOULEVARD",
}

_AUSTRALIAN_STATES = {"NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"}


def _expand_address(address: str) -> str:
    """Expands abbreviated street types. Private — call sanitise_address() instead."""
    words = address.upper().split()
    return " ".join(_NSW_STREET_ABBREVIATIONS.get(w, w) for w in words)


def sanitise_address(address: str) -> str:
    """
    Cleans and normalises a user-supplied NSW address string.
    Handles commas, state abbreviations, postcodes and street abbreviations.
    e.g. '87 Bunarba Rd, Gymea Bay NSW 2227' -> '87 BUNARBA ROAD GYMEA BAY'
    """
    # Uppercase
    address = address.upper()

    # Strip commas
    address = address.replace(",", " ")

    # Strip trailing 4-digit postcode
    address = re.sub(r'\b\d{4}\b\s*$', '', address)

    # Strip trailing state abbreviations
    pattern = r'\b(' + '|'.join(_AUSTRALIAN_STATES) + r')\b\s*$'
    address = re.sub(pattern, '', address)

    # Normalise whitespace
    address = ' '.join(address.split())

    # Expand street abbreviations
    return _expand_address(address)



def mga_zone_from_longitude(longitude: float) -> int:
    if longitude < 144:
        return 54
    elif longitude < 150:
        return 55
    else:
        return 56


def epsg_from_mga_zone(zone: int, datum: str = "GDA2020") -> int:
    if datum == "GDA2020":
        return 7850 + zone   # 7854, 7855, 7856
    elif datum == "GDA94":
        return 28300 + zone  # 28354, 28355, 28356
    else:
        raise ValueError(f"Unsupported datum: {datum}")