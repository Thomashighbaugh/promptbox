"""
Renders the Streamlit UI for managing character and scenario cards using a drill-down navigation.
Now includes search functionality and structured instruction fields.
"""
import streamlit as st
import pandas as pd
from typing import List, Dict, Optional
from collections import defaultdict

from promptbox.services.character_service import CharacterService
from promptbox.models.data_models import CharacterCardData

# get_card_folder_structure remains the same
def get_card_folder_structure(cards: List[CharacterCardData]) -> Dict:
    def create_node():
        return {"_cards_": [], "children": defaultdict(create_node)}
    root_node = create_node()
    for card in cards:
        folder_path = card.folder
        parts = [part for part in folder_path.strip("/").split("/") if part]
        if not parts:
            root_node["_cards_"].append(card)
            continue
        current_children_map = root_node["children"]
        for i, part in enumerate(parts):
            node_for_this_part = current_children_map[part]
            if i == len(parts) - 1:
                node_for_this_part["_cards_"].append(card)
            else:
                current_children_map = node_for_this_part["children"]
    return root_node

def render_character_view(character_service: CharacterService):
    st.header("Manage Characters & Scenarios")

    # Initialize session state variables
    if "card_search_query" not in st.session_state: st.session_state.card_search_query = ""
    if "card_selected_folder_path" not in st.session_state: st.session_state.card_selected_folder_path = ""
    if "selected_card_id" not in st.session_state: st.session_state.selected_card_id = None

    # --- Sidebar for actions and filters ---
    col_create, col_search, col_filter_jump = st.columns([1,2,1])
    with col_create:
        if st.button("➕ Create New Card", use_container_width=True):
            st.session_state.selected_card_id = None
            st.rerun()
    
    with col_search:
        st.session_state.card_search_query = st.text_input(
            "Search All Cards", # Changed placeholder
            value=st.session_state.card_search_query,
            placeholder="Name, Description, Folder, Type, Instructions...", # Updated placeholder
            label_visibility="collapsed"
        )

    # --- Data fetching and structuring ---
    if st.session_state.card_search_query:
        all_cards = character_service.search_cards_full_text(st.session_state.card_search_query)
        # When searching, we effectively ignore the folder jump selectbox for display list
        # but keep its state for when search is cleared.
    else:
        all_cards = character_service.get_all_cards()
        
    full_folder_tree = get_card_folder_structure(all_cards) # Build tree from all cards (or searched cards)

    # Folder selectbox for quick jumping (operates on the full list of folders from all_cards_data, not just displayed)
    all_cards_for_folder_list = character_service.get_all_cards() # Get all cards to populate folder list accurately
    all_folder_paths = [""] 
    def get_all_paths(node, current_p, paths_list):
        for name, child_node in node["children"].items():
            new_p = f"{current_p}/{name}" if current_p else name
            paths_list.append(new_p)
            get_all_paths(child_node, new_p, paths_list)
    
    # Populate all_folder_paths from the structure of *all* cards, not just currently displayed/searched
    temp_tree_for_paths = get_card_folder_structure(all_cards_for_folder_list)
    get_all_paths(temp_tree_for_paths, "", all_folder_paths)
    all_folder_paths = sorted(list(set(all_folder_paths)))

    with col_filter_jump:
        try:
            current_path_index = all_folder_paths.index(st.session_state.card_selected_folder_path)
        except ValueError:
            current_path_index = 0
            st.session_state.card_selected_folder_path = ""
        
        selected_jump_path = st.selectbox(
            "Quick Jump to Card Folder",
            options=all_folder_paths,
            index=current_path_index,
            format_func=lambda x: "All Cards (Root)" if x == "" else x,
            label_visibility="collapsed",
            key="card_folder_jump_selectbox" # Added key
        )
        if selected_jump_path != st.session_state.card_selected_folder_path:
            st.session_state.card_selected_folder_path = selected_jump_path
            st.session_state.card_search_query = "" # Clear search when jumping
            st.rerun()

    # --- Main display area ---
    col_display, col_form = st.columns([0.55, 0.45], gap="large")

    with col_display:
        if st.session_state.card_search_query:
            st.subheader(f"Search Results for: \"{st.session_state.card_search_query}\"")
            # `all_cards` here are already the search results
            if not all_cards:
                st.info("No cards found matching your search query.")
            for card in all_cards: # Display search results as a flat list
                if st.button(f"👤 {card.name} ({card.type}) - Folder: {card.folder}", key=f"select_search_card_{card.id}", use_container_width=True):
                    st.session_state.selected_card_id = card.id
                    st.session_state.card_selected_folder_path = card.folder # Navigate to card's folder
                    st.session_state.card_search_query = "" # Clear search
                    st.rerun()
        else: # Normal folder navigation display
            current_folder_display_path = st.session_state.card_selected_folder_path
            path_parts = [part for part in current_folder_display_path.split("/") if part]
            
            bc_cols = st.columns(len(path_parts) + 1)
            if bc_cols[0].button("All Cards (Root)", key="bc_card_root"):
                st.session_state.card_selected_folder_path = ""
                st.rerun()
            
            temp_p = []
            for i, part in enumerate(path_parts):
                temp_p.append(part)
                if bc_cols[i+1].button(part, key=f"bc_card_{'_'.join(temp_p)}"):
                    st.session_state.card_selected_folder_path = "/".join(temp_p)
                    st.rerun()

            current_node = full_folder_tree # Start with the tree based on all_cards (which could be pre-filtered if search was on)
                                         # but for navigation display, we need to traverse from selected_folder_path
            
            # Re-traverse from the absolute root of all cards to find the current node for display
            # This ensures navigation works correctly even if `all_cards` was from a search.
            display_tree_root = get_card_folder_structure(character_service.get_all_cards())
            current_display_node = display_tree_root
            for part in path_parts:
                if part in current_display_node["children"]:
                    current_display_node = current_display_node["children"][part]
                else:
                    st.error("Invalid card folder path selected for display.")
                    current_display_node = display_tree_root # Fallback to root
                    st.session_state.card_selected_folder_path = ""
                    break
            
            st.subheader(f"Contents of: {'Root' if not current_folder_display_path else current_folder_display_path}")

            if current_display_node["children"]:
                st.markdown("**Subfolders:**")
                for folder_name, _ in sorted(current_display_node["children"].items()):
                    subfolder_nav_path = f"{current_folder_display_path}/{folder_name}" if current_folder_display_path else folder_name
                    if st.button(f"📁 {folder_name}", key=f"nav_to_card_folder_{subfolder_nav_path.replace('/','_')}", use_container_width=True):
                        st.session_state.card_selected_folder_path = subfolder_nav_path
                        st.rerun()
            
            if current_display_node["_cards_"]:
                st.markdown("**Cards in this folder:**")
                for card in sorted(current_display_node["_cards_"], key=lambda c: c.name):
                    if st.button(f"👤 {card.name} ({card.type})", key=f"select_item_card_{card.id}", use_container_width=True):
                        st.session_state.selected_card_id = card.id
                        st.rerun()
            
            if not current_display_node["children"] and not current_display_node["_cards_"]:
                st.info("This folder is empty.")

    # --- Form Area (Create/Edit) ---
    with col_form:
        active_card_data: Optional[CharacterCardData] = None
        if st.session_state.get("selected_card_id"):
            card_db = character_service.get_card_by_id(st.session_state.selected_card_id)
            if card_db:
                active_card_data = card_db
                st.subheader(f"Edit: {active_card_data.name}")
            else:
                st.warning("The previously selected card is no longer available.")
                st.session_state.selected_card_id = None
        else:
            st.subheader("Create New Card")
            st.markdown(f"New card will be created in: `{st.session_state.card_selected_folder_path if st.session_state.card_selected_folder_path else '(Root Level)'}`")

        if active_card_data:
            render_edit_card_form(character_service, active_card_data)
        else:
            render_create_card_form(character_service, default_folder=st.session_state.card_selected_folder_path)


def render_create_card_form(character_service: CharacterService, default_folder: str):
    form_default_folder = default_folder if default_folder else "general"
    with st.form(key="card_form_create"):
        name = st.text_input("Name*", key="char_name_create")
        type_val = st.selectbox("Type", ["character", "scenario"], key="char_type_create")
        folder = st.text_input("Folder Path (e.g., fantasy/heroes)", value=form_default_folder, key="char_folder_create")
        description = st.text_area("Description", height=100, key="char_description_create")
        
        st.info("Use `[[variable_name]]` for template variables in instructions.", icon="💡")
        # New structured instruction fields
        system_instruction = st.text_area("System Instruction", height=100, key="char_system_create")
        user_instruction = st.text_area("User Instruction (Optional, e.g., first user turn)", height=100, key="char_user_create")
        assistant_instruction = st.text_area("Assistant Instruction (Optional, e.g., first AI turn)", height=100, key="char_assistant_create")

        if st.form_submit_button("Create Card"):
            folder_val = folder.strip("/").strip()
            if not folder_val: folder_val = "" 

            try:
                # Create CharacterCardData with new fields
                card_data = CharacterCardData(
                    name=name, type=type_val, folder=folder_val,
                    description=description or None,
                    system_instruction=system_instruction or None,
                    user_instruction=user_instruction or None,
                    assistant_instruction=assistant_instruction or None
                )
                # Validation for at least one instruction is handled by Pydantic model
                new_card = character_service.create_card(card_data)
                st.success(f"Card '{new_card.name}' created in folder '{new_card.folder if new_card.folder else '(Root Level)'}'!")
                st.session_state.selected_card_id = new_card.id
                st.session_state.card_selected_folder_path = new_card.folder
                st.session_state.card_search_query = "" # Clear search
                st.rerun()
            except ValueError as ve: 
                 st.error(f"Validation Error: {ve}") # Catch Pydantic validation errors
            except Exception as e:
                st.error(f"Failed to save card: {e}")

def render_edit_card_form(character_service: CharacterService, card: CharacterCardData):
    with st.form(key=f"card_form_edit_{card.id}"):
        name = st.text_input("Name*", value=card.name, key=f"char_name_edit_{card.id}")
        type_val = st.selectbox("Type", ["character", "scenario"], index=["character", "scenario"].index(card.type), key=f"char_type_edit_{card.id}")
        folder = st.text_input("Folder Path", value=card.folder, key=f"char_folder_edit_{card.id}")
        description = st.text_area("Description", value=card.description or "", height=100, key=f"char_description_edit_{card.id}")
        
        st.info("Use `[[variable_name]]` for template variables.", icon="💡")
        # New structured instruction fields
        system_instruction = st.text_area("System Instruction", value=card.system_instruction or "", height=100, key=f"char_system_edit_{card.id}")
        user_instruction = st.text_area("User Instruction", value=card.user_instruction or "", height=100, key=f"char_user_edit_{card.id}")
        assistant_instruction = st.text_area("Assistant Instruction", value=card.assistant_instruction or "", height=100, key=f"char_assistant_edit_{card.id}")
        
        if st.form_submit_button("Save Changes"):
            folder_val = folder.strip("/").strip()
            if not folder_val: folder_val = ""
            try:
                card_data_to_update = CharacterCardData( 
                    id=card.id, 
                    created_at=card.created_at, 
                    name=name, type=type_val, folder=folder_val,
                    description=description or None, 
                    system_instruction=system_instruction or None,
                    user_instruction=user_instruction or None,
                    assistant_instruction=assistant_instruction or None
                )
                # Validation by Pydantic model
                updated_card = character_service.update_card(card.id, card_data_to_update)
                st.success(f"Card '{updated_card.name}' updated successfully!")
                st.session_state.card_selected_folder_path = updated_card.folder
                st.session_state.card_search_query = "" # Clear search
                st.rerun()
            except ValueError as ve: 
                 st.error(f"Validation Error: {ve}")
            except Exception as e:
                st.error(f"Failed to save card: {e}")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"💬 Chat with this {card.type.capitalize()}", use_container_width=True, key=f"chat_card_{card.id}"):
            st.session_state.active_card = card 
            st.session_state.active_prompt = None
            st.session_state.view = "chat"
            st.session_state.chat_stage = "setup" 
            st.session_state.current_messages_data = [] 
            st.session_state.current_chat_session_id = None 
            st.session_state.chat_loaded_item_id = None
            st.rerun()
    with col2:
        if st.button("🗑️ Delete Card", type="primary", use_container_width=True, key=f"delete_card_{card.id}"):
            confirm_delete_key = f"confirm_delete_card_{card.id}"
            st.session_state[confirm_delete_key] = st.session_state.get(confirm_delete_key, False)

            if st.session_state[confirm_delete_key]:
                if character_service.delete_card(card.id):
                    st.success(f"Card '{card.name}' deleted.")
                    st.session_state.selected_card_id = None
                    del st.session_state[confirm_delete_key]
                    st.rerun()
                else:
                    st.error("Failed to delete card.")
            else:
                st.warning(f"Are you sure you want to delete '{card.name}'? This cannot be undone.")
                c1_del, c2_del = st.columns(2) # Renamed to avoid conflict
                if c1_del.button("Confirm Delete", key=f"confirm_del_btn_card_{card.id}", use_container_width=True):
                    st.session_state[confirm_delete_key] = True
                    st.rerun()
                if c2_del.button("Cancel", key=f"cancel_del_btn_card_{card.id}", use_container_width=True):
                    st.rerun()
