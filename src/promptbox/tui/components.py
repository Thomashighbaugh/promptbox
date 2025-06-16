"""
Contains reusable TUI components built with the Rich library.

These functions generate common UI elements like headers, panels, and tables
to ensure a consistent look and feel across the application.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from promptbox.models.prompt import PromptData

# A custom theme for consistent styling
custom_theme = Theme({
    "info": "dim cyan",
    "warning": "magenta",
    "danger": "bold red",
    "header": "bold white on blue",
    "title": "bold yellow",
    "menu": "cyan",
    "menu_key": "bold cyan",
    "menu_text": "white",
    "panel_border": "dim blue",
})

console = Console(theme=custom_theme)

def create_header() -> Panel:
    """Creates the main application header."""
    header_text = Text("promptbox v0.1.0", justify="center", style="header")
    return Panel(header_text, style="header")

def create_prompt_panel(prompt: PromptData, title: str | None = None) -> Panel:
    """
    Creates a detailed, styled panel to display a single prompt.
    """
    panel_title = title if title else f"[{'title' if title else 'white'}]{prompt.name}[/]"
    
    content = Text()
    content.append("Folder: ", style="bold")
    content.append(f"{prompt.folder}\n", style="info")
    content.append("Tags: ", style="bold")
    content.append(f"{', '.join(prompt.tags)}\n\n", style="info")
    
    if prompt.description:
        content.append(f"{prompt.description}\n", style="italic")
        content.append("-" * 20 + "\n\n")

    if prompt.system_instruction:
        content.append("System Instruction:\n", style="bold yellow")
        content.append(f"{prompt.system_instruction}\n\n")

    if prompt.user_instruction:
        content.append("User Instruction:\n", style="bold green")
        content.append(f"{prompt.user_instruction}\n\n")

    if prompt.assistant_instruction:
        content.append("Assistant Instruction:\n", style="bold cyan")
        content.append(f"{prompt.assistant_instruction}\n")

    return Panel(
        content,
        title=panel_title,
        border_style="panel_border",
        expand=False
    )

def create_prompt_list_table(prompts: list[PromptData]) -> Table:
    """
    Creates a table to display a list of prompts.
    """
    table = Table(title="Available Prompts", border_style="panel_border")
    table.add_column("ID", style="dim", width=5, justify="right")
    table.add_column("Name", style="bold white", no_wrap=True)
    table.add_column("Folder", style="cyan")
    table.add_column("Description", style="italic", no_wrap=True)

    for p in prompts:
        table.add_row(
            str(p.id),
            p.name,
            p.folder,
            p.description or ""
        )
    return table

def create_menu(title: str, options: dict[str, str]) -> Panel:
    """
    Creates a generic menu panel.
    
    Args:
        title: The title of the menu.
        options: A dictionary where keys are the option key (e.g., 'e')
                 and values are the description (e.g., 'Edit Prompt').

    Returns:
        A Rich Panel object for the menu.
    """
    # CORRECTED LOGIC: Build a single string with markup.
    # The Panel's content will be this string, which the console will then parse.
    menu_string = ""
    for key, text in options.items():
        menu_string += f"  [menu_key]({key})[/] - [menu_text]{text}[/]\n"
    
    return Panel(
        menu_string, # Pass the string directly
        title=f"[{'title'}]{title}[/]",
        border_style="panel_border"
    )
