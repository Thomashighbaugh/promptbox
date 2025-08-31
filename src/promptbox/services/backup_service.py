import os
import shutil
import tempfile
from datetime import datetime
from typing import Tuple, List
from PIL import Image

from promptbox.core.config import settings
from promptbox.services.prompt_service import PromptService
from promptbox.services.character_service import CharacterService
from promptbox.services.chat_service import ChatService
from promptbox.models.data_models import PromptData, CharacterCardData, ChatSessionData
from promptbox.utils.archiver import create_tar_gz_archive
from promptbox.utils.image_handler import write_metadata_to_png

class BackupService:
    def __init__(self, prompt_service: PromptService, character_service: CharacterService, chat_service: ChatService):
        self.prompt_service = prompt_service
        self.character_service = character_service
        self.chat_service = chat_service

    def backup_all_core_databases(self) -> List[Tuple[bool, str]]:
        """Backs up prompts, cards, and sessions databases."""
        results = []
        db_paths_to_backup = {
            "prompts": settings.prompts_database_path,
            "cards": settings.cards_database_path,
            "sessions": settings.sessions_database_path,
        }

        for db_name, db_path in db_paths_to_backup.items():
            if not db_path.exists():
                results.append((False, f"Database file for '{db_name}' not found at {db_path}."))
                continue

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"promptbox_{db_name}_db_backup_{timestamp}.db"
            backup_filepath = settings.backup_dir / backup_filename

            try:
                shutil.copy(db_path, backup_filepath)
                results.append((True, f"Successfully created database backup: {backup_filepath.name}"))
            except Exception as e:
                results.append((False, f"Failed to create backup for '{db_name}': {e}"))
        return results

    def backup_prompts_to_archive(self) -> Tuple[bool, str]:
        all_prompts = self.prompt_service.get_all_prompts()
        if not all_prompts:
            return False, "No prompts found to back up."

        with tempfile.TemporaryDirectory() as temp_dir:
            for prompt in all_prompts:
                self._create_markdown_file_for_prompt(prompt, temp_dir)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_filename = f"promptbox_prompts_markdown_backup_{timestamp}.tar.gz"
            archive_filepath = settings.backup_dir / archive_filename
            archive_name_in_tar = f"promptbox_prompts_backup_{timestamp}"

            try:
                result_path = create_tar_gz_archive(temp_dir, archive_filepath, arcname=archive_name_in_tar)
                if result_path:
                    return True, f"Successfully created prompt archive: {archive_filepath.name}"
                else:
                    return False, "Failed to create the archive file."
            except Exception as e:
                return False, f"Failed to create prompt archive: {e}"

    def backup_cards_to_archive(self) -> Tuple[bool, str]:
        all_cards = self.character_service.get_all_cards()
        if not all_cards:
            return False, "No character/scenario cards found to back up."

        with tempfile.TemporaryDirectory() as temp_dir:
            for card in all_cards:
                self._create_markdown_file_for_card(card, temp_dir)
                self._create_png_file_for_card(card, temp_dir)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_filename = f"promptbox_cards_backup_{timestamp}.tar.gz"
            archive_filepath = settings.backup_dir / archive_filename
            archive_name_in_tar = f"promptbox_cards_backup_{timestamp}"

            try:
                result_path = create_tar_gz_archive(temp_dir, archive_filepath, arcname=archive_name_in_tar)
                if result_path:
                    return True, f"Successfully created card archive: {archive_filepath.name}"
                else:
                    return False, "Failed to create the archive file."
            except Exception as e:
                return False, f"Failed to create card archive: {e}"

    def _create_markdown_file_for_prompt(self, prompt: PromptData, base_path: str):
        safe_folder_path = os.path.join(base_path, *prompt.folder.replace("\\", "/").split("/"))
        os.makedirs(safe_folder_path, exist_ok=True)

        safe_filename = "".join(c for c in prompt.name if c.isalnum() or c in (' ', '_', '-')).rstrip()
        filepath = os.path.join(safe_folder_path, f"{safe_filename}.md")

        frontmatter = f"---\nname: \"{prompt.name}\"\ndescription: \"{prompt.description or ''}\"\nfolder: \"{prompt.folder}\"\ncreated_at: \"{prompt.created_at.isoformat() if prompt.created_at else ''}\"\nupdated_at: \"{prompt.updated_at.isoformat() if prompt.updated_at else ''}\"\n---\n\n"
        content = ""
        if prompt.system_instruction:
            content += f"### System Instruction\n\n{prompt.system_instruction}\n\n"
        if prompt.user_instruction:
            content += f"### User Instruction\n\n{prompt.user_instruction}\n\n"
        if prompt.assistant_instruction:
            content += f"### Assistant Instruction\n\n{prompt.assistant_instruction}\n\n"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(frontmatter + content.strip())

    def _create_markdown_file_for_card(self, card: CharacterCardData, base_path: str):
        safe_folder_path = os.path.join(base_path, *card.folder.replace("\\", "/").split("/"))
        os.makedirs(safe_folder_path, exist_ok=True)

        safe_filename = "".join(c for c in card.name if c.isalnum() or c in (' ', '_', '-')).rstrip()
        filepath = os.path.join(safe_folder_path, f"{safe_filename}.md")

        frontmatter_parts = [
            f'name: "{card.name}"',
            f'type: "{card.type}"',
            f'description: "{card.description or ""}"',
            f'folder: "{card.folder}"',
        ]
        frontmatter = "---\n" + "\n".join(frontmatter_parts) + "\n---\n\n"

        content = ""
        if card.first_message:
            content += f"### First Message\n\n{card.first_message}\n\n"
        if card.type == "character" and card.example_dialog:
            content += f"### Example Dialog\n\n{card.example_dialog}\n\n"
        if card.type == "scenario" and card.example_scene:
            content += f"### Example Scene\n\n{card.example_scene}\n\n"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(frontmatter + content.strip())

    def _create_png_file_for_card(self, card: CharacterCardData, base_path: str):
        safe_folder_path = os.path.join(base_path, *card.folder.replace("\\", "/").split("/"))
        os.makedirs(safe_folder_path, exist_ok=True)
        safe_filename = "".join(c for c in card.name if c.isalnum() or c in (' ', '_', '-')).rstrip()
        filepath = os.path.join(safe_folder_path, f"{safe_filename}.png")

        image_bytes = card.image_data
        if not image_bytes:
            # Create a placeholder image if none exists
            img = Image.new('RGB', (512, 512), color = (73, 109, 137))
            with tempfile.NamedTemporaryFile(suffix=".png") as temp_img:
                img.save(temp_img, format='PNG')
                temp_img.seek(0)
                image_bytes = temp_img.read()

        # Prepare metadata for the standard 'chara' format
        metadata = {
            "spec": "chara_card_v2",
            "data": {
                "name": card.name,
                "description": card.description or "",
                "first_mes": card.first_message or "",
                "mes_example": card.example_dialog if card.type == 'character' else card.example_scene or "",
                "scenario": card.example_scene or "",
            }
        }

        try:
            image_with_metadata = write_metadata_to_png(image_bytes, metadata)
            with open(filepath, "wb") as f:
                f.write(image_with_metadata)
        except Exception as e:
            print(f"Could not write metadata to PNG for card '{card.name}': {e}")

    def backup_chats_to_archive(self) -> Tuple[bool, str]:
        """Backs up all chat sessions to a compressed archive of Markdown files."""
        all_chats = self.chat_service.get_all_chat_sessions()
        if not all_chats:
            return False, "No chat sessions found to back up."

        with tempfile.TemporaryDirectory() as temp_dir:
            for chat in all_chats:
                self._create_markdown_file_for_chat(chat, temp_dir)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_filename = f"promptbox_chats_markdown_backup_{timestamp}.tar.gz"
            archive_filepath = settings.backup_dir / archive_filename
            archive_name_in_tar = f"promptbox_chats_backup_{timestamp}"

            try:
                result_path = create_tar_gz_archive(temp_dir, archive_filepath, arcname=archive_name_in_tar)
                if result_path:
                    return True, f"Successfully created chat session archive: {archive_filepath.name}"
                else:
                    return False, "Failed to create the archive file."
            except Exception as e:
                return False, f"Failed to create chat session archive: {e}"

    def _create_markdown_file_for_chat(self, chat: ChatSessionData, base_path: str):
        """Creates a Markdown file for a single chat session."""
        safe_filename = "".join(c for c in chat.session_name if c.isalnum() or c in (' ', '_', '-')).rstrip()
        filepath = os.path.join(base_path, f"{safe_filename}_{chat.id}.md")

        # Basic frontmatter
        frontmatter_parts = [
            f'session_name: "{chat.session_name}"',
            f'id: {chat.id}',
            f'created_at: "{chat.created_at.isoformat() if chat.created_at else ""}"',
            f'updated_at: "{chat.updated_at.isoformat() if chat.updated_at else ""}"',
            f'llm_provider: "{chat.llm_provider or "N/A"}"',
            f'llm_model_name: "{chat.llm_model_name or "N/A"}"',
        ]
        frontmatter = "---\n" + "\n".join(frontmatter_parts) + "\n---\n\n"

        # Chat content
        content = f"# Chat Session: {chat.session_name}\n\n"
        sorted_messages = sorted(chat.messages, key=lambda m: m.message_order)
        for msg in sorted_messages:
            role = msg.role.capitalize()
            timestamp = msg.timestamp.strftime('%Y-%m-%d %H:%M:%S') if msg.timestamp else "No timestamp"
            content += f"**[{role}]** - {timestamp}\n\n"
            content += f"{msg.content}\n\n---\n\n"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(frontmatter + content.strip())






































































































































































































































































































































