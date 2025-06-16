import os
import shutil
import tarfile
import tempfile
from datetime import datetime
from promptbox.core.config import settings
from promptbox.services.prompt_service import PromptService
from promptbox.models.prompt import PromptData

class BackupService:
    def __init__(self, prompt_service: PromptService):
        self.prompt_service = prompt_service

    def backup_database_file(self) -> str | None:
        db_path = settings.database_path
        if not db_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"promptbox_db_backup_{timestamp}.db"
        backup_filepath = settings.backup_dir / backup_filename

        try:
            shutil.copy(db_path, backup_filepath)
            return str(backup_filepath)
        except Exception:
            return None

    def backup_prompts_to_archive(self) -> str | None:
        all_prompts = self.prompt_service.get_all_prompts()
        if not all_prompts:
            return None

        with tempfile.TemporaryDirectory() as temp_dir:
            for prompt in all_prompts:
                self._create_markdown_file_for_prompt(prompt, temp_dir)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_filename = f"promptbox_markdown_backup_{timestamp}.tar.gz"
            archive_filepath = settings.backup_dir / archive_filename

            try:
                with tarfile.open(archive_filepath, "w:gz") as tar:
                    tar.add(temp_dir, arcname=f"promptbox_backup_{timestamp}")
                return str(archive_filepath)
            except Exception:
                return None

    def _create_markdown_file_for_prompt(self, prompt: PromptData, base_path: str):
        safe_folder_path = os.path.join(base_path, *prompt.folder.replace("\\", "/").split("/"))
        os.makedirs(safe_folder_path, exist_ok=True)
        
        safe_filename = "".join(c for c in prompt.name if c.isalnum() or c in (' ', '_', '-')).rstrip()
        filepath = os.path.join(safe_folder_path, f"{safe_filename}.md")

        frontmatter = f"---\nname: \"{prompt.name}\"\ndescription: \"{prompt.description or ''}\"\ntags: [{', '.join(f'\"{t}\"' for t in prompt.tags)}]\nfolder: \"{prompt.folder}\"\ncreated_at: \"{prompt.created_at.isoformat()}\"\nupdated_at: \"{prompt.updated_at.isoformat()}\"\n---\n\n"
        content = ""
        if prompt.system_instruction:
            content += f"### System Instruction\n\n{prompt.system_instruction}\n\n"
        if prompt.user_instruction:
            content += f"### User Instruction\n\n{prompt.user_instruction}\n\n"
        if prompt.assistant_instruction:
            content += f"### Assistant Instruction\n\n{prompt.assistant_instruction}\n\n"
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(frontmatter + content.strip())
