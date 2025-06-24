import os
import shutil
import tempfile
from datetime import datetime
from typing import Tuple

from promptbox.core.config import settings
from promptbox.services.prompt_service import PromptService
from promptbox.services.character_service import CharacterService
# ChatService import is not directly needed here unless we add a specific backup for raw chat session tables
from promptbox.models.data_models import PromptData, CharacterCardData
from promptbox.utils.archiver import create_tar_gz_archive

class BackupService:
    def __init__(self, prompt_service: PromptService, character_service: CharacterService):
        self.prompt_service = prompt_service
        self.character_service = character_service
        # If you wanted to add a "backup all chat sessions to individual markdown files" feature,
        # you would inject ChatService here.

    def backup_database_file(self) -> Tuple[bool, str]:
        db_path = settings.database_path
        if not db_path.exists():
            return False, "Database file not found."

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"promptbox_db_backup_{timestamp}.db"
        backup_filepath = settings.backup_dir / backup_filename

        try:
            shutil.copy(db_path, backup_filepath)
            return True, f"Successfully created database backup: {backup_filepath.name}"
        except Exception as e:
            return False, f"Failed to create database backup: {e}"

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

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_filename = f"promptbox_cards_markdown_backup_{timestamp}.tar.gz"
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

        # Tags removed from frontmatter
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

        frontmatter = f"---\nname: \"{card.name}\"\ntype: \"{card.type}\"\ndescription: \"{card.description or ''}\"\nfolder: \"{card.folder}\"\ncreated_at: \"{card.created_at.isoformat() if card.created_at else ''}\"\nupdated_at: \"{card.updated_at.isoformat() if card.updated_at else ''}\"\n---\n\n"
        content = f"### Instructions\n\n{card.instructions}\n\n"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(frontmatter + content.strip())
