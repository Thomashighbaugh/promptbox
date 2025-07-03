"""
Service layer for handling business logic related to Character Cards.
"""
from promptbox.db.connection_manager import get_db, DB_CARDS, SQLAlchemySession as Session # MODIFIED IMPORT
from promptbox.db.models import CharacterCard as CharacterCardDBModel
from promptbox.models.data_models import CharacterCardData
from typing import List, Optional
import streamlit as st # Added for potential error messages

class CharacterService:
    def _db_to_pydantic(self, card: CharacterCardDBModel) -> CharacterCardData:
        return CharacterCardData.model_validate(card)

    def create_card(self, card_data: CharacterCardData) -> CharacterCardData:
        with get_db(DB_CARDS) as db: # MODIFIED
            db_card_data = card_data.model_dump(exclude={'id', 'created_at', 'updated_at'})
            new_card = CharacterCardDBModel(**db_card_data)
            db.add(new_card)
            db.commit()
            db.refresh(new_card)
            return self._db_to_pydantic(new_card)

    def get_card_by_id(self, card_id: int) -> Optional[CharacterCardData]:
        with get_db(DB_CARDS) as db: # MODIFIED
            card = db.query(CharacterCardDBModel).filter(CharacterCardDBModel.id == card_id).first()
            return self._db_to_pydantic(card) if card else None

    def get_all_cards(self) -> List[CharacterCardData]:
        with get_db(DB_CARDS) as db: # MODIFIED
            cards = db.query(CharacterCardDBModel).order_by(CharacterCardDBModel.folder, CharacterCardDBModel.name).all()
            return [self._db_to_pydantic(c) for c in cards]

    def update_card(self, card_id: int, card_data: CharacterCardData) -> Optional[CharacterCardData]:
        with get_db(DB_CARDS) as db: # MODIFIED
            card = db.query(CharacterCardDBModel).filter(CharacterCardDBModel.id == card_id).first()
            if not card:
                return None

            update_data = card_data.model_dump(exclude_unset=True, exclude={'id', 'created_at', 'updated_at'})
            for key, value in update_data.items():
                setattr(card, key, value)
            
            # Ensure fields that could be None are explicitly set if present in update_data
            # This is important if an instruction is being cleared (set to None)
            # model_dump with exclude_unset=True might not include keys if their value is None and they were None before.
            # However, if a field was "text" and is now None, exclude_unset should include it.
            # The setattr loop should handle this. The explicit assignments below are redundant if exclude_unset works as expected
            # for nullifying fields. Keeping them for safety if a field is explicitly set to None in Pydantic model.
            if 'system_instruction' in update_data:
                card.system_instruction = update_data.get('system_instruction')
            if 'user_instruction' in update_data:
                card.user_instruction = update_data.get('user_instruction')
            if 'assistant_instruction' in update_data:
                card.assistant_instruction = update_data.get('assistant_instruction')

            db.commit()
            db.refresh(card)
            return self._db_to_pydantic(card)

    def delete_card(self, card_id: int) -> bool:
        with get_db(DB_CARDS) as db: # MODIFIED
            card = db.query(CharacterCardDBModel).filter(CharacterCardDBModel.id == card_id).first()
            if card:
                # Add check for related chat sessions (logical, not DB constraint)
                # from promptbox.services.chat_service import ChatService # Avoid circular import
                # chat_service = ChatService() # Or get it via st.session_state
                # sessions_using_card = chat_service.get_sessions_by_originating_card(card_id)
                # if sessions_using_card:
                #    st.error(f"Cannot delete card. It is used by {len(sessions_using_card)} chat session(s).")
                #    return False
                db.delete(card)
                db.commit()
                return True
            return False

    def search_cards_full_text(self, query: str) -> List[CharacterCardData]:
        """Searches cards by name, description, folder, type, and instructions."""
        from sqlalchemy import or_ # local import for or_
        with get_db(DB_CARDS) as db: # MODIFIED
            search_term = f"%{query.lower()}%"
            results = db.query(CharacterCardDBModel).filter(
                or_(
                    CharacterCardDBModel.name.ilike(search_term),
                    CharacterCardDBModel.description.ilike(search_term),
                    CharacterCardDBModel.folder.ilike(search_term),
                    CharacterCardDBModel.type.ilike(search_term),
                    CharacterCardDBModel.system_instruction.ilike(search_term),
                    CharacterCardDBModel.user_instruction.ilike(search_term),
                    CharacterCardDBModel.assistant_instruction.ilike(search_term),
                )
            ).order_by(CharacterCardDBModel.folder, CharacterCardDBModel.name).all()
            return [self._db_to_pydantic(r) for r in results]
