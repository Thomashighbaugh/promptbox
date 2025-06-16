"""
The main entry point for the promptbox application.
"""
from promptbox.db.database import create_db_and_tables
from promptbox.tui.app import App
from promptbox.tui.components import console

def start():
    """
    Initializes and runs the promptbox application.
    """
    try:
        create_db_and_tables()
        app = App()
        app.run()
    except Exception as e:
        console.print_exception(show_locals=True)
        console.log(f"[bold red]An unexpected critical error occurred: {e}[/]")
        console.input("\nPress Enter to exit.")

if __name__ == "__main__":
    start()
