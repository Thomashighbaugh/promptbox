import os
import sys
from typing import Callable

from promptbox.models.prompt import PromptData
from promptbox.services.prompt_service import PromptService
from promptbox.tui.components import (
    console,
    create_header,
    create_menu,
    create_prompt_list_table,
    create_prompt_panel,
)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_user_input(prompt: str = ">> ") -> str:
    return console.input(f"[bold green]{prompt}[/]").strip()

def confirm_action(question: str) -> bool:
    answer = get_user_input(f"{question} [y/N]: ").lower()
    return answer in ['y', 'yes']

def show_splash_screen():
    clear_screen()
    console.print(create_header())
    console.print("\nWelcome to promptbox! Your personal LLM prompt toolkit.", justify="center")
    console.print("Loading...", justify="center", style="dim")

def show_main_menu() -> str:
    clear_screen()
    console.print(create_header())
    menu_options = {
        'l': 'List & Manage Prompts',
        'n': 'Create New Prompt',
        's': 'Search Prompts (Full-Text)',
        'b': 'Backup Options',
        'q': 'Quit'
    }
    console.print(create_menu("Main Menu", menu_options))
    return get_user_input()

def create_prompt_wizard(prompt_service: PromptService):
    clear_screen()
    console.print(create_header())
    console.print(create_menu("Create New Prompt", {}))
    
    try:
        name = get_user_input("Enter a unique name for the prompt: ")
        if not name:
            console.print("[danger]Name cannot be empty.[/]")
            return

        folder = get_user_input("Enter folder (e.g., 'work/coding') [general]: ") or "general"
        description = get_user_input("Enter description (optional): ")
        tags_str = get_user_input("Enter tags, comma-separated (optional): ")
        tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]

        console.print("\nEnter prompt instructions. Use 'Ctrl+D' (Unix) or 'Ctrl+Z'+Enter (Windows) on a new line to finish.")
        
        console.print("[bold yellow]System Instruction (optional):[/]")
        system_instruction = sys.stdin.read().strip() or None
        
        console.print("[bold green]User Instruction (optional):[/]")
        user_instruction = sys.stdin.read().strip() or None
        
        console.print("[bold cyan]Assistant Instruction (optional):[/]")
        assistant_instruction = sys.stdin.read().strip() or None

        prompt_data = PromptData(
            name=name,
            folder=folder,
            description=description,
            tags=tags,
            system_instruction=system_instruction,
            user_instruction=user_instruction,
            assistant_instruction=assistant_instruction,
        )

        created_prompt = prompt_service.create_prompt(prompt_data)
        console.print(f"\n[bold green]Success![/] Prompt '{created_prompt.name}' created with ID {created_prompt.id}.")

    except Exception as e:
        console.print(f"[danger]An unexpected error occurred: {e}[/]")
    
    get_user_input("\nPress Enter to return to the main menu...")

def list_and_select_prompt(prompt_service: PromptService) -> PromptData | None:
    clear_screen()
    console.print(create_header())
    
    prompts = prompt_service.get_all_prompts()
    if not prompts:
        console.print("\nNo prompts found in the database.")
        get_user_input("\nPress Enter to return...")
        return None
        
    console.print(create_prompt_list_table(prompts))
    console.print("\nEnter a prompt ID to view details, or press Enter to return.")
    
    while True:
        choice = get_user_input("Enter ID: ")
        if not choice:
            return None
        if choice.isdigit():
            prompt = prompt_service.get_prompt_by_id(int(choice))
            if prompt:
                return prompt
            else:
                console.print("[warning]Invalid ID.[/]")
        else:
            console.print("[warning]Please enter a number.[/]")

def show_prompt_details_menu(prompt: PromptData, prompt_service: PromptService) -> str | None:
    clear_screen()
    console.print(create_header())
    console.print(create_prompt_panel(prompt))

    menu_options = {
        'c': 'Chat with this prompt',
        'e': 'Edit this prompt',
        'd': 'Delete this prompt',
        'i': 'Improve this prompt (AI)',
        'b': 'Back to prompt list'
    }
    console.print(create_menu(f"Actions for '{prompt.name}'", menu_options))
    return get_user_input()
