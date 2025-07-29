"""
Renders the Streamlit UI for managing character and scenario cards using a drill-down navigation.
Now includes search, image import/association, and AI generation.
Manual image upload and backup functionality have been removed.
"""
import streamlit as st
from typing import List, Dict, Optional
from collections import defaultdict

from promptbox.services.character_service import CharacterService
from promptbox.services.llm_service import LLMService
from promptbox.models.data_models import CharacterCardData
from promptbox.utils.image_handler import read_metadata_from_image


def _handle_card_delete(character_service: CharacterService, card_id: int, card_name: str):
    """Callback function to delete a card and reset UI state."""
    if character_service.delete_card(card_id):
        st.toast(f"Card '{card_name}' deleted successfully.", icon="✅")
        st.session_state.selected_card_id = None
        st.session_state.confirming_delete_card_id = None
        st.rerun()
    else:
        st.error(f"Failed to delete card '{card_name}'. It might be in use or a database error occurred.")
        st.session_state.confirming_delete_card_id = None

def _set_confirm_delete_state_card(card_id: int):
    st.session_state.confirming_delete_card_id = card_id

def _cancel_delete_state_card():
    st.session_state.confirming_delete_card_id = None

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


def render_character_view(character_service: CharacterService, llm_service: LLMService):
    st.header("Manage Characters & Scenarios")

    # Initialize session state variables
    if "card_search_query" not in st.session_state:
        st.session_state.card_search_query = ""
    if "card_selected_folder_path" not in st.session_state:
        st.session_state.card_selected_folder_path = ""
    if "selected_card_id" not in st.session_state:
        st.session_state.selected_card_id = None
    if "confirming_delete_card_id" not in st.session_state:
        st.session_state.confirming_delete_card_id = None
    if "card_form_values" not in st.session_state:
        st.session_state.card_form_values = {}

    # --- Top Level Actions ---
    col_actions, col_search = st.columns([1, 2])
    with col_actions:
        if st.button("➕ Create New Card", use_container_width=True):
            st.session_state.selected_card_id = None
            st.session_state.confirming_delete_card_id = None
            st.session_state.card_form_values = {} # Clear form values
            st.rerun()

        png_file = st.file_uploader(
            "📤 Import Card from Image", type=["png", "jpg", "jpeg"], key="png_importer", help="Import a character card and its image from metadata."
        )
        if png_file:
            with st.spinner("Importing from image..."):
                try:
                    image_bytes = png_file.getvalue()
                    new_card = character_service.import_card_from_png(image_bytes)
                    st.success(f"Successfully imported card '{new_card.name}'!")
                    st.session_state.selected_card_id = new_card.id
                    st.session_state.card_selected_folder_path = new_card.folder
                    st.rerun()
                except Exception as e:
                    st.error(f"Import failed: {e}")
                    st.error("Ensure the image is a valid character card with metadata in the 'chara' text chunk.")


    with col_search:
        st.session_state.card_search_query = st.text_input(
            "Search All Cards", value=st.session_state.card_search_query,
            placeholder="Name, Description, Folder, Type...", label_visibility="collapsed")
    
    # --- Main two-column layout ---
    col_display, col_form = st.columns([0.55, 0.45], gap="large")

    with col_display:
        if st.session_state.card_search_query:
            st.subheader(f"Search Results for: '{st.session_state.card_search_query}'", anchor="search_results")
            all_cards = character_service.search_cards_full_text(st.session_state.card_search_query)
            if not all_cards:
                st.info("No cards found matching your search query.")
            for card in all_cards:
                if st.button(f"👤 {card.name} ({card.type}) - Folder: {card.folder}", key=f"select_search_card_{card.id}", use_container_width=True):
                    st.session_state.selected_card_id = card.id
                    st.session_state.card_selected_folder_path = card.folder
                    st.session_state.card_search_query = ""
                    st.session_state.confirming_delete_card_id = None
                    st.rerun()
        else:
            all_cards = character_service.get_all_cards()
            full_folder_tree = get_card_folder_structure(all_cards)
            current_folder_display_path = st.session_state.card_selected_folder_path
            path_parts = [part for part in current_folder_display_path.split("/") if part]

            bc_cols = st.columns(len(path_parts) + 1)
            if bc_cols[0].button("All Cards (Root)"):
                st.session_state.card_selected_folder_path = ""
                st.rerun()

            temp_p = []
            for i, part in enumerate(path_parts):
                temp_p.append(part)
                if bc_cols[i+1].button(part, key=f"bc_card_{'_'.join(temp_p)}"):
                    st.session_state.card_selected_folder_path = "/".join(temp_p)
                    st.rerun()

            current_display_node = full_folder_tree
            for part in path_parts:
                if part in current_display_node["children"]:
                    current_display_node = current_display_node["children"][part]
                else:
                    st.error("Invalid card folder path selected for display.")
                    current_display_node = full_folder_tree
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
                        st.session_state.confirming_delete_card_id = None
                        st.rerun()

            if not current_display_node["children"] and not current_display_node["_cards_"]:
                st.info("This folder is empty.")


    with col_form:
        active_card_data: Optional[CharacterCardData] = None
        if st.session_state.get("selected_card_id"):
            card_db = character_service.get_card_by_id(st.session_state.selected_card_id)
            if card_db:
                active_card_data = card_db
                st.subheader(f"Edit Card: {active_card_data.name}")
            else:
                st.warning("The previously selected card is no longer available.")
                st.session_state.selected_card_id = None
        else:
            st.subheader("Create New Card")

        render_card_form(character_service, llm_service, card=active_card_data)



def render_card_form(character_service: CharacterService, llm_service: LLMService, card: Optional[CharacterCardData] = None):
    is_edit = card is not None
    form_key = f"card_form_edit_{card.id}" if is_edit else "card_form_create"

    # Check for generated content from a previous run and apply it before rendering widgets
    if "generated_content" in st.session_state:
        field_key = st.session_state.generated_content["field"]
        text = st.session_state.generated_content["text"]
        st.session_state[f"{form_key}_{field_key}"] = text
        del st.session_state.generated_content

    # Helper to get value from session state or card object
    def get_form_value(field_name: str, default: any = "") -> any:
        # Prioritize session state, then card object, then default
        form_state_key = f"{form_key}_{field_name}"
        if form_state_key in st.session_state:
            return st.session_state[form_state_key]
        if is_edit:
            return getattr(card, field_name, default)
        return default

    # === THE FORM ===
    with st.form(key=form_key):
        name = st.text_input("Name*", value=get_form_value("name"), key=f"{form_key}_name")
        type_val = st.selectbox("Type", ["character", "scenario"], index=["character", "scenario"].index(get_form_value("type", "character")), key=f"{form_key}_type")
        folder = st.text_input("Folder Path", value=get_form_value("folder", "general"), key=f"{form_key}_folder")

        # Image Upload and Display
        current_image_data = get_form_value("image_data", None)
        if current_image_data:
            st.image(current_image_data, caption="Current Card Image", use_column_width=True)
            if st.checkbox("Remove current image", key=f"{form_key}_remove_image"):
                current_image_data = None
                st.session_state[f"{form_key}_image_data"] = None # Clear from session state immediately

        uploaded_file = st.file_uploader("Upload Card Image (PNG/JPG)", type=["png", "jpg", "jpeg"], key=f"{form_key}_image_uploader")

        if uploaded_file is not None:
            uploaded_image_bytes = uploaded_file.getvalue()
            try:
                # Attempt to read metadata from the uploaded image
                extracted_metadata = read_metadata_from_image(uploaded_image_bytes)
                if extracted_metadata:
                    st.info("Metadata found in image! Populating form fields.")
                    # Update session state with extracted metadata to pre-fill form
                    for field, value in extracted_metadata.items():
                        if field in ["name", "description", "first_message", "example_dialog", "example_scene", "folder", "type", "associated_scenarios", "associated_characters"]:
                            st.session_state[f"{form_key}_{field}"] = value
                    # Also store the image data itself
                    st.session_state[f"{form_key}_image_data"] = uploaded_image_bytes
                else:
                    st.info("No character card metadata found in image. Image will be saved as-is.")
                    st.session_state[f"{form_key}_image_data"] = uploaded_image_bytes
            except Exception as e:
                st.error(f"Error processing image: {e}. Please try another image.")
                st.session_state[f"{form_key}_image_data"] = None # Clear problematic image
        elif current_image_data is not None:
            # If no new file uploaded, but there was an existing image, keep it unless marked for removal
            st.session_state[f"{form_key}_image_data"] = current_image_data
        else:
            # Ensure image_data is None if no image is present or uploaded
            st.session_state[f"{form_key}_image_data"] = None

        

        st.markdown("**Description**")
        description = st.text_area("Description", value=get_form_value("description"), height=100, label_visibility="collapsed", key=f"{form_key}_description")

        st.markdown("**First Message***")
        first_message = st.text_area("First Message", value=get_form_value("first_message"), height=120, label_visibility="collapsed", key=f"{form_key}_first_message")

        if type_val == "character":
            st.markdown("**Example Dialog**")
            example_dialog = st.text_area("Example Dialog", value=get_form_value("example_dialog"), height=120, label_visibility="collapsed", key=f"{form_key}_example_dialog")
            example_scene = None
        else: # scenario
            st.markdown("**Example Scene**")
            example_scene = st.text_area("Example Scene", value=get_form_value("example_scene"), height=120, label_visibility="collapsed", key=f"{form_key}_example_scene")
            example_dialog = None

        if type_val == "character":
            all_scenarios = character_service.get_all_cards(card_type='scenario')
            scenario_options = {s.id: s.name for s in all_scenarios}
            selected_scenarios = st.multiselect("Link to Scenarios", options=list(scenario_options.keys()), format_func=lambda x: scenario_options[x], default=get_form_value("associated_scenarios", []), key=f"{form_key}_associated_scenarios")
            selected_characters = []
        else: # scenario
            all_characters = character_service.get_all_cards(card_type='character')
            char_options = {c.id: c.name for c in all_characters}
            selected_characters = st.multiselect("Link to Characters", options=list(char_options.keys()), format_func=lambda x: char_options[x], default=get_form_value("associated_characters", []), key=f"{form_key}_associated_characters")
            selected_scenarios = []

        # The one and only submit button
        submitted = st.form_submit_button("Save Changes" if is_edit else "Create Card")

        if submitted:
            try:
                card_data = CharacterCardData(
                    id=card.id if is_edit else None,
                    name=name, type=type_val, folder=folder,
                    description=description or None,
                    first_message=first_message or None,
                    example_dialog=example_dialog or None,
                    example_scene=example_scene or None,
                    associated_scenarios=selected_scenarios,
                    associated_characters=selected_characters,
                    image_data=st.session_state.get(f"{form_key}_image_data")
                )
                if is_edit:
                    result = character_service.update_card(card.id, card_data)
                    st.success(f"Card '{result.name}' updated!")
                else:
                    result = character_service.create_card(card_data)
                    st.success(f"Card '{result.name}' created!")

                st.session_state.selected_card_id = result.id
                st.rerun()
            except ValueError as ve:
                st.error(f"Validation Error: {ve}")
            except Exception as e:
                st.error(f"Failed to save card: {e}")

    # === AI GENERATION (OUTSIDE THE FORM) ===
    with st.expander("✨ AI Generation"):
        field_to_generate_map = {
            "Description": "description",
            "First Message": "first_message",
            "Example Dialog": "example_dialog",
            "Example Scene": "example_scene",
        }
        visible_fields = ["Description", "First Message"]
        type_val_for_gen = st.session_state.get(f"{form_key}_type", get_form_value("type", "character"))

        if type_val_for_gen == 'character':
            visible_fields.append("Example Dialog")
        else:
            visible_fields.append("Example Scene")

        selected_field_label = st.selectbox("Field to Generate", visible_fields)
        field_to_generate_key = field_to_generate_map[selected_field_label]

        available_models = llm_service.list_available_models()
        provider = st.selectbox("Provider", list(available_models.keys()), key=f"gen_prov_{form_key}")
        model = st.selectbox("Model", available_models.get(provider, []), key=f"gen_model_{form_key}")

        if st.button("🚀 Generate Content", key=f"exec_gen_{form_key}"):
            if not provider or not model:
                st.warning("Please select a provider and model.")
            else:
                with st.spinner("Generating content..."):
                    # Create a temporary card data object from current form values in session_state
                    form_values = {}
                    for key in st.session_state:
                        if key.startswith(form_key):
                            field = key.replace(f"{form_key}_", "")
                            form_values[field] = st.session_state[key]

                    if not form_values.get("name"):
                        st.warning("Please enter a name for the card before generating content.")
                    else:
                        try:
                            temp_card_data = CharacterCardData(**form_values)
                            llm = llm_service.get_chat_model(provider, model)
                            generated_text = character_service.generate_card_details(field_to_generate_key, temp_card_data, llm)

                            if generated_text:
                                # Set a temporary state to be handled on the next rerun
                                st.session_state.generated_content = {
                                    "field": field_to_generate_key,
                                    "text": generated_text
                                }
                                st.rerun()
                            else:
                                st.error("Failed to generate content.")
                        except ValueError as ve:
                            st.error(f"Validation Error: {ve}")

    # === OTHER ACTIONS (OUTSIDE THE FORM) ===
    if is_edit:
        st.markdown("---")
        # Confirmation Dialog Logic
        if st.session_state.confirming_delete_card_id == card.id:
             st.error(f"**Are you sure you want to permanently delete card '{card.name}'?**")
             c1, c2, _ = st.columns([1, 1, 3])
             c1.button("✅ Yes, Delete", use_container_width=True, on_click=_handle_card_delete, args=(character_service, card.id, card.name))
             c2.button("❌ No, Cancel", use_container_width=True, on_click=_cancel_delete_state_card)

        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"💬 Chat with this {card.type.capitalize()}", use_container_width=True):
                st.session_state.active_card = card
                st.session_state.active_prompt = None
                st.session_state.view = "chat"
                st.session_state.chat_stage = "setup"
                st.rerun()
        with col2:
            st.button("🗑️ Delete Card", type="primary", use_container_width=True, on_click=_set_confirm_delete_state_card, args=(card.id,))