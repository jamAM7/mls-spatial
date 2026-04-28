from flows.navigation import prompt_menu
from api.survey_marks import survey_mark_search, get_survey_mark_by_number

def survey_mark_flow():
    while (True):
        choice = prompt_menu (
            title="Survey Mark Menu",
            options={
                "1": "Find marks by Address",
                "2": "Return meta data of mark",
                "x": "Exit",
            }
        )
        if choice is None:
            break
        elif choice == '1':
            survey_mark_search()
        elif choice == '2':
            get_survey_mark_by_number()