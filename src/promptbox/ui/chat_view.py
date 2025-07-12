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
        role = "user"
    elif isinstance(lc_message, AIMessage):
        role = "assistant"

    return ChatMessageData(
        session_id=0,
        role=role,
        content=str(lc_message.content),
        message_order=order,
        timestamp=datetime.now()
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
            content = substitute_variables(prompt_data.system_instruction, variable_context)
            messages.append(ChatMessageData(session_id=0, role="system", content=content, message_order=order, timestamp=datetime.now()))
            order += 1
        if prompt_data.user_instruction:
            content = substitute_variables(prompt_data.user_instruction, variable_context)
            messages.append(ChatMessageData(session_id=0, role="user", content=content, message_order=order, timestamp=datetime.now()))
            order += 1
        if prompt_data.assistant_instruction:
            content = substitute_variables(prompt_data.assistant_instruction, variable_context)
            messages.append(ChatMessageData(session_id=0, role="assistant", content=content, message_order=order, timestamp=datetime.now()))
            order += 1
    elif card_data:
        if card_data.system_instruction:
            content = substitute_variables(card_data.system_instruction, variable_context)
            messages.append(ChatMessageData(session_id=0, role="system", content=content, message_order=order, timestamp=datetime.now()))
            order += 1
        if card_data.user_instruction:
            content = substitute_variables(card_data.user_instruction, variable_context)
            messages.append(ChatMessageData(session_id=0, role="user", content=content, message_order=order, timestamp=datetime.now()))
            order += 1
        if card_data.assistant_instruction:
            content = substitute_variables(card_data.assistant_instruction, variable_context)
            messages.append(ChatMessageData(session_id=0, role="assistant", content=content, message_order=order, timestamp=datetime.now()))
            order += 1
    return messages

def get_active_item_info() -> Tuple[Optional[str], Optional[int], Optional[PromptData], Optional[CharacterCardData]]:
    item_name: Optional[str] = None
    item_id: Optional[int] = None
    active_prompt: Optional[PromptData] = st.session_state.get("active_prompt")
    active_card: Optional[CharacterCardData] = st.session_state.get("active_card")

    if active_prompt:
        item_name = active_prompt.name
        item_id = active_prompt.id
    elif active_card:
        item_name = active_card.name
        item_id = active_card.id
    elif st.session_state.get("loading_session_flag"):
        item_name = st.session_state.get("active_item_name_for_chat_display", "Loaded Session")


    return item_name, item_id, active_prompt, active_card


def render_chat_ui(llm_service: LLMService, chat_service: ChatService):
    """
    Manages the entire chat UI lifecycle including setup, chatting, saving, and editing.
    """
    item_name, item_db_id, active_prompt, active_card = get_active_item_info()

    if not item_name and not st.session_state.get("loading_session_flag", False):
        st.error("No active prompt or card selected. Please return to the previous page.")
        if st.button("Go Back"):
            st.session_state.view = st.session_state.get("previous_view", "home")
            st.rerun()
        return

    st.header("Chat Session")

    if "chat_stage" not in st.session_state: st.session_state.chat_stage = "setup"
    if "current_chat_session_id" not in st.session_state: st.session_state.current_chat_session_id = None
    if "current_messages_data" not in st.session_state: st.session_state.current_messages_data = []
    if "editing_message_index" not in st.session_state: st.session_state.editing_message_index = None
    if "chat_provider" not in st.session_state: st.session_state.chat_provider = None
    if "chat_model" not in st.session_state: st.session_state.chat_model = None

    if st.session_state.chat_stage == "setup":
        render_chat_setup_stage(llm_service, active_prompt, active_card, item_name)
        return

    if st.session_state.chat_stage == "chatting":
        chatting_item_name = item_name or st.session_state.get("active_item_name_for_chat_display", "Chat")
        render_chatting_stage(llm_service, chat_service, chatting_item_name, active_prompt, active_card)
        return

    if st.session_state.chat_stage == "ask_save_dialog":
        dialog_item_name = item_name or st.session_state.get("active_item_name_for_chat_display", "Current Chat")
        render_ask_save_dialog(chat_service, dialog_item_name, active_prompt, active_card)
        return


def render_chat_setup_stage(llm_service: LLMService, active_prompt: Optional[PromptData], active_card: Optional[CharacterCardData], item_name: str):
    st.subheader(f"Setup Chat: {item_name}")
    st.markdown("Confirm the model and fill in any required variables for this session.")

    available_models = llm_service.list_available_models()
    if not available_models:
        st.error("No LLM providers are configured. Please check your API key setup."); return

    prov_key = "setup_chat_provider"
    mod_key = "setup_chat_model"

    default_provider = list(available_models.keys())[0] if available_models else None
    current_provider = st.session_state.get(prov_key, default_provider)
    if current_provider not in available_models: current_provider = default_provider

    st.session_state[prov_key] = st.selectbox(
        "Provider",
        options=list(available_models.keys()),
        index=list(available_models.keys()).index(current_provider) if current_provider and current_provider in available_models else 0,
        key=f"{prov_key}_widget"
    )
    current_provider = st.session_state[prov_key]

    models_for_provider = available_models.get(current_provider, [])
    default_model = models_for_provider[0] if models_for_provider else None
    current_model = st.session_state.get(mod_key, default_model)
    if current_model not in models_for_provider: current_model = default_model

    st.session_state[mod_key] = st.selectbox(
        "Model",
        options=models_for_provider,
        index=models_for_provider.index(current_model) if current_model and current_model in models_for_provider else 0,
        key=f"{mod_key}_widget",
        disabled=not models_for_provider
    )
    current_model = st.session_state[mod_key]

    initial_text_parts = []
    item_id = "new"
    if active_prompt:
        item_id = f"prompt_{active_prompt.id}"
        if active_prompt.system_instruction: initial_text_parts.append(active_prompt.system_instruction)
        if active_prompt.user_instruction: initial_text_parts.append(active_prompt.user_instruction)
        if active_prompt.assistant_instruction: initial_text_parts.append(active_prompt.assistant_instruction)
    elif active_card:
        item_id = f"card_{active_card.id}"
        if active_card.system_instruction: initial_text_parts.append(active_card.system_instruction)
        if active_card.user_instruction: initial_text_parts.append(active_card.user_instruction)
        if active_card.assistant_instruction: initial_text_parts.append(active_card.assistant_instruction)
    initial_text_content = "\n".join(initial_text_parts)

    variables = extract_variables(initial_text_content)
    if variables:
        st.markdown("---")
        st.subheader("Fill in Variables")
        for var in variables:
            # Create a unique key for each text input to prevent state conflicts
            widget_key = f"var_input_{item_id}_{var}"
            st.text_input(f"Value for `[[{var}]]`:", key=widget_key)

    st.markdown("---")
    if st.button("🚀 Start Chat", type="primary", use_container_width=True, disabled=not current_model):
        if not st.session_state.get(prov_key) or not st.session_state.get(mod_key):
            st.error("Please select a Provider and a Model."); return
        
        # ** THE FIX IS HERE **
        # We now correctly collect the values from the widgets before proceeding.
        variable_values = {}
        all_vars_filled = True
        for var in variables:
            widget_key = f"var_input_{item_id}_{var}"
            value = st.session_state.get(widget_key, "").strip()
            if not value:
                all_vars_filled = False
            variable_values[var] = value

        if not all_vars_filled:
            st.error("Please fill in all variable values."); return

        st.session_state.chat_provider = st.session_state[prov_key]
        st.session_state.chat_model = st.session_state[mod_key]
        st.session_state.current_messages_data = initialize_chat_messages_from_item(active_prompt, active_card, variable_values)
        st.session_state.active_item_name_for_chat_display = item_name
        st.session_state.chat_stage = "chatting"
        st.rerun()

def render_chatting_stage(llm_service: LLMService, chat_service: ChatService, item_name: str, active_prompt: Optional[PromptData], active_card: Optional[CharacterCardData]):
    st.caption(f"Chatting with: **{item_name}** using **{st.session_state.chat_provider} / {st.session_state.chat_model}**")
    if st.session_state.current_chat_session_id:
        st.caption(f"Session ID: {st.session_state.current_chat_session_id}")

    btn_cols = st.columns([1.2, 1, 1, 1.3, 0.5])
    with btn_cols[0]:
        if st.button("💾 Save Session", use_container_width=True, help="Save/Update the current chat."):
            _save_current_chat_session(chat_service, item_name, active_prompt, active_card)
            st.toast("Chat session saved/updated!", icon="✅")
            st.rerun()

    with btn_cols[1]:
        if st.button("📝 Export MD", use_container_width=True, help="Export current chat to Markdown."):
            if st.session_state.current_chat_session_id:
                file_path = chat_service.export_session_to_markdown(st.session_state.current_chat_session_id)
                if file_path: st.success(f"Chat exported to: `{file_path}`")
                else: st.error("Failed to export chat session.")
            else: _export_unsaved_chat_to_markdown(item_name)

    with btn_cols[2]:
        if st.button("⚙️ Change Model", use_container_width=True, help="Change LLM for this chat."):
            st.session_state.next_chat_stage = "setup"
            st.session_state.chat_stage = "ask_save_dialog"
            st.rerun()

    with btn_cols[3]:
        if st.button("🛑 Exit Chat", type="secondary", use_container_width=True, help="Exit chat. You'll be asked to save."):
            st.session_state.next_chat_stage = st.session_state.get("previous_view", "home")
            st.session_state.chat_stage = "ask_save_dialog"
            st.rerun()

    st.markdown("---")

    for i, msg_data in enumerate(st.session_state.current_messages_data):
        role_for_display = msg_data.role.lower()
        if role_for_display == "human": role_for_display = "user"
        if role_for_display == "ai": role_for_display = "assistant"

        with st.chat_message(role_for_display):
            if st.session_state.editing_message_index == i and msg_data.role == "user":
                edited_content = st.text_area("Edit message:", value=msg_data.content, key=f"edit_msg_{i}_{msg_data.id or i}", height=100)
                col_save, col_cancel = st.columns(2)
                if col_save.button("✅ Save Edit", key=f"save_edit_{i}_{msg_data.id or i}"):
                    st.session_state.current_messages_data[i].content = edited_content
                    st.session_state.current_messages_data = st.session_state.current_messages_data[:i+1]
                    st.session_state.editing_message_index = None
                    st.rerun()
                if col_cancel.button("❌ Cancel Edit", key=f"cancel_edit_{i}_{msg_data.id or i}"):
                    st.session_state.editing_message_index = None
                    st.rerun()
            else:
                st.markdown(msg_data.content)
                if msg_data.role == "user":
                    if st.button("✏️", key=f"edit_btn_{i}_{msg_data.id or i}", help="Edit & Resend from here"):
                        st.session_state.editing_message_index = i
                        st.rerun()

    if st.session_state.editing_message_index is not None: return

    llm = llm_service.get_chat_model(st.session_state.chat_provider, st.session_state.chat_model)
    if not llm:
        st.error(f"Failed to init model '{st.session_state.chat_model}'. Try changing model or check logs."); return

    if user_input := st.chat_input("Your message..."):
        new_user_message = ChatMessageData(
            session_id=st.session_state.current_chat_session_id or 0,
            role="user", content=user_input,
            message_order=len(st.session_state.current_messages_data),
            timestamp=datetime.now()
        )
        st.session_state.current_messages_data.append(new_user_message)
        st.rerun()

    if st.session_state.current_messages_data and st.session_state.current_messages_data[-1].role == "user":
        current_lc_messages_for_llm = [convert_to_langchain_message(msg) for msg in st.session_state.current_messages_data]
        with st.chat_message("assistant"):
            with st.spinner("🧠 Thinking..."):
                try:
                    response_placeholder = st.empty()
                    full_response_content = ""
                    for chunk in llm.stream(current_lc_messages_for_llm):
                        chunk_content = cast(str, chunk.content)
                        full_response_content += chunk_content
                        response_placeholder.markdown(full_response_content + "▌")
                    response_placeholder.markdown(full_response_content)

                    ai_message_data = ChatMessageData(
                        session_id=st.session_state.current_chat_session_id or 0,
                        role="assistant", content=full_response_content,
                        message_order=len(st.session_state.current_messages_data),
                        timestamp=datetime.now()
                    )
                    st.session_state.current_messages_data.append(ai_message_data)
                except Exception as e:
                    st.error(f"LLM communication error: {e}")


def _save_current_chat_session(chat_service: ChatService, item_name: str, active_prompt: Optional[PromptData], active_card: Optional[CharacterCardData]):
    session_id = st.session_state.current_chat_session_id
    messages_to_save = st.session_state.current_messages_data

    if not messages_to_save:
        st.toast("No messages to save.", icon="🤷"); return

    default_session_name = f"{item_name} ({st.session_state.chat_model}) - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    session_name_to_save = default_session_name
    
    if session_id:
        existing_session = chat_service.get_chat_session(session_id)
        if existing_session and existing_session.session_name:
            session_name_to_save = existing_session.session_name

    if session_id:
        chat_service.update_chat_session_metadata(
            session_id, session_name=session_name_to_save,
            llm_provider=st.session_state.chat_provider,
            llm_model_name=st.session_state.chat_model
        )
        chat_service.save_chat_messages(session_id, messages_to_save)
    else:
        origin_prompt_id = active_prompt.id if active_prompt else None
        origin_card_id = active_card.id if active_card else None

        if not origin_prompt_id and not origin_card_id and st.session_state.get("chat_origin_item_id"):
            origin_id_str = st.session_state.chat_origin_item_id
            if origin_id_str.startswith("prompt_"): origin_prompt_id = int(origin_id_str.split("_")[1])
            elif origin_id_str.startswith("card_"): origin_card_id = int(origin_id_str.split("_")[1])

        session_data = ChatSessionData(
            session_name=session_name_to_save,
            llm_provider=st.session_state.chat_provider,
            llm_model_name=st.session_state.chat_model,
            originating_prompt_id=origin_prompt_id,
            originating_card_id=origin_card_id,
            messages=[]
        )
        created_session = chat_service.create_chat_session(session_data)
        st.session_state.current_chat_session_id = created_session.id
        chat_service.save_chat_messages(created_session.id, messages_to_save)

    for msg_data in st.session_state.current_messages_data:
        if msg_data.session_id == 0 and st.session_state.current_chat_session_id:
            msg_data.session_id = st.session_state.current_chat_session_id


def render_ask_save_dialog(chat_service: ChatService, item_name:str, active_prompt: Optional[PromptData], active_card: Optional[CharacterCardData]):
    st.subheader("Save Current Chat?")
    st.warning("You have unsaved changes in the current chat session.")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✅ Yes, Save", use_container_width=True, type="primary"):
            _save_current_chat_session(chat_service, item_name, active_prompt, active_card)
            st.success("Session saved!")
            next_stage_or_view = st.session_state.get("next_chat_stage", "home")

            if next_stage_or_view in ["setup", "chatting"]:
                st.session_state.chat_stage = next_stage_or_view
            else:
                st.session_state.view = next_stage_or_view
                st.session_state.chat_stage = "setup"

            _clear_chat_transient_state(keep_active_item=False)
            st.rerun()
    with col2:
        if st.button("❌ No, Discard", use_container_width=True):
            next_stage_or_view = st.session_state.get("next_chat_stage", "home")
            if next_stage_or_view in ["setup", "chatting"]:
                st.session_state.chat_stage = next_stage_or_view
            else:
                st.session_state.view = next_stage_or_view
                st.session_state.chat_stage = "setup"
            
            _clear_chat_transient_state(keep_active_item=False)
            st.rerun()
    with col3:
        if st.button("↩️ Cancel", use_container_width=True):
            st.session_state.chat_stage = "chatting"
            st.session_state.next_chat_stage = None
            st.rerun()

def _clear_chat_transient_state(keep_active_item=False):
    keys_to_clear = [
        "current_messages_data", "editing_message_index",
        "chat_provider", "chat_model", "current_chat_session_id",
        "setup_chat_provider", "setup_chat_model", "chat_loaded_item_id",
        "loading_session_flag", "next_chat_stage",
        "active_item_name_for_chat_display", "chat_origin_item_id"
    ]
    if not keep_active_item:
        keys_to_clear.extend(["active_prompt", "active_card"])

    for key in list(st.session_state.keys()):
        if key.startswith("var_input_"):
            keys_to_clear.append(key)
    for key in keys_to_clear:
        if key in st.session_state: del st.session_state[key]


def _export_unsaved_chat_to_markdown(item_name: str):
    messages_data = st.session_state.get("current_messages_data", [])
    if not messages_data:
        st.warning("Nothing to export."); return

    provider = st.session_state.get('chat_provider', 'N/A')
    model = st.session_state.get('chat_model', 'N/A')

    content = f"# Chat with: {item_name}\n"
    content += f"_Provider: {provider}, Model: {model}_\n"
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
        from promptbox.utils.file_handler import save_markdown_file
        settings.backup_dir.mkdir(parents=True, exist_ok=True)
        save_path = save_markdown_file(filename, content, directory=settings.backup_dir)
        st.success(f"Unsaved chat exported successfully to: `{save_path}`")
    except Exception as e:
        st.error(f"Failed to export unsaved chat: {e}")
