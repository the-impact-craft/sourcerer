"""
File system entity classes.

This module defines data classes representing file system entities and
operation results used throughout the application.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class SearchResult:
    """
    Represents the result of a search operation.

    This class encapsulates the details of a single search result, including
    the matched text, the file where the match was found, and the line number
    within the file. It is typically used to store and organize search results
    for further processing or display.

    Attributes:
        text (str): The text that matched the search pattern.
        file_name (str): The name of the file where the text was found.
        line (int): The line number within the file where the text was found.
    """

    text: str
    file_name: str
    line: int


@dataclass
class SearchResultOutput:
    """
    Represents the output of a search operation.

    This class encapsulates the results of a search operation, including
    the search pattern used, the list of search results, and the total
    number of matches found. It is typically used to organize and present
    search results to the user.

    Attributes:
        pattern (str): The search pattern that was used.
        output (list[SearchResult]): List of search result objects.
        total (int): Total number of matches found.
    """

    pattern: str
    output: list[SearchResult]
    total: int


@dataclass
class ListDirOutput:
    """
    Represents the output of a list directory operation.

    This class encapsulates the details of a list directory operation,
    including the list of files and directories within the specified
    directory. It is typically used to store and organize the directory
    listing for further processing or display.

    Attributes:
        files (list[Path]): List of file paths found in the directory.
        directories (list[Path]): List of directory paths found in the directory.
    """

    files: list[Path]
    directories: list[Path]
