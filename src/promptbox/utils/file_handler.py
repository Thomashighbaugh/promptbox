"""
Contains utility functions for handling files, particularly markdown
with YAML frontmatter.
"""

import yaml # type: ignore
from pathlib import Path
from typing import Tuple, Dict, Any

# Define a custom exception for parsing errors
class FrontmatterError(ValueError):
    """Custom exception for errors related to frontmatter parsing."""
    pass

def parse_markdown_with_frontmatter(file_path: str | Path) -> Tuple[Dict[str, Any], str]:
    """
    Parses a markdown file to separate YAML frontmatter from the main content.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        raise
    except Exception as e:
        raise FrontmatterError(f"Could not read file at {file_path}: {e}")

    if not content.startswith('---'):
        return {}, content

    parts = content.split('---', 2)
    if len(parts) < 3:
        raise FrontmatterError(
            f"Malformed frontmatter in {file_path}. Ensure it is enclosed in '---' blocks."
        )

    frontmatter_str = parts[1]
    main_content = parts[2].strip()

    try:
        metadata = yaml.safe_load(frontmatter_str)
        if not isinstance(metadata, dict):
            raise FrontmatterError("Frontmatter did not parse as a dictionary (key-value pairs).")
        return metadata, main_content
    except yaml.YAMLError as e:
        raise FrontmatterError(f"Error parsing YAML frontmatter in {file_path}: {e}")

def save_markdown_file(filename: str, content: str, directory: Path | str | None = None) -> str:
    """
    Saves content to a markdown file in a specified directory.
    """
    import tempfile 

    if directory is None:
        save_dir = Path(tempfile.gettempdir())
    else:
        save_dir = Path(directory)

    save_dir.mkdir(parents=True, exist_ok=True)
    file_path = save_dir / filename

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return str(file_path)
    except Exception as e:
        print(f"Error saving file {file_path}: {e}")
        raise
