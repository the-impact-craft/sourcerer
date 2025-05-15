"""
File system exception classes.

This module defines exception classes for handling errors that occur
during interactions with the local file system.
"""

from sourcerer.domain.file_system.exceptions import BaseFileSystemError


class FileSystemGrepError(BaseFileSystemError):
    """
    Custom exception for errors occurring during a file system search operation.

    This exception is used to indicate and encapsulate errors specific
    to the process of searching and grepping through file system contents.
    It provides additional context about the nature of the error.
    """


class ReadFileError(BaseFileSystemError):
    """
    Custom exception for errors occurring during a file system read operation.

    This exception is used to indicate and encapsulate errors specific
    to the process of reading file contents.
    It provides additional context about the nature of the error.
    """


class CreateFileError(BaseFileSystemError):
    """
    Custom exception for errors occurring during a file system create file operation.

    This exception is used to indicate and encapsulate errors specific
    to the process of creating a new file.
    It provides additional context about the nature of the error.
    """


class CreateDirError(BaseFileSystemError):
    """
    Custom exception for errors occurring during a file system create directory operation.

    This exception is used to indicate and encapsulate errors specific
    to the process of creating a new directory.
    It provides additional context about the nature of the error.
    """


class MoveFileError(BaseFileSystemError):
    """
    Exception raised for errors during file move operation.

    This class is a specific type of exception that handles issues encountered
    when attempting to move files in a file system. It inherits from
    `BaseFileSystemException` to maintain consistency with other file system
    related exceptions.
    """


class ListDirError(BaseFileSystemError):
    """
    Custom exception for errors occurring during a file system list directory operation.

    This exception is used to indicate and encapsulate errors specific
    to the process of listing directory contents.
    It provides additional context about the nature of the error.
    """


class DeleteFileError(BaseFileSystemError):
    """
    Custom exception for errors occurring during a file system delete file operation.

    This exception is used to indicate and encapsulate errors specific
    to the process of deleting a file.
    It provides additional context about the nature of the error.
    """


class DeleteDirError(BaseFileSystemError):
    """
    Custom exception for errors occurring during a file system delete directory operation.

    This exception is used to indicate and encapsulate errors specific
    to the process of deleting a directory.
    It provides additional context about the nature of the error.
    """
