"""
Base file system service interface.

This module defines the abstract base class for file system services,
providing a common interface for file system operations.
"""

import abc
from pathlib import Path

from sourcerer.domain.file_system.entities import ListDirOutput


class BaseFileSystemService(metaclass=abc.ABCMeta):
    """
    Abstract base class for file system services.

    This class defines the interface for file system operations such as
    listing, reading, creating, and deleting files and directories.
    Concrete implementations should provide the actual functionality.
    """

    @abc.abstractmethod
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
        raise NotImplementedError

    @abc.abstractmethod
    def list_dir(
        self, path: Path, relative_paths: bool = False, recursively=False
    ) -> ListDirOutput:
        """
        List all files and directories within the specified directory.

        Args:
            path (Path): The path to the directory.
            relative_paths (bool): Whether to return relative paths or full paths.
            recursively (bool): Whether iterate recursively over the content

        Returns:
            ListDirOutput: A data class containing the list of files and directories within the specified path.
                - files (list[Path]): Sorted list of file paths
                - directories (list[Path]): Sorted list of directory paths

        Raises:
            ListDirError: If the path is invalid, directory doesn't exist, or path is not a directory.
        """
        raise NotImplementedError
