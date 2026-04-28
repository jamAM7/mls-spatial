from flows.navigation import prompt_menu
from api.cre import cre_search

def cre_flow():
    while (True):
        choice = prompt_menu (
            title="CRE Enquiry Menu",
            options={
                "1": "Get lot title status",
                "2": "Get lot area and perimeter",
                "x": "Exit",
            }
        )
        if choice is None:
            break
        elif choice == '1':
            cre_search()
        elif choice == '2':
            cre_search()