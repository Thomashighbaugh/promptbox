"""
Renders the chat interface, including variable substitution, conversation flow,
session saving, message editing, and markdown export.
"""
import streamlit as st
from datetime import datetime
from typing import List, Optional, Tuple, cast
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage

from promptbox.services.llm_service import LLMService
from promptbox.services.chat_service import ChatService
from promptbox.models.data_models import PromptData, CharacterCardData, ChatSessionData, ChatMessageData
from promptbox.utils.prompt_parser import extract_variables, substitute_variables
from promptbox.core.config import settings


def convert_to_langchain_message(msg_data: ChatMessageData) -> BaseMessage:
    """Converts ChatMessageData to a Langchain BaseMessage."""
    if msg_data.role.lower() == "system":
        return SystemMessage(content=msg_data.content)
    elif msg_data.role.lower() in ["user", "human"]:
        return HumanMessage(content=msg_data.content)
    elif msg_data.role.lower() in ["assistant", "ai"]:
        return AIMessage(content=msg_data.content)
    raise ValueError(f"Unknown message role: {msg_data.role}")

def convert_from_langchain_message(lc_message: BaseMessage, order: int) -> ChatMessageData:
    """Converts a Langchain BaseMessage to ChatMessageData."""
    role = "unknown"
    if isinstance(lc_message, SystemMessage):
        role = "system"
    elif isinstance(lc_message, HumanMessage):
        role = "user" # Use 'user' for consistency with our ChatMessageData
    elif isinstance(lc_message, AIMessage):
        role = "assistant" # Use 'assistant'

    return ChatMessageData(
        session_id=0, # Placeholder, will be set when saving to a real session
        role=role,
        content=str(lc_message.content),
        message_order=order,
        timestamp=datetime.now() # Approximate timestamp
    )

def initialize_chat_messages_from_item(
    prompt_data: Optional[PromptData] = None,
    card_data: Optional[CharacterCardData] = None,
    variable_context: Optional[dict[str, str]] = None
) -> List[ChatMessageData]:
    """
    Creates the initial list of ChatMessageData objects for the chat,
    substituting variables as needed.
    """
    messages: List[ChatMessageData] = []
    variable_context = variable_context or {}
    order = 0

    if prompt_data:
        if prompt_data.system_instruction:
            messages.append(ChatMessageData(session_id=0, role="system", content=substitute_variables(prompt_data.system_instruction, variable_context), message_order=order, timestamp=datetime.now()))
            order += 1
        if prompt_data.user_instruction: # This becomes the first "user" message if present
            messages.append(ChatMessageData(session_id=0, role="user", content=substitute_variables(prompt_data.user_instruction, variable_context), message_order=order, timestamp=datetime.now()))
            order += 1
        if prompt_data.assistant_instruction: # This becomes the first "assistant" reply if present
             messages.append(ChatMessageData(session_id=0, role="assistant", content=substitute_variables(prompt_data.assistant_instruction, variable_context), message_order=order, timestamp=datetime.now()))
             order += 1
    elif card_data:
        messages.append(ChatMessageData(session_id=0, role="system", content=substitute_variables(card_data.instructions, variable_context), message_order=order, timestamp=datetime.now()))
        # order +=1 # No increment here as system message from card doesn't typically start a turn

    return messages

def get_active_item_info() -> Tuple[Optional[str], Optional[int], Optional[PromptData], Optional[CharacterCardData]]:
    """Determines the name and ID of the active prompt or card."""
    item_name: Optional[str] = None
    item_id: Optional[int] = None # DB ID of prompt/card
    active_prompt: Optional[PromptData] = st.session_state.get("active_prompt")
    active_card: Optional[CharacterCardData] = st.session_state.get("active_card")

    if active_prompt:
        item_name = active_prompt.name
        item_id = active_prompt.id
    elif active_card:
        item_name = active_card.name
        item_id = active_card.id
    return item_name, item_id, active_prompt, active_card


def render_chat_ui(llm_service: LLMService, chat_service: ChatService):
    """
    Manages the entire chat UI lifecycle including setup, chatting, saving, and editing.
    """
    item_name, item_db_id, active_prompt, active_card = get_active_item_info()

    if not item_name:
        st.error("No active prompt or card selected. Please return to the previous page.")
        if st.button("Go Back"):
            st.session_state.view = "prompts" # Or home, or intelligently pick
            st.rerun()
        return

    st.header(f"Chat Session") # General header, details below
    
    # --- Initialize session state variables ---
    if "chat_stage" not in st.session_state: st.session_state.chat_stage = "setup" # setup, chatting
    if "current_chat_session_id" not in st.session_state: st.session_state.current_chat_session_id = None # DB ID of ChatSession
    if "current_messages_data" not in st.session_state: st.session_state.current_messages_data = [] # List[ChatMessageData]
    if "editing_message_index" not in st.session_state: st.session_state.editing_message_index = None # Index of message being edited
    if "chat_provider" not in st.session_state: st.session_state.chat_provider = None
    if "chat_model" not in st.session_state: st.session_state.chat_model = None
    
    # Check if navigating away (this is a simplified check, Streamlit doesn't have a robust on_leave event)
    # This check happens *before* the main chat logic.
    # A more robust solution might involve a modal triggered by sidebar clicks.
    # For now, we rely on user explicitly saving or the "Save Session?" dialog if they try to change view.
    # This logic is complex to get right in Streamlit's execution model.
    # We will trigger the save dialog primarily through explicit "Exit" or "Change Model" buttons,
    # or if the view changes.

    # If the active item (prompt/card) changes, or if loading a new session, reset chat.
    # This is a key part of managing state when user selects a NEW prompt/card for chat.
    # Or when a session is loaded.
    unique_item_identifier = f"{'prompt' if active_prompt else 'card'}_{item_db_id}"
    if st.session_state.get("chat_loaded_item_id") != unique_item_identifier and not st.session_state.get("loading_session_flag", False):
        # This means user selected a new prompt/card for chat, not loading an old session.
        # So, if there's an ongoing chat, ask to save.
        if st.session_state.current_messages_data and st.session_state.chat_stage == "chatting":
             # This scenario is tricky. Usually handled by "Start Chat" from prompt/card view.
             # For simplicity, we'll assume if they reach here and item changed, it's a "new" chat setup.
             pass # Will be handled by stage logic below.

    # --- CHAT STAGES ---
    if st.session_state.chat_stage == "setup":
        render_chat_setup_stage(llm_service, active_prompt, active_card, item_name)
        return

    if st.session_state.chat_stage == "chatting":
        render_chatting_stage(llm_service, chat_service, item_name, active_prompt, active_card)
        return
        
    if st.session_state.chat_stage == "ask_save_dialog":
        render_ask_save_dialog(chat_service, item_name, active_prompt, active_card)
        return


def render_chat_setup_stage(llm_service: LLMService, active_prompt: Optional[PromptData], active_card: Optional[CharacterCardData], item_name: str):
    st.subheader(f"Setup Chat: {item_name}")
    st.markdown("Confirm the model and fill in any required variables for this session.")
    
    available_models = llm_service.list_available_models()
    if not available_models:
        st.error("No LLM providers are configured. Please check your API key setup."); return

    # Persist provider/model selection in session_state immediately for responsiveness
    # Default to previously selected if available and valid
    prov_key = "setup_chat_provider"
    mod_key = "setup_chat_model"

    current_provider = st.session_state.get(prov_key, list(available_models.keys())[0] if available_models else None)
    if current_provider not in available_models: # Handle case where provider list changed
        current_provider = list(available_models.keys())[0] if available_models else None
    
    st.session_state[prov_key] = st.selectbox(
        "Provider", 
        options=list(available_models.keys()), 
        index=list(available_models.keys()).index(current_provider) if current_provider else 0,
        key=f"{prov_key}_widget" # Unique key for the widget
    )
    current_provider = st.session_state[prov_key] # Update with widget's current value

    models_for_provider = available_models.get(current_provider, [])
    current_model = st.session_state.get(mod_key, models_for_provider[0] if models_for_provider else None)
    if current_model not in models_for_provider: # Handle case where model list changed
         current_model = models_for_provider[0] if models_for_provider else None

    st.session_state[mod_key] = st.selectbox(
        "Model", 
        options=models_for_provider, 
        index=models_for_provider.index(current_model) if current_model and models_for_provider else 0,
        key=f"{mod_key}_widget" # Unique key for the widget
    )
    current_model = st.session_state[mod_key] # Update


    initial_text_content = ""
    if active_prompt:
        initial_text_content = (active_prompt.system_instruction or "") + (active_prompt.user_instruction or "") + (active_prompt.assistant_instruction or "")
    elif active_card:
        initial_text_content = active_card.instructions or ""
    
    variables = extract_variables(initial_text_content)
    variable_values = {}
    if variables:
        st.markdown("---")
        st.subheader("Fill in Variables")
        for var in variables:
            variable_values[var] = st.text_input(f"Value for `[[{var}]]`:", key=f"var_{var}_setup")

    st.markdown("---")
    if st.button("🚀 Start Chat", type="primary", use_container_width=True):
        if not st.session_state[prov_key] or not st.session_state[mod_key]:
            st.error("Please select a Provider and a Model."); return
        if variables and not all(variable_values.get(v,"").strip() for v in variables):
            st.error("Please fill in all variable values."); return
        
        st.session_state.chat_provider = st.session_state[prov_key]
        st.session_state.chat_model = st.session_state[mod_key]
        
        # Initialize messages
        st.session_state.current_messages_data = initialize_chat_messages_from_item(active_prompt, active_card, variable_values)
        
        # Determine unique ID for the item being chatted with (prompt or card)
        item_db_id = active_prompt.id if active_prompt else active_card.id
        st.session_state.chat_loaded_item_id = f"{'prompt' if active_prompt else 'card'}_{item_db_id}"

        st.session_state.current_chat_session_id = None # New chat, no DB session ID yet
        st.session_state.editing_message_index = None
        st.session_state.chat_stage = "chatting"
        st.rerun()

def render_chatting_stage(llm_service: LLMService, chat_service: ChatService, item_name: str, active_prompt: Optional[PromptData], active_card: Optional[CharacterCardData]):
    st.caption(f"Chatting with: **{item_name}** using **{st.session_state.chat_provider} / {st.session_state.chat_model}**")
    
    # --- Action Buttons ---
    btn_cols = st.columns([1.2, 1, 1, 1.3, 0.5]) # Adjusted for new buttons
    with btn_cols[0]:
        if st.button("💾 Save Session", use_container_width=True, help="Save the current chat to your sessions history."):
            _save_current_chat_session(chat_service, item_name, active_prompt, active_card)
            # Stay in chat view after saving
            st.success("Chat session saved!") 
            st.rerun() # Rerun to reflect saved state, e.g. update session ID display

    with btn_cols[1]:
        if st.button("📝 Export MD", use_container_width=True, help="Export current chat to a Markdown file."):
            if st.session_state.current_chat_session_id:
                file_path = chat_service.export_session_to_markdown(st.session_state.current_chat_session_id)
                if file_path:
                    st.success(f"Chat exported to: `{file_path}`")
                else:
                    st.error("Failed to export chat session.")
            else: # unsaved chat
                _export_unsaved_chat_to_markdown(item_name)


    with btn_cols[2]:
        if st.button("⚙️ Change Model", use_container_width=True, help="Change LLM provider/model for this chat (may require saving first)."):
            st.session_state.next_chat_stage = "setup" # What to do after save dialog
            st.session_state.chat_stage = "ask_save_dialog"
            st.rerun()
            
    with btn_cols[3]:
        if st.button("🛑 Exit Chat", type="secondary", use_container_width=True, help="Exit the chat. You'll be asked to save if there are changes."):
            st.session_state.next_chat_stage = "prompts" # Or home, or previous view
            st.session_state.chat_stage = "ask_save_dialog"
            st.rerun()
    
    st.markdown("---")

    # --- Display Messages ---
    # Convert ChatMessageData to Langchain messages for display and LLM interaction
    langchain_messages: List[BaseMessage] = [convert_to_langchain_message(msg) for msg in st.session_state.current_messages_data]
    
    for i, msg_data in enumerate(st.session_state.current_messages_data):
        role_for_display = "user" if msg_data.role == "user" else ("assistant" if msg_data.role == "assistant" else "system")
        
        with st.chat_message(role_for_display):
            if st.session_state.editing_message_index == i and msg_data.role == "user":
                edited_content = st.text_area("Edit your message:", value=msg_data.content, key=f"edit_msg_{i}", height=100)
                if st.button("✅ Save Edit", key=f"save_edit_{i}"):
                    # Update message and truncate history
                    st.session_state.current_messages_data[i].content = edited_content
                    st.session_state.current_messages_data = st.session_state.current_messages_data[:i+1] # Truncate
                    st.session_state.editing_message_index = None
                    st.rerun() # Rerun to process the edited message as new input
                if st.button("❌ Cancel Edit", key=f"cancel_edit_{i}"):
                    st.session_state.editing_message_index = None
                    st.rerun()
            else:
                st.markdown(msg_data.content)
                if msg_data.role == "user": # Only allow editing user messages
                    if st.button("✏️", key=f"edit_btn_{i}", help="Edit this message (will regenerate response from here)"):
                        st.session_state.editing_message_index = i
                        st.rerun()
    
    if st.session_state.editing_message_index is not None: # If editing, don't show chat input or process new messages
        return

    # --- Chat Input & LLM Response ---
    llm = llm_service.get_chat_model(st.session_state.chat_provider, st.session_state.chat_model)
    if not llm:
        st.error(f"Failed to initialize model '{st.session_state.chat_model}'. Please try changing the model or check logs."); return

    if user_input := st.chat_input("Your message..."):
        new_user_message = ChatMessageData(
            session_id=st.session_state.current_chat_session_id or 0, 
            role="user", 
            content=user_input, 
            message_order=len(st.session_state.current_messages_data),
            timestamp=datetime.now()
        )
        st.session_state.current_messages_data.append(new_user_message)
        st.rerun() # Show user message immediately

    # Check if the last message is from the user (and not currently editing)
    if st.session_state.current_messages_data and st.session_state.current_messages_data[-1].role == "user":
        # Ensure we use up-to-date langchain_messages for the LLM call
        current_lc_messages_for_llm = [convert_to_langchain_message(msg) for msg in st.session_state.current_messages_data]

        with st.chat_message("assistant"):
            with st.spinner("🧠 Thinking..."):
                try:
                    response_placeholder = st.empty()
                    full_response_content = ""
                    # Stream response from LLM
                    for chunk in llm.stream(current_lc_messages_for_llm): # Pass the current set of messages
                        chunk_content = cast(str, chunk.content) # Ensure content is string
                        full_response_content += chunk_content
                        response_placeholder.markdown(full_response_content + "▌")
                    response_placeholder.markdown(full_response_content) # Final response

                    # Add AI response to message history
                    ai_message_data = ChatMessageData(
                        session_id=st.session_state.current_chat_session_id or 0,
                        role="assistant",
                        content=full_response_content,
                        message_order=len(st.session_state.current_messages_data),
                        timestamp=datetime.now()
                    )
                    st.session_state.current_messages_data.append(ai_message_data)
                    # Don't rerun here, let the natural Streamlit flow complete the turn
                    # This rerun was causing issues by interrupting the stream completion.
                    # We only need to rerun if we are *not* the last operation in the script.
                    # Since adding the message to state IS the last step before input or next action,
                    # Streamlit will naturally update the display.
                except Exception as e:
                    st.error(f"An error occurred while communicating with the LLM: {e}")
                    # Optionally, remove the last user message if the AI call failed catastrophically
                    # if st.session_state.current_messages_data and st.session_state.current_messages_data[-1].role == "user":
                    # st.session_state.current_messages_data.pop()


def _save_current_chat_session(chat_service: ChatService, item_name: str, active_prompt: Optional[PromptData], active_card: Optional[CharacterCardData]):
    """Saves the current chat state to the database."""
    session_id = st.session_state.current_chat_session_id
    messages_to_save = st.session_state.current_messages_data

    if not messages_to_save:
        st.toast("No messages to save.", icon="🤷")
        return

    session_name = f"{item_name} ({st.session_state.chat_model}) - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    if session_id: # Existing session, update it
        chat_service.update_chat_session_metadata(
            session_id, 
            session_name=session_name, # Potentially update name if model/item changed
            llm_provider=st.session_state.chat_provider,
            llm_model_name=st.session_state.chat_model
        )
        # Then save messages (this will replace existing messages for the session)
        chat_service.save_chat_messages(session_id, messages_to_save)
    else: # New session, create it
        session_data = ChatSessionData(
            session_name=session_name,
            llm_provider=st.session_state.chat_provider,
            llm_model_name=st.session_state.chat_model,
            originating_prompt_id=active_prompt.id if active_prompt else None,
            originating_card_id=active_card.id if active_card else None,
            messages=[] # Messages will be saved separately by save_chat_messages
        )
        created_session = chat_service.create_chat_session(session_data)
        st.session_state.current_chat_session_id = created_session.id
        # Now save messages to this new session
        chat_service.save_chat_messages(created_session.id, messages_to_save)
    
    # Update message session_ids if they were 0 (for new messages in an unsaved session)
    for msg_data in st.session_state.current_messages_data:
        if msg_data.session_id == 0 and st.session_state.current_chat_session_id:
            msg_data.session_id = st.session_state.current_chat_session_id


def render_ask_save_dialog(chat_service: ChatService, item_name:str, active_prompt: Optional[PromptData], active_card: Optional[CharacterCardData]):
    st.subheader("Save Current Chat?")
    st.warning("You have unsaved changes in the current chat session.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✅ Yes, Save Session", use_container_width=True, type="primary"):
            _save_current_chat_session(chat_service, item_name, active_prompt, active_card)
            st.success("Session saved!")
            # Proceed to the originally intended next stage
            next_stage = st.session_state.get("next_chat_stage", "prompts") 
            st.session_state.view = next_stage # if next stage is a view
            st.session_state.chat_stage = next_stage # if next stage is another chat stage (e.g. "setup")
            # Clear chat specific states for a clean transition
            _clear_chat_transient_state()
            st.rerun()
    with col2:
        if st.button("❌ No, Discard Changes", use_container_width=True):
            next_stage = st.session_state.get("next_chat_stage", "prompts")
            st.session_state.view = next_stage
            st.session_state.chat_stage = next_stage
            _clear_chat_transient_state()
            st.rerun()
    with col3:
        if st.button("↩️ Cancel (Stay in Chat)", use_container_width=True):
            st.session_state.chat_stage = "chatting" # Go back to chatting
            st.session_state.next_chat_stage = None
            st.rerun()

def _clear_chat_transient_state():
    """Clears session state variables specific to an active chat flow."""
    keys_to_clear = [
        "current_messages_data", "editing_message_index", 
        "chat_provider", "chat_model", "current_chat_session_id",
        "setup_chat_provider", "setup_chat_model", "chat_loaded_item_id",
        "active_prompt", "active_card", "loading_session_flag"
    ]
    # Also clear any variable inputs like "var_X_setup"
    for key in list(st.session_state.keys()):
        if key.startswith("var_") and key.endswith("_setup"):
            keys_to_clear.append(key)
            
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    # Keep 'chat_stage' and 'view' as they are set by the calling function for navigation


def _export_unsaved_chat_to_markdown(item_name: str):
    """Formats and saves an unsaved chat to a markdown file."""
    messages_data = st.session_state.get("current_messages_data", [])
    if not messages_data:
        st.warning("There is nothing to save/export."); return

    content = f"# Chat with: {item_name}\n"
    content += f"_Provider: {st.session_state.chat_provider}, Model: {st.session_state.chat_model}_\n"
    content += f"_Status: Unsaved Session, Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n\n"
    content += "---\n\n"

    for msg_data in messages_data:
        role_display = msg_data.role.capitalize()
        if msg_data.role.lower() == "system":
            content += f"## System Instruction\n\n> {msg_data.content}\n\n"
        elif msg_data.role.lower() in ["human", "user"]:
            content += f"### User\n\n{msg_data.content}\n\n"
        elif msg_data.role.lower() in ["ai", "assistant"]:
            content += f"### Assistant\n\n{msg_data.content}\n\n"
        else:
             content += f"### {role_display}\n\n{msg_data.content}\n\n"
        content += "---\n\n"
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_item_name = "".join(c for c in item_name if c.isalnum() or c in (' ', '_', '-')).rstrip()
    filename = f"Unsaved Chat - {safe_item_name} - {timestamp}.md"
    
    try:
        from promptbox.utils.file_handler import save_markdown_file # Local import
        settings.backup_dir.mkdir(parents=True, exist_ok=True)
        save_path = save_markdown_file(filename, content, directory=settings.backup_dir)
        st.success(f"Unsaved chat exported successfully to: `{save_path}`")
    except Exception as e:
        st.error(f"Failed to export unsaved chat: {e}")
