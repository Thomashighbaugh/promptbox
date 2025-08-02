"""
Service layer for handling business logic related to Character Cards.
"""
from typing import List, Optional

import streamlit as st
from langchain_core.language_models import BaseChatModel

from promptbox.db.connection_manager import DB_CARDS, get_db
from promptbox.db.models import CharacterCard as CharacterCardDBModel
from promptbox.models.data_models import CharacterCardData
from promptbox.utils.image_handler import read_metadata_from_image, ImageMetadataError


class CharacterService:
    def _db_to_pydantic(self, card: CharacterCardDBModel) -> CharacterCardData:
        # Based on the card type, populate the correct association list
        associated_scenarios = []
        if card.type == 'character':
            associated_scenarios = [s.id for s in card.scenarios]

        associated_characters = []
        if card.type == 'scenario':
            associated_characters = [c.id for c in card.characters]

        return CharacterCardData(
            id=card.id,
            name=card.name,
            folder=card.folder,
            description=card.description,
            type=card.type,
            image_data=card.image_data,
            first_message=card.first_message,
            example_dialog=card.example_dialog,
            example_scene=card.example_scene,
            created_at=card.created_at,
            updated_at=card.updated_at,
            associated_scenarios=associated_scenarios,
            associated_characters=associated_characters,
        )

    def create_card(self, card_data: CharacterCardData) -> CharacterCardData:
        with get_db(DB_CARDS) as db:
            db_card_data = card_data.model_dump(
                exclude={'id', 'created_at', 'updated_at', 'associated_scenarios', 'associated_characters'}
            )
            new_card = CharacterCardDBModel(**db_card_data)
            db.add(new_card)
            db.commit()  # Commit to get an ID for the new card

            # Handle relationships
            if new_card.type == 'character' and card_data.associated_scenarios:
                scenarios = db.query(CharacterCardDBModel).filter(
                    CharacterCardDBModel.id.in_(card_data.associated_scenarios)).all()
                new_card.scenarios.extend(scenarios)
            elif new_card.type == 'scenario' and card_data.associated_characters:
                characters = db.query(CharacterCardDBModel).filter(
                    CharacterCardDBModel.id.in_(card_data.associated_characters)).all()
                new_card.characters.extend(characters)

            db.commit()
            db.refresh(new_card)
            return self._db_to_pydantic(new_card)

    def get_card_by_id(self, card_id: int) -> Optional[CharacterCardData]:
        with get_db(DB_CARDS) as db:
            card = db.query(CharacterCardDBModel).filter(CharacterCardDBModel.id == card_id).first()
            return self._db_to_pydantic(card) if card else None

    def get_all_cards(self, card_type: Optional[str] = None) -> List[CharacterCardData]:
        with get_db(DB_CARDS) as db:
            query = db.query(CharacterCardDBModel)
            if card_type:
                query = query.filter(CharacterCardDBModel.type == card_type)
            cards = query.order_by(CharacterCardDBModel.folder, CharacterCardDBModel.name).all()
            return [self._db_to_pydantic(c) for c in cards]

    def update_card(self, card_id: int, card_data: CharacterCardData) -> Optional[CharacterCardData]:
        with get_db(DB_CARDS) as db:
            card = db.query(CharacterCardDBModel).filter(CharacterCardDBModel.id == card_id).first()
            if not card:
                return None

            update_data = card_data.model_dump(
                exclude_unset=True,
                exclude={'id', 'created_at', 'updated_at', 'associated_scenarios', 'associated_characters'}
            )
            for key, value in update_data.items():
                setattr(card, key, value)

            # Handle relationships
            if card.type == 'character':
                card.scenarios.clear()
                if card_data.associated_scenarios:
                    scenarios = db.query(CharacterCardDBModel).filter(
                        CharacterCardDBModel.id.in_(card_data.associated_scenarios)).all()
                    card.scenarios.extend(scenarios)
            elif card.type == 'scenario':
                card.characters.clear()
                if card_data.associated_characters:
                    characters = db.query(CharacterCardDBModel).filter(
                        CharacterCardDBModel.id.in_(card_data.associated_characters)).all()
                    card.characters.extend(characters)

            db.commit()
            db.refresh(card)
            return self._db_to_pydantic(card)

    def delete_card(self, card_id: int) -> bool:
        with get_db(DB_CARDS) as db:
            card = db.query(CharacterCardDBModel).filter(CharacterCardDBModel.id == card_id).first()
            if card:
                db.delete(card)
                db.commit()
                return True
            return False

    def search_cards_full_text(self, query: str) -> List[CharacterCardData]:
        from sqlalchemy import or_
        with get_db(DB_CARDS) as db:
            search_term = f"%{query.lower()}%"
            results = db.query(CharacterCardDBModel).filter(
                or_(
                    CharacterCardDBModel.name.ilike(search_term),
                    CharacterCardDBModel.description.ilike(search_term),
                    CharacterCardDBModel.folder.ilike(search_term),
                    CharacterCardDBModel.type.ilike(search_term),
                    CharacterCardDBModel.first_message.ilike(search_term),
                    CharacterCardDBModel.example_dialog.ilike(search_term),
                    CharacterCardDBModel.example_scene.ilike(search_term),
                )
            ).order_by(CharacterCardDBModel.folder, CharacterCardDBModel.name).all()
            return [self._db_to_pydantic(r) for r in results]

    def get_card_by_name(self, name: str) -> Optional[CharacterCardData]:
        with get_db(DB_CARDS) as db:
            # Use ilike for case-insensitive comparison
            card = db.query(CharacterCardDBModel).filter(CharacterCardDBModel.name.ilike(name)).first()
            return self._db_to_pydantic(card) if card else None

    def import_card_from_png(self, image_bytes: bytes) -> tuple[CharacterCardData, bool, list[str]]:
        metadata = None
        try:
            metadata = read_metadata_from_image(image_bytes)
        except ImageMetadataError as e:
            st.error(f"Error reading image metadata: {e}")

        if not metadata:
            st.warning("No character card metadata found in image. Creating a basic card.")
            card_data = CharacterCardData(name="Imported Image Card", image_data=image_bytes)
            existing_card = self.get_card_by_name(card_data.name)
            return card_data, existing_card is not None, []

        st.info("Metadata found in image. Processing card data.")
        spec = metadata.get('spec', 'chara_card_v2')
        data = metadata.get('data', {}) if spec == 'chara_card_v2' else metadata
        
        missing_fields = []

        name = data.get("name", "Unnamed Import").strip()
        if not data.get("name"):
            missing_fields.append("Name")

        description = data.get("description", "")
        if not description:
            missing_fields.append("Description")

        personality = data.get("personality", "")
        if personality:
            description = f"{description}\n\n{personality}".strip()

        first_message = data.get("first_mes" if spec == 'chara_card_v2' else "first_message", "")
        if not first_message:
            missing_fields.append("First Message")

        example_dialog = data.get("mes_example" if spec == 'chara_card_v2' else "example_dialog", "")
        if not example_dialog:
            missing_fields.append("Example Dialog")

        params = {
            "name": name,
            "description": description,
            "first_message": first_message,
            "example_dialog": example_dialog,
            "type": "character",
            "image_data": image_bytes
        }

        card_data = CharacterCardData(**params)
        existing_card = self.get_card_by_name(card_data.name)
        
        return card_data, existing_card is not None, missing_fields

    def generate_card_details(self, field_to_generate: str, card_data: CharacterCardData, llm: BaseChatModel) -> str | None:
        """Generates content for a specific field of a character card using an LLM."""
        context_prompt = f"""
        You are a creative writer specializing in creating role-playing characters and scenarios.
        Based on the following information about a card, generate a compelling value for the '{field_to_generate}' field.

        Existing Card Information:
        - Name: {card_data.name}
        - Type: {card_data.type}
        - Description: {card_data.description or 'Not provided.'}
        - First Message: {card_data.first_message or 'Not provided.'}
        - Example Dialog: {card_data.example_dialog or 'Not provided.'}
        - Example Scene: {card_data.example_scene or 'Not provided.'}

        Generate the content for the '{field_to_generate}' field.
        Return ONLY the generated text for that field. Do not include the field name, explanations, or any other text.
        """
        try:
            response = llm.invoke(context_prompt)
            return response.content
        except Exception as e:
            st.error(f"An error occurred during content generation: {e}")
            return None
