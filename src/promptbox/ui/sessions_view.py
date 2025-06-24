"""
Renders the Streamlit UI for managing saved chat sessions.
"""
import streamlit as st
import pandas as pd
from typing import List
from promptbox.services.chat_service import ChatService
from promptbox.models.data_models import ChatSessionData, ChatMessageData # For type hinting if needed elsewhere
from promptbox.ui.chat_view import convert_to_langchain_message, convert_from_langchain_message, _clear_chat_transient_state # For loading session

def render_sessions_view(chat_service: ChatService):
    st.header("Saved Chat Sessions")

    if "session_detail_id" not in st.session_state:
        st.session_state.session_detail_id = None

    sessions = chat_service.get_all_chat_sessions() # These don't include messages by default

    if not sessions:
        st.info("No saved chat sessions found. Chats can be saved from the chat interface.")
        return

    # Create a DataFrame for display
    df_data = []
    for s in sessions:
        df_data.append({
            "ID": s.id,
            "Name": s.session_name,
            "Provider": s.llm_provider,
            "Model": s.llm_model_name,
            "Origin Prompt ID": s.originating_prompt_id if s.originating_prompt_id is not None else "N/A",
            "Origin Card ID": s.originating_card_id if s.originating_card_id is not None else "N/A",
            "Last Updated": s.updated_at.strftime("%Y-%m-%d %H:%M") if s.updated_at else "N/A",
        })
    
    df = pd.DataFrame(df_data)

    st.subheader("All Sessions")
    
    # Use st.dataframe for selection
    st.dataframe(
        df,
        hide_index=True,
        use_container_width=True,
        key="session_selector",
        on_select="rerun",
        selection_mode="single-row"
    )

    selected_session_id: int | None = None
    if 'session_selector' in st.session_state and st.session_state.session_selector.selection.rows:
        selected_index = st.session_state.session_selector.selection.rows[0]
        if selected_index < len(df):
            selected_session_id = int(df.iloc[selected_index]['ID'])
            # Store it also in a more general session state variable if needed outside this view
            st.session_state.selected_session_for_actions = selected_session_id 


    if selected_session_id:
        session_details = chat_service.get_chat_session(selected_session_id) # Fetches with messages
        if session_details:
            st.subheader(f"Details for Session: {session_details.session_name}")
            
            # Display some metadata
            st.write(f"**Provider/Model:** {session_details.llm_provider} / {session_details.llm_model_name}")
            if session_details.originating_prompt_id:
                st.write(f"**Started from Prompt ID:** {session_details.originating_prompt_id}")
            if session_details.originating_card_id:
                st.write(f"**Started from Card ID:** {session_details.originating_card_id}")
            st.write(f"**Last Updated:** {session_details.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")

            with st.expander("View Messages", expanded=False):
                if session_details.messages:
                    for msg in sorted(session_details.messages, key=lambda m: m.message_order):
                        role_for_display = "user" if msg.role == "user" else ("assistant" if msg.role == "assistant" else "system")
                        with st.chat_message(role_for_display):
                            st.markdown(msg.content)
                else:
                    st.info("No messages found for this session (this might indicate an issue or an empty session).")

            st.markdown("---")
            col1, col2, col3 = st.columns([1,1,2])
            with col1:
                if st.button("🔄 Load & Continue Chat", key=f"load_session_{session_details.id}", use_container_width=True):
                    # Prepare session state for chat_view
                    _clear_chat_transient_state() # Clear any previous chat state
                    st.session_state.loading_session_flag = True # Signal that we are loading

                    st.session_state.current_chat_session_id = session_details.id
                    st.session_state.chat_provider = session_details.llm_provider
                    st.session_state.chat_model = session_details.llm_model_name
                    st.session_state.current_messages_data = session_details.messages # Already ChatMessageData list

                    # Try to set active_prompt or active_card if available (requires fetching them)
                    # This is complex because ChatService doesn't know about PromptService/CharacterService
                    # For simplicity, we'll just use the name from the session. A more robust solution
                    # would be to store prompt/card name in ChatSession table or fetch them here.
                    if session_details.originating_prompt_id:
                        # Ideally, fetch prompt name here via prompt_service
                        # For now, derive a placeholder name.
                        st.session_state.active_prompt_name_for_chat = f"Prompt ID {session_details.originating_prompt_id}"
                        # Need to actually load the PromptData for variables etc.
                        # This would require access to PromptService here.
                        # For now, loading a session will not re-run variable substitution.
                    elif session_details.originating_card_id:
                        st.session_state.active_card_name_for_chat = f"Card ID {session_details.originating_card_id}"

                    st.session_state.chat_loaded_item_id = f"session_{session_details.id}" # Special ID for loaded sessions
                    st.session_state.chat_stage = "chatting" # Go directly to chatting
                    st.session_state.view = "chat"
                    st.rerun()

            with col2:
                if st.button("🗑️ Delete Session", type="primary", key=f"delete_session_{session_details.id}", use_container_width=True):
                    confirm_delete_key = f"confirm_delete_session_{session_details.id}"
                    if confirm_delete_key not in st.session_state:
                        st.session_state[confirm_delete_key] = False

                    if st.session_state[confirm_delete_key]:
                        if chat_service.delete_chat_session(session_details.id):
                            st.success(f"Session '{session_details.session_name}' deleted.")
                            st.session_state.selected_session_for_actions = None
                            del st.session_state[confirm_delete_key]
                            st.rerun()
                        else:
                            st.error("Failed to delete session.")
                    else:
                        st.warning(f"Are you sure you want to delete session '{session_details.session_name}'? This cannot be undone.")
                        c1,c2 = st.columns(2)
                        if c1.button("Confirm Delete", key=f"confirm_del_btn_sess_{session_details.id}", use_container_width=True):
                            st.session_state[confirm_delete_key] = True
                            st.rerun()
                        if c2.button("Cancel", key=f"cancel_del_btn_sess_{session_details.id}", use_container_width=True):
                            st.rerun()
            # col3 is empty, for spacing or future actions
        else:
            st.error(f"Could not load details for session ID {selected_session_id}.")
            st.session_state.selected_session_for_actions = None
