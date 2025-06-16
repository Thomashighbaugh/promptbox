"""
Contains utility functions for handling files, particularly markdown
with YAML frontmatter.
"""

import os
import yaml
from pathlib import Path
from typing import Tuple, Dict, Any

# Define a custom exception for parsing errors
class FrontmatterError(ValueError):
    """Custom exception for errors related to frontmatter parsing."""
    pass

def parse_markdown_with_frontmatter(file_path: str | Path) -> Tuple[Dict[str, Any], str]:
    """
    Parses a markdown file to separate YAML frontmatter from the main content.

    Args:
        file_path: The path to the markdown file.

    Returns:
        A tuple containing:
        - A dictionary of the parsed frontmatter metadata.
        - A string of the main content.
    
    Raises:
        FileNotFoundError: If the file does not exist.
        FrontmatterError: If the frontmatter is missing or malformed.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        raise
    except Exception as e:
        raise FrontmatterError(f"Could not read file at {file_path}: {e}")

    # Regex is an option, but simple splitting is often safer and sufficient
    if not content.startswith('---'):
        # If no frontmatter, return empty metadata and full content
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
            # Handle cases where YAML is valid but not a dictionary
            raise FrontmatterError("Frontmatter did not parse as a dictionary (key-value pairs).")
        return metadata, main_content
    except yaml.YAMLError as e:
        raise FrontmatterError(f"Error parsing YAML frontmatter in {file_path}: {e}")

def save_markdown_file(filename: str, content: str, directory: Path | str | None = None) -> str:
    """
    Saves content to a markdown file in a specified directory.
    
    Args:
        filename: The name of the file to save (e.g., 'my_chat_01.md').
        content: The string content to write to the file.
        directory: The directory to save the file in. Defaults to a temporary directory.

    Returns:
        The full path to the saved file.
    """
    import tempfile # Local import to keep global namespace clean

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

# Example usage for standalone testing
if __name__ == '__main__':
    # Create a dummy markdown file for testing
    test_dir = Path("test_file_handler")
    test_dir.mkdir(exist_ok=True)
    test_file_path = test_dir / "test_prompt.md"
    
    test_content = """---
name: "My Test Prompt"
tags: ["test", "example"]
version: 1
---

### System Instruction

You are a helpful assistant.
"""
    with open(test_file_path, 'w', encoding='utf-8') as f:
        f.write(test_content)
        
    print(f"--- Testing with valid file: {test_file_path} ---")
    try:
        metadata, content = parse_markdown_with_frontmatter(test_file_path)
        print("Parsing successful!")
        print("Metadata:", metadata)
        print("Content:", content.strip())
        assert metadata['name'] == "My Test Prompt"
        assert "helpful assistant" in content
    except (FrontmatterError, FileNotFoundError) as e:
        print(f"Test failed: {e}")

    # Test file with no frontmatter
    no_fm_path = test_dir / "no_frontmatter.md"
    with open(no_fm_path, 'w', encoding='utf-8') as f:
        f.write("Just some plain text.")
    
    print(f"\n--- Testing with file lacking frontmatter: {no_fm_path} ---")
    metadata, content = parse_markdown_with_frontmatter(no_fm_path)
    print("Metadata:", metadata)
    print("Content:", content)
    assert metadata == {}
    assert content == "Just some plain text."

    # Test malformed file
    malformed_path = test_dir / "malformed.md"
    with open(malformed_path, 'w', encoding='utf-8') as f:
        f.write("---\nthis is not valid yaml: { a: b\n---\nContent")

    print(f"\n--- Testing with malformed frontmatter: {malformed_path} ---")
    try:
        parse_markdown_with_frontmatter(malformed_path)
    except FrontmatterError as e:
        print(f"Caught expected error: {e}")

    # Clean up
    import shutil
    shutil.rmtree(test_dir)
    print("\nCleanup complete.")
