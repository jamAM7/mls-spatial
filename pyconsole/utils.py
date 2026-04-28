NSW_STREET_ABBREVIATIONS = {
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


def expand_address(address: str) -> str:
    """
    Expands abbreviated street types in an NSW address.
    e.g. '1 PITT ST SYDNEY' -> '1 PITT STREET SYDNEY'
    """
    words = address.upper().split()
    expanded = []

    for word in words:
        expanded.append(NSW_STREET_ABBREVIATIONS.get(word, word))

    return " ".join(expanded)