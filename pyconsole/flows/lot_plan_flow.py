from flows.navigation import prompt_menu
from api.lot import get_lps
from api.plan import get_plan_info

def lot_plan_section_flow():
    while (True):
        choice = prompt_menu (
            title="Lot / Plan / Section Menu",
            options={
                "1": "Find L/P/S by Address",
                "2": "Return Plan Meta Data",
                "x": "Exit",
            }
        )
        if choice is None:
            break
        elif choice == '1':
            get_lps()
        elif choice == '2':
            get_plan_info()

