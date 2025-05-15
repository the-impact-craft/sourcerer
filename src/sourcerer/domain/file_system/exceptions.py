"""
File system exception base class.

This module defines the base exception class for errors related to
file system operations.
"""


class BaseFileSystemError(Exception):
    """
    Base exception class for filesystem-related errors.

    This class serves as the base for all exceptions that arise
    within the filesystem module. It provides a foundation for
    more specific exceptions to inherit from, making it easier to
    handle different filesystem error scenarios in a structured way.
    """
