from promptbox.services.llm_service import LLMService
from promptbox.services.prompt_service import PromptService
from promptbox.services.chat_service import ChatService
from promptbox.services.backup_service import BackupService
from promptbox.tui import menus
from promptbox.tui.chat_ui import ChatUI, select_llm_model
from promptbox.tui.components import console, create_prompt_panel
from promptbox.models.prompt import PromptData

class App:
    def __init__(self):
        self.llm_service = LLMService()
        self.prompt_service = PromptService(self.llm_service)
        self.chat_service = ChatService(self.llm_service, self.prompt_service)
        self.backup_service = BackupService(self.prompt_service)
        self.running = True

    def run(self):
        menus.show_splash_screen()
        import time
        time.sleep(1.5)
        while self.running:
            choice = menus.show_main_menu()
            self.route_main_menu(choice)
    
    def route_main_menu(self, choice: str):
        match choice.lower():
            case 'l':
                self.manage_prompts_flow()
            case 'n':
                menus.create_prompt_wizard(self.prompt_service)
            case 's':
                self.search_prompts_flow()
            case 'b':
                self.backup_flow()
            case 'q':
                self.running = False
                console.print("\nGoodbye!\n")
            case _:
                console.print("[warning]Invalid option. Please try again.[/]")
                menus.get_user_input("Press Enter to continue...")

    def manage_prompts_flow(self):
        while True:
            selected_prompt = menus.list_and_select_prompt(self.prompt_service)
            if not selected_prompt:
                break

            action = menus.show_prompt_details_menu(selected_prompt, self.prompt_service)
            
            if action == 'c':
                self.chat_flow(selected_prompt)
            elif action == 'e':
                console.print("[warning]Edit functionality is not yet implemented.[/]")
                menus.get_user_input()
            elif action == 'd':
                if menus.confirm_action(f"Are you sure you want to delete '{selected_prompt.name}'?"):
                    self.prompt_service.delete_prompt(selected_prompt.id)
                    console.print("[info]Prompt deleted.[/]")
                    menus.get_user_input()
                    break
            elif action == 'i':
                self.improve_prompt_flow(selected_prompt)
            elif action == 'b':
                continue
            else:
                break

    def improve_prompt_flow(self, prompt_data: PromptData):
        console.print("\nSelect an LLM to use for improving the prompt...")
        model_selection = select_llm_model(self.llm_service)
        if not model_selection:
            return

        provider, model_name = model_selection
        llm = self.llm_service.get_chat_model(provider, model_name)
        if not llm:
            console.print("[danger]Could not initialize the selected LLM.[/]")
            menus.get_user_input()
            return

        with console.status("[bold green]Asking AI for prompt improvements...[/]"):
            suggestion = self.prompt_service.improve_prompt(prompt_data.id, llm)
        
        if not suggestion:
            console.print("[warning]Could not get an improvement suggestion.[/]")
            menus.get_user_input()
            return
            
        menus.clear_screen()
        console.print(create_prompt_panel(prompt_data, title="Original Prompt"))
        
        suggested_prompt = PromptData(
            name="Suggested Improvement",
            folder=prompt_data.folder,
            system_instruction=suggestion.get("system_instruction"),
            user_instruction=suggestion.get("user_instruction"),
            assistant_instruction=suggestion.get("assistant_instruction"),
        )
        console.print(create_prompt_panel(suggested_prompt, title="[yellow]Suggested Improvement[/]"))
        
        if menus.confirm_action("Do you want to apply this improvement?"):
            prompt_data.system_instruction = suggestion.get("system_instruction")
            prompt_data.user_instruction = suggestion.get("user_instruction")
            prompt_data.assistant_instruction = suggestion.get("assistant_instruction")
            self.prompt_service.update_prompt(prompt_data.id, prompt_data)
            console.print("[info]Prompt has been updated.[/]")
        else:
            console.print("Improvement discarded.")
        menus.get_user_input()

    def chat_flow(self, prompt_data: PromptData):
        model_selection = select_llm_model(self.llm_service)
        if not model_selection:
            return
        provider, model_name = model_selection
        chat_ui = ChatUI(self.llm_service, self.chat_service, prompt_data, provider, model_name)
        chat_ui.run()
        
    def search_prompts_flow(self):
        menus.clear_screen()
        console.print(menus.create_header())
        query = menus.get_user_input("Enter search query: ")
        if not query:
            return
        results = self.prompt_service.search_prompts_full_text(query)
        if results:
            console.print(menus.create_prompt_list_table(results))
        else:
            console.print("No results found.")
        menus.get_user_input("\nPress Enter to return to the main menu...")

    def backup_flow(self):
        menus.clear_screen()
        console.print(menus.create_header())
        menu_options = {
            '1': 'Backup Database File',
            '2': 'Backup Prompts to Markdown Archive',
            'b': 'Back to Main Menu'
        }
        console.print(menus.create_menu("Backup Options", menu_options))
        choice = menus.get_user_input()
        if choice == '1':
            with console.status("[bold green]Creating database backup...[/]"):
                self.backup_service.backup_database_file()
        elif choice == '2':
            with console.status("[bold green]Creating markdown archive...[/]"):
                self.backup_service.backup_prompts_to_archive()
        
        if choice in ['1', '2']:
             menus.get_user_input("\nPress Enter to return...")
