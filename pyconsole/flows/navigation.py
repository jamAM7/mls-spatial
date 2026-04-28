def exit_loop(key):
    if (key == 'x' or key == 'X'):
        return True
    else:
        return False
    

def prompt_menu(title, options):
    while True:
        print(f"\n{title}")
        for key, label in options.items():
            print(f"  {key}: {label}")
        
        answer = input("Enter choice: ").strip().lower()
        
        if exit_loop(answer):
            return None
        
        if answer in options:
            return answer
        
        print("Invalid choice, try again")