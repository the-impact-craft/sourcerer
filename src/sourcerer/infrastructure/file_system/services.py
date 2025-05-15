"""
File system service implementation.

This module provides a concrete implementation of the BaseFileSystemService
interface for interacting with the local file system.
"""

from pathlib import Path

from sourcerer.domain.file_system.entities import ListDirOutput
from sourcerer.domain.file_system.services import BaseFileSystemService
from sourcerer.infrastructure.file_system.exceptions import (
    ListDirError,
    ReadFileError,
)
from sourcerer.infrastructure.utils import custom_sort_key


class FileSystemService(BaseFileSystemService):
    """
    Implementation of the file system service for local file operations.

    This class provides methods for interacting with the local file system,
    implementing the BaseFileSystemService interface. It handles operations
    like reading, writing, listing, and searching files within a specified
    working directory.
    """

    ACCESS_DENIED_ERROR = "Access denied: Path outside work directory"
    FILE_NOT_FOUND_ERROR = "File does not exist"
    MOVING_FILE_ERROR = "Moving file error"

    def __init__(self, work_dir: Path | str):
        """
        Initialize a FileSystemService instance with the specified working directory.

        Args:
            work_dir (Path or str): The path to the working directory. If a string is provided,
                it will be converted to a Path object.
        """
        self.work_dir = work_dir if isinstance(work_dir, Path) else Path(work_dir)

    def read(self, path: Path) -> str:
        """
        Reads and processes the contents of a file located at the specified path.

        This method will attempt to open the file, read its content, and perform
        any necessary processing on the data. It assumes that the file is in
        a format appropriate for the specific application logic and that the
        given path is accessible.

        Args:
            path (Path): The path to the file to read.

        Returns:
            str: The processed data extracted from the file.

        Raises:
            ReadFileError: An error occurred during the file read operation.
        """

        if not isinstance(path, Path):
            raise ReadFileError("file_path must be a Path object")
        if not path.exists():
            raise ReadFileError(f"File not found: {path}")
        self.validate_path_within_work_dir(path, ReadFileError)
        try:
            return path.read_text()
        except Exception as e:
            raise ReadFileError(f"Error reading file: {e}") from e

    def list_dir(
        self,
        path: Path,
        relative_paths: bool = False,
        recursively=False,
        max_items: int | None = None,
    ) -> ListDirOutput:
        """
        List all files and directories within the specified directory.

        Args:
            path (Path): The path to the directory.
            relative_paths (bool): Whether to return relative paths or full paths.
            recursively (bool): Whether iterate recursively over the content.
            max_items (int | None): Maximum number of items to return.

        Returns:
             ListDirOutput: A data class containing the list of files and directories within the specified path.
                - files (list[Path]): Sorted list of file paths
                - directories (list[Path]): Sorted list of directory paths

        Raises:
            ListDirError: If the path is invalid, directory doesn't exist, or path is not a directory.

        """
        if not isinstance(path, Path):
            raise ListDirError("Path must be a Path object")
        if not path.exists():
            raise ListDirError(f"Directory not found: {path}")
        if not path.is_dir():
            raise ListDirError(f"Path is not a directory: {path}")
        try:
            path.relative_to(self.work_dir)
        except ValueError as e:
            raise ListDirError("Access denied: Path outside work directory") from e
        try:
            files = []
            directories = []

            entries = path.rglob("*") if recursively else path.iterdir()
            items = 0
            for entry in entries:
                if max_items and items > max_items:
                    raise ListDirError(
                        f"Too many items, max processable dir size: {max_items}"
                    )
                items += 1  # noqa SIM103
                target = files if entry.is_file() else directories
                target.append(entry.relative_to(path) if relative_paths else entry)
            return ListDirOutput(
                files=sorted(files, key=custom_sort_key),
                directories=sorted(directories, key=custom_sort_key),
            )
        except PermissionError as e:
            raise ListDirError(f"Access denied: {e}") from e
        except Exception as e:
            raise ListDirError(f"Error listing directory: {e}") from e

    def validate_path_within_work_dir(self, path: Path, exception_class: type) -> None:
        """
        Validates if a path is within the working directory.

        This method checks if the given path is contained within the working directory
        to prevent unauthorized access to files outside the designated work area.

        Args:
            path (Path): The path to validate
            exception_class (type): The exception class to raise if validation fails

        Raises:
            exception_class: If the path is outside the working directory
        """
        try:
            path.relative_to(self.work_dir)
        except ValueError as e:
            raise exception_class(self.ACCESS_DENIED_ERROR) from e
