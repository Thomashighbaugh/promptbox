"""
Main entry point for the Promptbox Streamlit application.
"""
import sys
from pathlib import Path
import streamlit as st

# Add src directory to Python path for module resolution
file_path = Path(__file__).resolve()
parent_of_package_dir = file_path.parent.parent
if str(parent_of_package_dir) not in sys.path:
    sys.path.insert(0, str(parent_of_package_dir))

from promptbox.core.config import settings
from promptbox.db.connection_manager import init_all_engines, create_all_db_and_tables
from promptbox.services.llm_service import LLMService
from promptbox.services.prompt_service import PromptService
from promptbox.services.character_service import CharacterService
from promptbox.services.backup_service import BackupService
from promptbox.services.chat_service import ChatService
from promptbox.ui.prompt_view import render_prompt_view
from promptbox.ui.character_view import render_character_view
from promptbox.ui.chat_view import render_chat_ui, _clear_chat_transient_state
from promptbox.ui.backup_view import render_backup_view
from promptbox.ui.sessions_view import render_sessions_view

@st.cache_resource
def get_llm_service():
    return LLMService()

@st.cache_resource
def get_prompt_service(_llm_service):
    return PromptService(_llm_service)

@st.cache_resource
def get_character_service():
    return CharacterService()

@st.cache_resource
def get_chat_service():
    return ChatService()

@st.cache_resource
def get_backup_service(_prompt_service, _character_service):
    return BackupService(_prompt_service, _character_service)


def initialize_app_state():
    """Initialize core application state and services if not already present."""
    if 'app_initialized' not in st.session_state:
        if not init_all_engines():
            st.error("Fatal Error: Failed to initialize one or more database engines. Application cannot start.")
            st.error("Please check your .env file for database paths and ensure directories are writable.")
            st.stop()

        try:
            create_all_db_and_tables()
        except Exception as e:
            st.error(f"Fatal Error: Failed to create/verify database tables: {e}")
            st.error("This might be due to database file issues or permissions. Check logs.")
            st.stop()
        
        st.session_state.app_initialized = True
        st.session_state.previous_view = "home"

    if "view" not in st.session_state:
        st.session_state.view = "home"


def clear_view_specific_session_state(new_view: str):
    """Clears session state specific to views when navigating."""
    if new_view != "prompts":
        if "selected_prompt_id" in st.session_state: del st.session_state.selected_prompt_id
        if "editing_prompt_data" in st.session_state: del st.session_state.editing_prompt_data
    if new_view != "characters":
        if "selected_card_id" in st.session_state: del st.session_state.selected_card_id
    if new_view != "sessions":
        if "selected_session_for_actions" in st.session_state: del st.session_state.selected_session_for_actions
        if "session_detail_id" in st.session_state: del st.session_state.session_detail_id


def handle_navigation(target_view: str):
    """Handles view changes, including checks for unsaved chat sessions."""
    current_view = st.session_state.get("view", "home")
    
    if current_view == "chat" and st.session_state.get("current_messages_data"):
        # If in chat with unsaved messages, trigger save dialog
        st.session_state.next_chat_stage = target_view
        st.session_state.chat_stage = "ask_save_dialog"
    else:
        # Normal navigation
        # MODIFIED: Removed the unexpected keyword argument 'clear_view'
        _clear_chat_transient_state() # Clear chat state if navigating away from chat
        clear_view_specific_session_state(target_view)
        st.session_state.previous_view = current_view
        st.session_state.view = target_view
    st.rerun()


def main():
    st.set_page_config(page_title="promptbox", layout="wide", initial_sidebar_state="expanded")
    
    initialize_app_state()

    llm_service = get_llm_service()
    prompt_service = get_prompt_service(llm_service)
    character_service = get_character_service()
    chat_service = get_chat_service()
    backup_service = get_backup_service(prompt_service, character_service)

    with st.sidebar:
        st.title("📦 promptbox")
        st.caption("Your Personal LLM Toolkit")
        st.markdown("---")

        if st.button("🏠 Home", use_container_width=True, key="nav_home"):
            handle_navigation("home")
        if st.button("📝 Prompts", use_container_width=True, key="nav_prompts"):
            handle_navigation("prompts")
        if st.button("🎭 Characters/Scenarios", use_container_width=True, key="nav_characters"):
            handle_navigation("characters")
        if st.button("💬 Chat Sessions", use_container_width=True, key="nav_sessions"):
            handle_navigation("sessions")
        if st.button("💾 Backups", use_container_width=True, key="nav_backups"):
            handle_navigation("backups")

        st.markdown("---")
        st.info(f"""
        **API Keys:** Set in `.env` file.
        **Data Root:** `{settings.APP_HOME}`
        **DBs:**
        - Prompts: `{settings.prompts_database_path.name}`
        - Cards: `{settings.cards_database_path.name}`
        - Sessions: `{settings.sessions_database_path.name}`
        Located in: `{settings.data_dir}`
        """)
        st.markdown("---")
        if st.button("⚠️ Clear ALL Session State", use_container_width=True, type="secondary", help="Resets UI state. Does not delete data. Use for debugging."):
            app_init_val = st.session_state.get('app_initialized', False)
            st.session_state.clear()
            st.session_state.app_initialized = app_init_val
            st.session_state.view = "home"
            st.rerun()

    current_view = st.session_state.get("view", "home")

    if current_view == "home":
        st.header("Welcome to Promptbox!")
        st.markdown("""
        **Promptbox** helps you create, manage, test, and organize your prompts for Large Language Models.
        Use the navigation panel on the left to explore its features.
        """)
        st.markdown(f"All application data, including databases and backups, is stored in subdirectories within `{settings.APP_HOME}`.")
    elif current_view == "prompts":
        render_prompt_view(prompt_service, llm_service)
    elif current_view == "characters":
        render_character_view(character_service)
    elif current_view == "sessions":
        render_sessions_view(chat_service, prompt_service, character_service)
    elif current_view == "backups":
        render_backup_view(backup_service)
    elif current_view == "chat":
        render_chat_ui(llm_service, chat_service)

if __name__ == "__main__":
    main()
