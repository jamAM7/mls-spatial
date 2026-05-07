# Built by search.py — it calls all api/ modules and assembles one SearchResult
# nearby_lots includes the subject lot
# plans is a deduplicated list — many lots share a plan, only include each plan once


from service.models import SearchResult, Address, Lot, Plan, SurveyMark
from service.utils import sanitise_address, epsg_from_mga_zone, mga_zone_from_longitude
from service.config import EPSG_CODES
from service.api.address import get_address_coordinates
from service.api.lot import get_lot_info
from service.api.plan import get_plan_info
from service.api.survey_marks import get_survey_mark_info



def search(address_input: str, radius_m: int, datum: str = "GDA2020") -> SearchResult | None:
    # Resolve address
    address_input = sanitise_address(address_input)

    # Pass 1 — WGS84 only, just to get longitude for zone detection
    address_geo = get_address_coordinates(address_input, out_sr=4326)
    if not address_geo:
        return None

    # Derive zone and EPSG from real longitude
    zone = mga_zone_from_longitude(address_geo.longitude)
    try:
        epsg = EPSG_CODES[(datum, zone)]
    except KeyError:
        raise ValueError(f"Unsupported datum/zone combination: {datum}, {zone}")

    # Pass 2 — correct projected coordinates + admin boundaries
    address = get_address_coordinates(address_input, out_sr=epsg)
    if not address:
        return None
    # address = get_address_coordinates(address_input )
    # if not address:
    #     return None
    
    # print(str(address.easting) + " and " + str(address.northing))
    
    # Get mga zone from lognitude
    # zone = mga_zone_from_longitude(address.longitude)
    # epsg = epsg_from_mga_zone(zone)

    # zone = mga_zone_from_longitude(address.longitude)

    # try:
    #     epsg = EPSG_CODES[(datum, zone)]
    # except KeyError:
    #     raise ValueError(f"Unsupported datum/zone combination: {datum}, {zone}")


    # Get subject lot — tight query at exact point
    subject_candidates = get_lot_info(address.easting, address.northing, epsg, distance=1)
    subject_lot = subject_candidates[0] if subject_candidates else None

    # Get all nearby lots
    lots = get_lot_info(address.easting, address.northing, epsg, radius_m) or []

    # Mark subject lot
    if subject_lot:
        for lot in lots:
            if lot.plan_label == subject_lot.plan_label and lot.lot_number == subject_lot.lot_number:
                lot.is_subject = True
                break

    # Get unique plans from nearby lots ---
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Deduplicate plan labels first
    seen_plan_labels = list({lot.plan_label for lot in lots})

    # Fetch all plans in parallel
    plans = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(get_plan_info, label): label for label in seen_plan_labels}
        for future in as_completed(futures):
            plan = future.result()
            if plan:
                plans.append(plan)


    # Get survey marks
    survey_marks = get_survey_mark_info(address.easting, address.northing, epsg, radius_m) or []

    

    return SearchResult(
        address         = address,
        subject_lot     = subject_lot,
        nearby_lots     = lots,
        plans           = plans,
        survey_marks    = survey_marks,
        search_radius_m = radius_m,
        cre_map_image   = None,
        epsg = epsg,
        datum = datum
    )


