"""
Main entry point for the Promptbox Streamlit application.
"""
import sys
from pathlib import Path

# Add src directory to Python path for module resolution
file_path = Path(__file__).resolve()
src_path = file_path.parent.parent # Should point to the 'src' directory
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import streamlit as st
from promptbox.core.config import settings # Ensure settings are loaded early
from promptbox.db.database import init_engine, create_db_and_tables
from promptbox.services.llm_service import LLMService
from promptbox.services.prompt_service import PromptService
from promptbox.services.character_service import CharacterService
from promptbox.services.backup_service import BackupService
from promptbox.services.chat_service import ChatService
from promptbox.ui.prompt_view import render_prompt_view
from promptbox.ui.character_view import render_character_view
from promptbox.ui.chat_view import render_chat_ui, _clear_chat_transient_state # Import helper
from promptbox.ui.backup_view import render_backup_view
from promptbox.ui.sessions_view import render_sessions_view # New import

def initialize_services():
    """Initialize and cache services in Streamlit's session state."""
    if 'llm_service' not in st.session_state:
        st.session_state.llm_service = LLMService()
    if 'prompt_service' not in st.session_state:
        # LLMService is optional for PromptService unless improving prompts
        st.session_state.prompt_service = PromptService(st.session_state.llm_service)
    if 'character_service' not in st.session_state:
        st.session_state.character_service = CharacterService()
    if 'chat_service' not in st.session_state:
        # ChatService does not directly need LLMService or PromptService in its constructor
        # based on the refactored version. LLMService is passed to chat_view.
        st.session_state.chat_service = ChatService()
    if 'backup_service' not in st.session_state:
        st.session_state.backup_service = BackupService(
            st.session_state.prompt_service, st.session_state.character_service
            # ChatService could be added if backups were to include individual chat md exports directly from backup_view
        )

def clear_app_specific_session_state(preserve_services=True, preserve_view=False):
    """Clears most of the session state, optionally preserving services and current view."""
    keys_to_preserve = []
    if preserve_services:
        keys_to_preserve.extend(['llm_service', 'prompt_service', 'character_service', 'backup_service', 'chat_service'])
    if preserve_view and 'view' in st.session_state:
        keys_to_preserve.append('view')

    # Also preserve Streamlit's internal keys if necessary, though usually not an issue
    # streamlit_internal_keys = [k for k in st.session_state.keys() if k.startswith("streamlit_")]
    # keys_to_preserve.extend(streamlit_internal_keys)

    for key in list(st.session_state.keys()):
        if key not in keys_to_preserve:
            del st.session_state[key]
    
    # Specifically clear chat transient state if it exists, as it's complex
    _clear_chat_transient_state()


def main():
    st.set_page_config(page_title="promptbox", layout="wide", initial_sidebar_state="expanded")

    # Initialize database
    if not init_engine():
        st.error("Failed to initialize database engine. Application cannot start.")
        st.stop()
    
    # Create tables (idempotent)
    try:
        create_db_and_tables()
    except Exception as e:
        st.error(f"Failed to create database tables: {e}. Check database connection and permissions.")
        st.stop()

    # Initialize services
    initialize_services()
    llm_service = st.session_state.llm_service
    prompt_service = st.session_state.prompt_service
    character_service = st.session_state.character_service
    backup_service = st.session_state.backup_service
    chat_service = st.session_state.chat_service

    if "view" not in st.session_state:
        st.session_state.view = "home" # Default view

    # --- Sidebar Navigation ---
    with st.sidebar:
        st.title("📦 promptbox")
        st.caption("Your Personal LLM Toolkit")
        st.markdown("---")

        if st.button("🏠 Home", use_container_width=True, key="nav_home"):
            if st.session_state.view == "chat" and st.session_state.get("current_messages_data"):
                st.session_state.next_chat_stage = "home"
                st.session_state.chat_stage = "ask_save_dialog" # Ask to save before leaving chat
            else:
                st.session_state.view = "home"
                clear_app_specific_session_state(preserve_services=True, preserve_view=True)
            st.rerun()

        if st.button("📝 Prompts", use_container_width=True, key="nav_prompts"):
            if st.session_state.view == "chat" and st.session_state.get("current_messages_data"):
                st.session_state.next_chat_stage = "prompts"
                st.session_state.chat_stage = "ask_save_dialog"
            else:
                st.session_state.view = "prompts"
                # Minimal clearing, prompt_view manages its own state well
                if "selected_prompt_id" in st.session_state: del st.session_state.selected_prompt_id 
            st.rerun()

        if st.button("🎭 Characters/Scenarios", use_container_width=True, key="nav_characters"):
            if st.session_state.view == "chat" and st.session_state.get("current_messages_data"):
                st.session_state.next_chat_stage = "characters"
                st.session_state.chat_stage = "ask_save_dialog"
            else:
                st.session_state.view = "characters"
                if "selected_card_id" in st.session_state: del st.session_state.selected_card_id
            st.rerun()

        if st.button("💬 Chat Sessions", use_container_width=True, key="nav_sessions"): # New "Sessions" Page
            if st.session_state.view == "chat" and st.session_state.get("current_messages_data"):
                st.session_state.next_chat_stage = "sessions"
                st.session_state.chat_stage = "ask_save_dialog"
            else:
                st.session_state.view = "sessions"
                if "session_detail_id" in st.session_state: del st.session_state.session_detail_id
            st.rerun()

        if st.button("💾 Backups", use_container_width=True, key="nav_backups"):
            if st.session_state.view == "chat" and st.session_state.get("current_messages_data"):
                st.session_state.next_chat_stage = "backups"
                st.session_state.chat_stage = "ask_save_dialog"
            else:
                st.session_state.view = "backups"
            st.rerun()
        
        st.markdown("---")
        st.info(f"""
        **API Keys:** Set in `.env` file.
        **Data Path:** `{settings.APP_HOME}`
        """)

    # --- Main Page Content based on View ---
    if st.session_state.view == "home":
        st.header("Welcome to Promptbox!")
        st.markdown("""
        **Promptbox** helps you create, manage, test, and organize your prompts for Large Language Models.
        
        Use the navigation panel on the left to:
        - **📝 Manage Prompts:** Create, edit, and organize your prompt templates.
        - **🎭 Manage Characters/Scenarios:** Define reusable personas or scenario instructions.
        - **💬 View Chat Sessions:** Review and continue your past conversations.
        - **💾 Create Backups:** Safeguard your prompt library and database.

        Start by creating a new prompt or character, or explore existing ones!
        """)
        st.markdown(f"All application data, including the database (`promptbox.db`) and backups, is stored in `{settings.APP_HOME}`.")


    elif st.session_state.view == "prompts":
        render_prompt_view(prompt_service, llm_service)

    elif st.session_state.view == "characters":
        render_character_view(character_service)
    
    elif st.session_state.view == "sessions": # New View
        render_sessions_view(chat_service)

    elif st.session_state.view == "backups":
        render_backup_view(backup_service)

    elif st.session_state.view == "chat":
        # Chat view manages its own item loading through active_prompt/active_card or loaded session
        render_chat_ui(llm_service, chat_service)

if __name__ == "__main__":
    main()
