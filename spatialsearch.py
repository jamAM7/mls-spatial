from search import search

result = search("483 GEORGE STREET SYDNEY", 150)

if result is None:
    print("Search failed")
else:
    print(f"Address: {result.address.resolved_string}")
    print(f"Suburb: {result.address.suburb}")
    print(f"LGA: {result.address.lga}")
    print(f"Easting: {result.address.easting}")
    print(f"Northing: {result.address.northing}")

    print(f"\nSubject lot: {result.subject_lot.plan_label} — {result.subject_lot.lot_number}")

    print(f"\nNearby lots ({len(result.nearby_lots)}):")
    for lot in result.nearby_lots:
        subject_marker = " ← SUBJECT" if lot.is_subject else ""
        print(f"  {lot.plan_label} — {lot.lot_number} — {lot.its_title_status_label}{subject_marker}")

    print(f"\nPlans ({len(result.plans)}):")
    for plan in result.plans:
        print(f"  {plan.plan_label} — surveyed: {plan.is_surveyed} — {plan.registration_date}")

    print(f"\nSurvey marks ({len(result.survey_marks)}):")
    for mark in result.survey_marks:
        print(f"  {mark.mark_number} — {mark.mark_type} — {mark.gda_class}")





















# from flows.lot_plan_flow import lot_plan_section_flow
# from flows.survey_mark_flow import survey_mark_flow
# from flows.cre_flow import cre_flow
# from flows.navigation import prompt_menu

# while (True):
#         choice = prompt_menu (
#             title="Home Menu",
#             options={
#                 "1": "Lot/Plan/Section",
#                 "2": "Survey Mark",
#                 "3": "CRE Enquiry",
#                 "x": "Exit",
#             }
#         )
#         if choice is None:
#             break
#         elif choice == '1':
#             lot_plan_section_flow()
#         elif choice == '2':
#             survey_mark_flow()
#         elif choice == '3':
#             cre_flow()




# from api.address import get_address_coordinates
# from api.lot import get_lot_info
# from api.survey_marks import get_survey_mark_info
# from api.plan import get_plan_info
# from utils import expand_address


# address = expand_address("483 GEORGE STREET SYDNEY")
# address_object = get_address_coordinates(address)

# if address_object is None:
#     print("Address is none")
# if address_object:
#     lots = get_lot_info(address_object.easting, address_object.northing, 30)
#     if lots:
#         for lot in lots:
#             print(f"{lot.plan_label} — {lot.lot_number} — {lot.its_title_status_label}")
#             print(f"  geometry points: {len(lot.geometry)}")


#     print("\n" + "Survey Marks")
#     survey_marks = get_survey_mark_info(address_object.easting, address_object.northing, 100)
#     if survey_marks:
#         for survey_mark in survey_marks:
#             print(f"{survey_mark.mark_number} — {survey_mark.mark_type} — {survey_mark.mark_status}")
#             #print(f"  geometry points: {len(lot.geometry)}")

#     print("\n" + "Plan info")
#     plan = get_plan_info(lots[0].plan_label)
#     if plan:
#         print(f"{plan.plan_label} — {plan.plan_type} — {plan.plan_number}")
#         #print(f"  geometry points: {len(lot.geometry)}")


