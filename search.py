# Built by search.py — it calls all api/ modules and assembles one SearchResult
# nearby_lots includes the subject lot
# plans is a deduplicated list — many lots share a plan, only include each plan once


    # address: Address
    # subject_lot: Lot                        # the lot at the searched address
    # nearby_lots: list[Lot]                  # all lots within search_radius_m (includes subject_lot)
    # plans: list[Plan]                       # unique plans referenced by nearby_lots
    # survey_marks: list[SurveyMark]          # all marks within search_radius_m
    # search_radius_m: int
    # cre_map_image: Optional[Path] = None    # PNG saved from CRE MapServer export


from models import SearchResult, Address, Lot, Plan, SurveyMark
from utils import expand_address
from api.address import get_address_coordinates
from api.lot import get_lot_info
from api.plan import get_plan_info
from api.survey_marks import get_survey_mark_info



def search(address_input: str, radius_m: int) -> SearchResult | None:
    # Resolve address
    expanded = expand_address(address_input)
    address  = get_address_coordinates(expanded)
    if not address:
        return None

    # Get subject lot — tight query at exact point
    subject_candidates = get_lot_info(address.easting, address.northing, distance=1)
    subject_lot = subject_candidates[0] if subject_candidates else None

    # Get all nearby lots
    lots = get_lot_info(address.easting, address.northing, radius_m) or []

    # Mark subject lot
    if subject_lot:
        for lot in lots:
            if lot.plan_label == subject_lot.plan_label and lot.lot_number == subject_lot.lot_number:
                lot.is_subject = True
                break

    # Get unique plans from nearby lots
    plans = []
    seen_plan_labels = set()
    for lot in lots:
        if lot.plan_label not in seen_plan_labels:
            seen_plan_labels.add(lot.plan_label)
            plan = get_plan_info(lot.plan_label)
            if plan:
                plans.append(plan)

    # Get survey marks
    survey_marks = get_survey_mark_info(address.easting, address.northing, radius_m) or []

    return SearchResult(
        address         = address,
        subject_lot     = subject_lot,
        nearby_lots     = lots,
        plans           = plans,
        survey_marks    = survey_marks,
        search_radius_m = radius_m,
        cre_map_image   = None,
    )












# def search(address: str, radius_m: int) -> SearchResult:
#     address = expand_address("483 GEORGE STREET SYDNEY")
#     address = get_address_coordinates(address)

#     lots = get_lot_info(address.easting, address.northing, radius_m)
#     subject_lot = lots[0]

#     plans = []
#     seen_plan_labels = set()

#     for lot in lots:
#         if lot.plan_label not in seen_plan_labels:
#             seen_plan_labels.add(lot.plan_label)
#             plan = get_plan_info(lot.plan_label)
#             if plan:
#                 plans.append(plan)
    
#     survey_marks = get_survey_mark_info(address.easting, address.northing, radius_m)

#     return SearchResult(
#         address = address,
#         subject_lot = subject_lot,
#         nearby_lots = lots,
#         plans = plans,
#         survey_marks = survey_marks,
#         search_radius_m = radius_m,
#         cre_map_image = None
#     )

