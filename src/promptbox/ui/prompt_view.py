"""
Renders the Streamlit UI for managing prompts using a drill-down navigation for folders.
"""
import streamlit as st
import pandas as pd
from typing import List, Dict, Optional
from collections import defaultdict

# Ensure these imports are correct and the modules exist and are error-free
from promptbox.services.prompt_service import PromptService
from promptbox.models.data_models import PromptData
from promptbox.services.llm_service import LLMService

# get_folder_structure can remain largely the same, as it builds the data structure.
def get_folder_structure(prompts: List[PromptData]) -> Dict:
    def create_node():
        return {"_prompts_": [], "children": defaultdict(create_node)}
    root_node = create_node()
    for prompt in prompts:
        folder_path = prompt.folder
        parts = [part for part in folder_path.strip("/").split("/") if part]
        if not parts:
            root_node["_prompts_"].append(prompt)
            continue
        current_children_map = root_node["children"]
        for i, part in enumerate(parts):
            node_for_this_part = current_children_map[part]
            if i == len(parts) - 1:
                node_for_this_part["_prompts_"].append(prompt)
            else:
                current_children_map = node_for_this_part["children"]
    return root_node

def render_prompt_view(prompt_service: PromptService, llm_service: LLMService):
    st.header("Manage Prompts")

    # Initialize session state variables
    if "prompt_search_query" not in st.session_state: st.session_state.prompt_search_query = ""
    # prompt_selected_folder: "" means root, "All" means show all (for selectbox)
    if "prompt_selected_folder_path" not in st.session_state: st.session_state.prompt_selected_folder_path = "" 
    if "selected_prompt_id" not in st.session_state: st.session_state.selected_prompt_id = None
    if "editing_prompt_data" not in st.session_state: st.session_state.editing_prompt_data = None

    # --- Sidebar for actions and filters ---
    col_create, col_search, col_filter_jump = st.columns([1,2,1])
    with col_create:
        if st.button("➕ Create New Prompt", use_container_width=True):
            st.session_state.selected_prompt_id = None
            st.session_state.editing_prompt_data = None
            # Optionally, set current folder for new prompt based on view, or default
            st.rerun()
    
    with col_search:
        st.session_state.prompt_search_query = st.text_input(
            "Search All Prompts",
            value=st.session_state.prompt_search_query,
            placeholder="Name, Description, Content, Folder...",
            label_visibility="collapsed"
        )

    # --- Data fetching and structuring ---
    all_prompts = prompt_service.get_all_prompts()
    full_folder_tree = get_folder_structure(all_prompts)

    # Folder selectbox for quick jumping
    all_folder_paths = [""] # Root path
    def get_all_paths(node, current_p, paths_list):
        for name, child_node in node["children"].items():
            new_p = f"{current_p}/{name}" if current_p else name
            paths_list.append(new_p)
            get_all_paths(child_node, new_p, paths_list)
    get_all_paths(full_folder_tree, "", all_folder_paths)
    all_folder_paths = sorted(list(set(all_folder_paths))) # Unique sorted paths

    with col_filter_jump:
        # Ensure current path is in options, default to "" (root) if not
        try:
            current_path_index = all_folder_paths.index(st.session_state.prompt_selected_folder_path)
        except ValueError:
            current_path_index = 0 # Default to root ("") if current path not found
            st.session_state.prompt_selected_folder_path = ""

        selected_jump_path = st.selectbox(
            "Quick Jump to Folder",
            options=all_folder_paths,
            index=current_path_index,
            format_func=lambda x: "All Prompts (Root)" if x == "" else x,
            label_visibility="collapsed"
        )
        if selected_jump_path != st.session_state.prompt_selected_folder_path:
            st.session_state.prompt_selected_folder_path = selected_jump_path
            st.session_state.prompt_search_query = "" # Clear search when jumping
            st.rerun()

    # --- Main display area ---
    col_display, col_form = st.columns([0.55, 0.45], gap="large")

    with col_display:
        if st.session_state.prompt_search_query:
            st.subheader(f"Search Results for: \"{st.session_state.prompt_search_query}\"")
            searched_prompts = prompt_service.search_prompts_full_text(st.session_state.prompt_search_query)
            if not searched_prompts:
                st.info("No prompts found matching your search query.")
            for prompt in searched_prompts:
                if st.button(f"📄 {prompt.name} ({prompt.folder})", key=f"select_search_prompt_{prompt.id}", use_container_width=True):
                    st.session_state.selected_prompt_id = prompt.id
                    st.session_state.editing_prompt_data = None
                    st.session_state.prompt_selected_folder_path = prompt.folder # Navigate to prompt's folder
                    st.session_state.prompt_search_query = "" # Clear search
                    st.rerun()
        else:
            # --- Breadcrumb Navigation ---
            current_folder_display_path = st.session_state.prompt_selected_folder_path
            path_parts = [part for part in current_folder_display_path.split("/") if part]
            
            bc_cols = st.columns(len(path_parts) + 1)
            if bc_cols[0].button("All Prompts (Root)", key="bc_root"):
                st.session_state.prompt_selected_folder_path = ""
                st.rerun()
            
            temp_p = []
            for i, part in enumerate(path_parts):
                temp_p.append(part)
                if bc_cols[i+1].button(part, key=f"bc_{'_'.join(temp_p)}"):
                    st.session_state.prompt_selected_folder_path = "/".join(temp_p)
                    st.rerun()

            # --- Navigate tree to current folder node ---
            current_node = full_folder_tree
            for part in path_parts:
                if part in current_node["children"]:
                    current_node = current_node["children"][part]
                else: # Should not happen if selectbox/buttons are main navigation
                    st.error("Invalid folder path selected.") 
                    current_node = full_folder_tree 
                    st.session_state.prompt_selected_folder_path = ""
                    break 
            
            st.subheader(f"Contents of: {'Root' if not current_folder_display_path else current_folder_display_path}")

            # Display Subfolders
            if current_node["children"]:
                st.markdown("**Subfolders:**")
                for folder_name, _ in sorted(current_node["children"].items()):
                    subfolder_nav_path = f"{current_folder_display_path}/{folder_name}" if current_folder_display_path else folder_name
                    if st.button(f"📁 {folder_name}", key=f"nav_to_folder_{subfolder_nav_path.replace('/','_')}", use_container_width=True):
                        st.session_state.prompt_selected_folder_path = subfolder_nav_path
                        st.rerun()
            
            # Display Prompts in current folder
            if current_node["_prompts_"]:
                st.markdown("**Prompts in this folder:**")
                for prompt in sorted(current_node["_prompts_"], key=lambda p: p.name):
                    if st.button(f"📄 {prompt.name}", key=f"select_item_prompt_{prompt.id}", use_container_width=True):
                        st.session_state.selected_prompt_id = prompt.id
                        st.session_state.editing_prompt_data = None
                        st.rerun()
            
            if not current_node["children"] and not current_node["_prompts_"]:
                st.info("This folder is empty.")

    # --- Form Area (Create/Edit) ---
    with col_form:
        active_prompt_data: Optional[PromptData] = None
        if st.session_state.editing_prompt_data: 
            active_prompt_data = st.session_state.editing_prompt_data
            st.subheader(f"Edit: {active_prompt_data.name}")
        elif st.session_state.selected_prompt_id:
            prompt_db = prompt_service.get_prompt_by_id(st.session_state.selected_prompt_id)
            if prompt_db:
                active_prompt_data = prompt_db
                st.subheader(f"Edit: {active_prompt_data.name}")
            else:
                st.warning("The previously selected prompt is no longer available.")
                st.session_state.selected_prompt_id = None 
                st.session_state.editing_prompt_data = None
        else:
            st.subheader("Create New Prompt")
            st.markdown(f"New prompt will be created in: `{st.session_state.prompt_selected_folder_path if st.session_state.prompt_selected_folder_path else '(Root Level)'}`")


        if active_prompt_data: 
            render_edit_form(prompt_service, llm_service, active_prompt_data, key_suffix=f"_edit_{active_prompt_data.id}")
        else: 
            # Pass current folder path to create form
            render_create_form(prompt_service, key_suffix="_create", default_folder=st.session_state.prompt_selected_folder_path)


def render_create_form(prompt_service: PromptService, key_suffix: str, default_folder: str):
    # If default_folder is empty string (root), form should show "general" or similar, or let user type.
    # For now, let's make it so if default_folder is "", the input is empty or "general".
    form_default_folder = default_folder if default_folder else "general"

    with st.form(key=f"prompt_form{key_suffix}"):
        name = st.text_input("Name*", key=f"prompt_name{key_suffix}")
        # Folder input defaults to current view or "general"
        folder = st.text_input("Folder Path (e.g., general/utility)", value=form_default_folder, key=f"prompt_folder{key_suffix}")
        description = st.text_area("Description", height=100, key=f"prompt_description{key_suffix}")
        
        st.info("Use `[[variable_name]]` for template variables in instructions.", icon="💡")
        system_instruction = st.text_area("System Instruction", height=150, key=f"prompt_system{key_suffix}")
        user_instruction = st.text_area("User Instruction", height=150, key=f"prompt_user{key_suffix}")
        assistant_instruction = st.text_area("Assistant Instruction", height=150, key=f"prompt_assistant{key_suffix}")
        
        if st.form_submit_button("Create Prompt"):
            if not name.strip():
                st.error("The 'Name' field is required."); return
            
            folder_val = folder.strip("/").strip()
            # If user empties the folder field, treat it as root ""
            # Or enforce a default like "general" if empty. Let's make it "" for root.
            if not folder_val: folder_val = "" # Explicitly root if cleared

            try:
                prompt_data = PromptData(
                    name=name, folder=folder_val, 
                    description=description or None,
                    system_instruction=system_instruction or None,
                    user_instruction=user_instruction or None,
                    assistant_instruction=assistant_instruction or None,
                )
                new_prompt = prompt_service.create_prompt(prompt_data)
                st.success(f"Prompt '{new_prompt.name}' created in folder '{new_prompt.folder if new_prompt.folder else '(Root Level)'}'!")
                st.session_state.selected_prompt_id = new_prompt.id 
                st.session_state.editing_prompt_data = None
                st.session_state.prompt_search_query = "" 
                st.session_state.prompt_selected_folder_path = new_prompt.folder # Navigate to new prompt's folder
                st.rerun()
            except ValueError as ve: 
                 st.error(f"Validation Error: {ve}")
            except Exception as e:
                st.error(f"Failed to create prompt: {e}")

def render_edit_form(prompt_service: PromptService, llm_service: LLMService, prompt: PromptData, key_suffix: str):
    with st.form(key=f"prompt_form{key_suffix}"):
        name = st.text_input("Name*", value=prompt.name, key=f"name{key_suffix}")
        folder = st.text_input("Folder Path", value=prompt.folder, key=f"folder{key_suffix}")
        description = st.text_area("Description", value=prompt.description or "", height=100, key=f"description{key_suffix}")
        
        st.info("Use `[[variable_name]]` for template variables.", icon="💡")
        system_instruction = st.text_area("System Instruction", value=prompt.system_instruction or "", height=150, key=f"system{key_suffix}")
        user_instruction = st.text_area("User Instruction", value=prompt.user_instruction or "", height=150, key=f"user{key_suffix}")
        assistant_instruction = st.text_area("Assistant Instruction", value=prompt.assistant_instruction or "", height=150, key=f"assistant{key_suffix}")
        
        if st.form_submit_button("Save Changes"):
            if not name.strip():
                st.error("The 'Name' field is required."); return
            
            folder_val = folder.strip("/").strip()
            if not folder_val: folder_val = "" # Explicitly root if cleared


            try:
                updated_prompt_data = PromptData(
                    id=prompt.id, 
                    created_at=prompt.created_at, 
                    name=name, folder=folder_val,
                    description=description or None,
                    system_instruction=system_instruction or None,
                    user_instruction=user_instruction or None,
                    assistant_instruction=assistant_instruction or None,
                )
                updated_prompt = prompt_service.update_prompt(prompt.id, updated_prompt_data) 
                st.success(f"Prompt '{updated_prompt.name}' updated successfully!")
                st.session_state.editing_prompt_data = None 
                st.session_state.prompt_search_query = "" 
                st.session_state.prompt_selected_folder_path = updated_prompt.folder # Ensure view updates to new folder if changed
                st.rerun()
            except ValueError as ve: 
                 st.error(f"Validation Error: {ve}")
            except Exception as e:
                st.error(f"Failed to save prompt: {e}")

    st.markdown("---")
    
    with st.expander("✨ Improve with AI"):
        available_models = llm_service.list_available_models()
        if not available_models:
            st.warning("No LLM providers configured to offer improvement suggestions.")
        else:
            c1, c2 = st.columns(2)
            provider_key = f"improve_provider{key_suffix}"
            model_key = f"improve_model{key_suffix}"
            
            selected_provider = c1.selectbox("Select Provider", options=list(available_models.keys()), key=provider_key)
            selected_model = c2.selectbox("Select Model", options=available_models.get(selected_provider, []), key=model_key)
            
            if st.button("Analyze and Suggest Improvements", key=f"improve_btn{key_suffix}"):
                if selected_provider and selected_model:
                    llm = llm_service.get_chat_model(selected_provider, selected_model)
                    if llm:
                        with st.spinner("AI is analyzing your prompt..."):
                            suggestion = prompt_service.improve_prompt(prompt.id, llm)
                            st.session_state[f"suggestion_data{key_suffix}"] = suggestion 
                            if suggestion is None:
                                st.error("AI could not generate a suggestion or an error occurred.")
                            st.rerun() 
                    else: 
                        st.error(f"Could not initialize the selected LLM: {selected_provider}/{selected_model}.")
                else:
                    st.warning("Please select a provider and model for improvement.")

    suggestion_key = f"suggestion_data{key_suffix}"
    if suggestion_key in st.session_state and st.session_state[suggestion_key]:
        suggestion = st.session_state[suggestion_key]
        st.subheader("🤖 AI Suggestion")
        st.info("Review the suggestion below. Click 'Apply Suggestion' to load it into the form above, then 'Save Changes'.")
        
        st.text_area("Suggested System Instruction", value=suggestion.get("system_instruction", ""), height=100, disabled=True, key=f"sugg_sys{key_suffix}")
        st.text_area("Suggested User Instruction", value=suggestion.get("user_instruction", ""), height=100, disabled=True, key=f"sugg_user{key_suffix}")
        st.text_area("Suggested Assistant Instruction", value=suggestion.get("assistant_instruction", ""), height=100, disabled=True, key=f"sugg_asst{key_suffix}")
        
        if st.button("Apply Suggestion", key=f"apply_suggestion{key_suffix}"):
            st.session_state.editing_prompt_data = PromptData(
                id=prompt.id,
                name=prompt.name, 
                folder=prompt.folder, 
                description=prompt.description, 
                system_instruction=suggestion.get("system_instruction", prompt.system_instruction),
                user_instruction=suggestion.get("user_instruction", prompt.user_instruction),
                assistant_instruction=suggestion.get("assistant_instruction", prompt.assistant_instruction),
                created_at=prompt.created_at,
                updated_at=prompt.updated_at 
            )
            del st.session_state[suggestion_key] 
            st.rerun()

    st.markdown("---")
    col_actions1, col_actions2 = st.columns(2)
    with col_actions1:
        if st.button("💬 Chat with this Prompt", use_container_width=True, key=f"chat_prompt{key_suffix}"):
            st.session_state.active_prompt = prompt 
            st.session_state.active_card = None
            st.session_state.view = "chat"
            st.session_state.chat_stage = "setup" 
            st.session_state.current_messages_data = [] 
            st.session_state.current_chat_session_id = None 
            st.session_state.chat_loaded_item_id = None 
            st.rerun()
    with col_actions2:
        if st.button("🗑️ Delete Prompt", type="primary", use_container_width=True, key=f"delete_prompt{key_suffix}"):
            confirm_delete_key = f"confirm_delete_prompt_{prompt.id}"
            st.session_state[confirm_delete_key] = st.session_state.get(confirm_delete_key, False)

            if st.session_state[confirm_delete_key]: 
                if prompt_service.delete_prompt(prompt.id):
                    st.success(f"Prompt '{prompt.name}' deleted.")
                    st.session_state.selected_prompt_id = None
                    st.session_state.editing_prompt_data = None
                    del st.session_state[confirm_delete_key] 
                    # Consider where to navigate after delete, e.g., to parent folder or root
                    # st.session_state.prompt_selected_folder_path = "" # Go to root
                    st.rerun()
                else:
                    st.error("Failed to delete prompt.")
            else: 
                st.warning(f"Are you sure you want to delete '{prompt.name}'? This cannot be undone.")
                c1,c2 = st.columns(2)
                if c1.button("Confirm Delete", key=f"confirm_del_btn_{prompt.id}", use_container_width=True):
                    st.session_state[confirm_delete_key] = True
                    st.rerun()
                if c2.button("Cancel", key=f"cancel_del_btn_{prompt.id}", use_container_width=True):
                    st.rerun()
