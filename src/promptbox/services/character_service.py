"""
Service layer for handling business logic related to Character Cards.
"""
from promptbox.db.database import get_db, Session # Added Session for type hinting
from promptbox.db.models import CharacterCard as CharacterCardDBModel
from promptbox.models.data_models import CharacterCardData
from typing import List, Optional # Ensure List and Optional are imported

class CharacterService:
    def _db_to_pydantic(self, card: CharacterCardDBModel) -> CharacterCardData:
        return CharacterCardData.model_validate(card)

    def create_card(self, card_data: CharacterCardData) -> CharacterCardData:
        with get_db() as db:
            # model_dump will now include system_instruction, user_instruction, assistant_instruction
            # and exclude 'instructions' if it was accidentally passed.
            db_card_data = card_data.model_dump(exclude={'id', 'created_at', 'updated_at'})
            new_card = CharacterCardDBModel(**db_card_data)
            db.add(new_card)
            db.commit()
            db.refresh(new_card)
            return self._db_to_pydantic(new_card)

    def get_card_by_id(self, card_id: int) -> Optional[CharacterCardData]:
        with get_db() as db:
            card = db.query(CharacterCardDBModel).filter(CharacterCardDBModel.id == card_id).first()
            return self._db_to_pydantic(card) if card else None

    def get_all_cards(self) -> List[CharacterCardData]:
        with get_db() as db:
            cards = db.query(CharacterCardDBModel).order_by(CharacterCardDBModel.folder, CharacterCardDBModel.name).all()
            return [self._db_to_pydantic(c) for c in cards]

    def update_card(self, card_id: int, card_data: CharacterCardData) -> Optional[CharacterCardData]:
        with get_db() as db:
            card = db.query(CharacterCardDBModel).filter(CharacterCardDBModel.id == card_id).first()
            if not card:
                return None

            # model_dump will correctly get the new instruction fields
            update_data = card_data.model_dump(exclude_unset=True, exclude={'id', 'created_at', 'updated_at'})
            for key, value in update_data.items():
                setattr(card, key, value)
            
            # Ensure fields that could be None are explicitly set if present in update_data
            # This is important if an instruction is being cleared (set to None)
            card.system_instruction = update_data.get('system_instruction')
            card.user_instruction = update_data.get('user_instruction')
            card.assistant_instruction = update_data.get('assistant_instruction')


            db.commit()
            db.refresh(card)
            return self._db_to_pydantic(card)

    def delete_card(self, card_id: int) -> bool:
        with get_db() as db:
            card = db.query(CharacterCardDBModel).filter(CharacterCardDBModel.id == card_id).first()
            if card:
                db.delete(card)
                db.commit()
                return True
            return False

    # No search_cards_full_text implemented yet, but if added, it would search the new instruction fields.
