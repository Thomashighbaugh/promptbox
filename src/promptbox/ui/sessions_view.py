"""
Renders the Streamlit UI for managing saved chat sessions.
"""
import streamlit as st
import pandas as pd
from typing import List
from promptbox.services.chat_service import ChatService
from promptbox.services.prompt_service import PromptService # MODIFIED: Added import
from promptbox.services.character_service import CharacterService # MODIFIED: Added import
from promptbox.models.data_models import ChatSessionData, ChatMessageData
from promptbox.ui.chat_view import _clear_chat_transient_state

def render_sessions_view(
    chat_service: ChatService,
    prompt_service: PromptService, # MODIFIED: Added parameter
    character_service: CharacterService # MODIFIED: Added parameter
):
    st.header("Saved Chat Sessions")

    if "session_detail_id" not in st.session_state: # Retained for potential future use if direct linking is needed
        st.session_state.session_detail_id = None
    if "selected_session_for_actions" not in st.session_state:
        st.session_state.selected_session_for_actions = None


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

    # Use st.dataframe for selection logic, which is slightly different from st.data_editor
    # For selection, we might need to handle it based on clicks or a dedicated column.
    # A simpler way with st.dataframe is to just display and use buttons for actions.
    # Or, use st.data_editor which has better built-in selection handling.
    # Let's try to get selection from st.dataframe if possible, or fall back to explicit buttons.

    # Event for dataframe row selection
    if 'session_df_select_event' not in st.session_state:
        st.session_state.session_df_select_event = None

    edited_df = st.dataframe( # Using st.dataframe for display
        df,
        hide_index=True,
        use_container_width=True,
        key="session_dataframe_display", # Unique key
        on_select="rerun", # Rerun on selection change
        selection_mode="single-row"
    )

    selected_session_id_from_df: int | None = None
    if st.session_state.session_dataframe_display and st.session_state.session_dataframe_display.selection.rows:
        selected_row_index = st.session_state.session_dataframe_display.selection.rows[0]
        if selected_row_index < len(df):
            selected_session_id_from_df = int(df.iloc[selected_row_index]["ID"])
            # Update a general selected ID if it changed
            if st.session_state.selected_session_for_actions != selected_session_id_from_df:
                st.session_state.selected_session_for_actions = selected_session_id_from_df
                # No rerun here, let the natural flow after st.dataframe handle it.

    # Use the consistent selected_session_for_actions for details display
    selected_session_to_display = st.session_state.selected_session_for_actions

    if selected_session_to_display:
        session_details = chat_service.get_chat_session(selected_session_to_display)
        if session_details:
            st.subheader(f"Details for Session: {session_details.session_name}")

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
            col1, col2, col3 = st.columns([1.5, 1.5, 2]) # Adjusted column widths
            with col1:
                if st.button("🔄 Load & Continue Chat", key=f"load_session_{session_details.id}", use_container_width=True):
                    _clear_chat_transient_state()
                    st.session_state.loading_session_flag = True

                    st.session_state.current_chat_session_id = session_details.id
                    st.session_state.chat_provider = session_details.llm_provider
                    st.session_state.chat_model = session_details.llm_model_name
                    st.session_state.current_messages_data = list(session_details.messages) # Ensure it's a new list

                    active_item_name = session_details.session_name # Fallback name

                    # MODIFIED: Load actual PromptData or CharacterCardData
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

                    if not loaded_prompt and not loaded_card: # Fallback if original item deleted or not found
                        st.session_state.chat_loaded_item_id = f"session_{session_details.id}_no_item"
                        st.session_state.chat_origin_item_id = None
                        st.warning("Original prompt/card for this session not found. Chat will load with existing messages.")
                    
                    st.session_state.active_item_name_for_chat_display = active_item_name # For display in chat_view

                    st.session_state.chat_stage = "chatting"
                    st.session_state.view = "chat"
                    st.session_state.previous_view = "sessions" # To return here from chat
                    st.rerun()

            with col2:
                if st.button("🗑️ Delete Session", type="primary", key=f"delete_session_btn_{session_details.id}", use_container_width=True):
                    confirm_delete_key = f"confirm_delete_session_{session_details.id}"
                    st.session_state[confirm_delete_key] = True # Trigger confirmation directly for simplicity here
                    st.rerun() # Rerun to show confirmation

            # Confirmation dialog for delete
            confirm_delete_key_check = f"confirm_delete_session_{session_details.id}"
            if st.session_state.get(confirm_delete_key_check, False):
                st.warning(f"Are you sure you want to delete session '{session_details.session_name}'? This cannot be undone.")
                c1_del, c2_del, _ = st.columns([1,1,3])
                if c1_del.button("Confirm Delete", key=f"confirm_del_btn_sess_final_{session_details.id}", use_container_width=True):
                    if chat_service.delete_chat_session(session_details.id):
                        st.success(f"Session '{session_details.session_name}' deleted.")
                        st.session_state.selected_session_for_actions = None # Clear selection
                        del st.session_state[confirm_delete_key_check]
                        st.rerun()
                    else:
                        st.error("Failed to delete session.")
                        del st.session_state[confirm_delete_key_check] # Reset confirm state
                if c2_del.button("Cancel Delete", key=f"cancel_del_btn_sess_{session_details.id}", use_container_width=True):
                    del st.session_state[confirm_delete_key_check]
                    st.rerun()
        else:
            st.error(f"Could not load details for session ID {selected_session_to_display}.")
            st.session_state.selected_session_for_actions = None
