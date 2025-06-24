"""
Contains utility functions for creating compressed archives.
"""

import tarfile
from pathlib import Path
from typing import Union

def create_tar_gz_archive(
    source_dir: Union[str, Path],
    archive_path: Union[str, Path],
    arcname: str = None
) -> str | None:
    """
    Creates a compressed tar.gz archive from a source directory.

    Args:
        source_dir (Union[str, Path]): The path to the directory to be archived.
        archive_path (Union[str, Path]): The full path for the output .tar.gz file.
                                         The parent directory will be created if it doesn't exist.
        arcname (str, optional): The name for the root directory inside the archive.
                                 If None, it defaults to the basename of the source_dir.

    Returns:
        str: The path to the created archive on success, otherwise None.
    """
    source_dir = Path(source_dir)
    archive_path = Path(archive_path)

    # Ensure the source directory exists
    if not source_dir.is_dir():
        print(f"Error: Source directory not found at '{source_dir}'")
        return None

    # Ensure the destination directory exists
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    # Determine the name of the root folder within the archive
    archive_root_name = arcname if arcname is not None else source_dir.name

    try:
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(source_dir, arcname=archive_root_name)

        return str(archive_path)
    except Exception as e:
        print(f"Failed to create archive: {e}")
        return None
