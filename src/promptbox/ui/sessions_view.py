"""
Renders the Streamlit UI for managing saved chat sessions.
"""
import streamlit as st
import pandas as pd
from typing import List
from promptbox.services.chat_service import ChatService
from promptbox.services.prompt_service import PromptService
from promptbox.services.character_service import CharacterService
from promptbox.models.data_models import ChatSessionData, ChatMessageData
from promptbox.ui.chat_view import _clear_chat_transient_state

# --- Callback Functions for Actions (More reliable than if-button blocks) ---

def _handle_session_delete(chat_service: ChatService, session_id: int):
    """Callback function to delete a session and reset UI state."""
    if chat_service.delete_chat_session(session_id):
        st.toast(f"Session {session_id} deleted successfully.", icon="✅")
        # Reset state to remove the deleted item from view
        st.session_state.selected_session_for_actions = None
        st.session_state.confirming_delete_session_id = None
    else:
        st.error(f"Failed to delete session {session_id}.")
        # Only reset the confirmation flag so the user can see the error
        st.session_state.confirming_delete_session_id = None

def _set_confirm_delete_state(session_id: int):
    """Callback to enter the 'confirming delete' mode."""
    st.session_state.confirming_delete_session_id = session_id

def _cancel_delete_state():
    """Callback to exit the 'confirming delete' mode."""
    st.session_state.confirming_delete_session_id = None

def _load_session_for_chat(session_details: ChatSessionData, prompt_service: PromptService, character_service: CharacterService):
    """Callback to load a session into the chat view."""
    _clear_chat_transient_state()
    st.session_state.loading_session_flag = True

    st.session_state.current_chat_session_id = session_details.id
    st.session_state.chat_provider = session_details.llm_provider
    st.session_state.chat_model = session_details.llm_model_name
    st.session_state.current_messages_data = list(session_details.messages)

    active_item_name = session_details.session_name

    loaded_prompt = None
    loaded_card = None
    if session_details.originating_prompt_id:
        loaded_prompt = prompt_service.get_prompt_by_id(session_details.originating_prompt_id)
        if loaded_prompt:
            st.session_state.active_prompt = loaded_prompt
            active_item_name = loaded_prompt.name
            st.session_state.chat_loaded_item_id = f"prompt_{loaded_prompt.id}"
            st.session_state.chat_origin_item_id = f"prompt_{loaded_prompt.id}"
    elif session_details.originating_card_id:
        loaded_card = character_service.get_card_by_id(session_details.originating_card_id)
        if loaded_card:
            st.session_state.active_card = loaded_card
            active_item_name = loaded_card.name
            st.session_state.chat_loaded_item_id = f"card_{loaded_card.id}"
            st.session_state.chat_origin_item_id = f"card_{loaded_card.id}"

    if not loaded_prompt and not loaded_card:
        st.session_state.chat_loaded_item_id = f"session_{session_details.id}_no_item"
        st.session_state.chat_origin_item_id = None
        st.warning("Original prompt/card for this session not found. Chat will load with existing messages.")
    
    st.session_state.active_item_name_for_chat_display = active_item_name

    st.session_state.chat_stage = "chatting"
    st.session_state.view = "chat"
    st.session_state.previous_view = "sessions"
    

def render_sessions_view(
    chat_service: ChatService,
    prompt_service: PromptService,
    character_service: CharacterService
):
    st.header("Saved Chat Sessions")

    # Initialize state variables if they don't exist
    if "selected_session_for_actions" not in st.session_state:
        st.session_state.selected_session_for_actions = None
    if "confirming_delete_session_id" not in st.session_state:
        st.session_state.confirming_delete_session_id = None

    sessions = chat_service.get_all_chat_sessions()

    if not sessions:
        st.info("No saved chat sessions found. Chats can be saved from the chat interface.")
        return

    df_data = []
    for s in sessions:
        df_data.append({
            "ID": s.id,
            "Name": s.session_name,
            "Provider": s.llm_provider or "N/A",
            "Model": s.llm_model_name or "N/A",
            "Origin Prompt ID": str(s.originating_prompt_id) if s.originating_prompt_id is not None else "N/A",
            "Origin Card ID": str(s.originating_card_id) if s.originating_card_id is not None else "N/A",
            "Last Updated": s.updated_at.strftime("%Y-%m-%d %H:%M") if s.updated_at else "N/A",
        })

    df = pd.DataFrame(df_data)
    if df.empty:
        st.info("No saved chat sessions to display.")
        return

    st.subheader("All Sessions")

    st.dataframe(
        df,
        hide_index=True,
        use_container_width=True,
        key="session_dataframe_display",
        on_select="rerun",
        selection_mode="single-row"
    )

    # Process dataframe selection
    if st.session_state.session_dataframe_display and st.session_state.session_dataframe_display.selection.rows:
        selected_row_index = st.session_state.session_dataframe_display.selection.rows[0]
        if selected_row_index < len(df):
            selected_session_id_from_df = int(df.iloc[selected_row_index]["ID"])
            if st.session_state.selected_session_for_actions != selected_session_id_from_df:
                st.session_state.selected_session_for_actions = selected_session_id_from_df
                st.session_state.confirming_delete_session_id = None # Clear delete confirmation if selection changes
                st.rerun()

    selected_session_to_display_id = st.session_state.selected_session_for_actions

    if selected_session_to_display_id:
        session_details = chat_service.get_chat_session(selected_session_to_display_id)
        if session_details:
            st.subheader(f"Details for Session: {session_details.session_name}")

            # --- Display Confirmation Dialog if in that state ---
            if st.session_state.confirming_delete_session_id == session_details.id:
                st.error(f"**Are you sure you want to permanently delete session '{session_details.session_name}'?**")
                c1_del, c2_del, _ = st.columns([1, 1, 3])
                c1_del.button(
                    "✅ Yes, Delete",
                    key=f"confirm_del_btn_{session_details.id}",
                    use_container_width=True,
                    on_click=_handle_session_delete,
                    args=(chat_service, session_details.id)
                )
                c2_del.button(
                    "❌ No, Cancel",
                    key=f"cancel_del_btn_{session_details.id}",
                    use_container_width=True,
                    on_click=_cancel_delete_state
                )
            # --- End Confirmation Dialog ---

            st.write(f"**Provider/Model:** {session_details.llm_provider or 'N/A'} / {session_details.llm_model_name or 'N/A'}")
            origin_info = []
            if session_details.originating_prompt_id:
                origin_info.append(f"Prompt ID: {session_details.originating_prompt_id}")
            if session_details.originating_card_id:
                origin_info.append(f"Card ID: {session_details.originating_card_id}")
            st.write(f"**Started from:** {', '.join(origin_info) if origin_info else 'N/A'}")
            st.write(f"**Last Updated:** {session_details.updated_at.strftime('%Y-%m-%d %H:%M:%S') if session_details.updated_at else 'N/A'}")

            with st.expander("View Messages", expanded=False):
                if session_details.messages:
                    for msg in sorted(session_details.messages, key=lambda m: m.message_order):
                        role_for_display = msg.role.lower()
                        if role_for_display == "human": role_for_display = "user"
                        if role_for_display == "ai": role_for_display = "assistant"
                        with st.chat_message(role_for_display):
                            st.markdown(msg.content)
                else:
                    st.info("No messages found for this session.")

            st.markdown("---")
            col1, col2, col3 = st.columns([1.5, 1.5, 2])
            with col1:
                st.button(
                    "🔄 Load & Continue Chat",
                    key=f"load_session_{session_details.id}",
                    use_container_width=True,
                    on_click=_load_session_for_chat,
                    args=(session_details, prompt_service, character_service)
                )

            with col2:
                st.button(
                    "🗑️ Delete Session",
                    type="primary",
                    key=f"delete_session_btn_{session_details.id}",
                    use_container_width=True,
                    on_click=_set_confirm_delete_state,
                    args=(session_details.id,)
                )
        else:
            st.error(f"Could not load details for session ID {selected_session_to_display_id}.")
            st.session_state.selected_session_for_actions = None
