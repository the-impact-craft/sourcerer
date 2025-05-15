"""
Base access credentials service interfaces.

This module defines the abstract base classes and data structures for
access credential services, providing a common interface for different
authentication methods.
"""

from abc import abstractmethod
from dataclasses import dataclass

from sourcerer.domain.access_credentials.repositories import BaseCredentialsRepository


@dataclass
class AuthField:
    """
    Data class representing an authentication field.

    Args:
        key (str): Unique identifier for the auth field
        label (str): Display label for the auth field
        required (bool): Whether this field is required
        description (str | None): Optional description of the field
    """

    key: str
    label: str
    required: bool
    multiline: bool = False
    description: str | None = None


class BaseAccessCredentialsService:
    """
    Base class for access credentials services.

    This abstract class defines the interface for services that manage
    authentication credentials for various cloud providers and services.
    """

    def __init__(self, credentials_repo: BaseCredentialsRepository):
        """
        Initialize the service.

        Args:
            credentials_repo (BaseCredentialsRepository): Repository for storing credentials
        """
        self.credentials_repo = credentials_repo

    @abstractmethod
    def store(self, name: str, credentials: dict):
        """
        Store credentials.

        Args:
            name (str): Name identifier for the credentials
            credentials (dict): Dictionary containing credential information
        """

    @abstractmethod
    def extract(self, uuid: str):
        """
        Extract credentials by UUID.

        Args:
            uuid (str): UUID of the credentials to extract

        Returns:
            Credentials: The credentials object
        """

    @abstractmethod
    def authenticate(self, credentials: str):
        """
        Authenticate using stored credentials.

        Returns:
            Any: Authentication result, typically a session or client object
        """

    @classmethod
    @abstractmethod
    def auth_fields(cls) -> list[AuthField]:
        """
        Get list of authentication fields.

        Returns:
            List[AuthField]: List of authentication field definitions
        """

    @classmethod
    def validate_auth_fields_values(cls, auth_fields: dict) -> None:
        """
        Validate authentication fields.

        Args:
            auth_fields (dict): Dictionary containing authentication field,
                                where keys are field names and values are field values

        Raises:
            MissingAuthFieldsError: If any required authentication fields are missing
        """
