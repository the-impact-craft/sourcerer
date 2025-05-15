"""
Storage provider exception base class.

This module defines the base exception class for errors related to
cloud storage provider operations.
"""


class BaseStorageProviderError(Exception):
    """
    Base exception class for cloud storage provider-related errors.

    This class serves as the base for all exceptions that may occur
    when interacting with cloud storage services. Specific exception
    types should inherit from this class to maintain a consistent
    exception hierarchy.
    """
