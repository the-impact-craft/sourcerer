"""
Access credentials exception base class.

This module defines the base exception class for errors related to
access credentials operations.
"""


class BaseAccessCredentialsError(Exception):
    """
    Base exception class for access credentials-related errors.

    This class serves as the base for all exceptions that arise
    within the access credentials module. It provides a foundation for
    more specific exceptions to inherit from, making it easier to
    handle different credential error scenarios in a structured way.
    """
