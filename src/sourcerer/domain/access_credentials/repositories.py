"""
Base credentials repository interface.

This module defines the abstract base class for credentials repositories,
providing a common interface for different storage implementations.
"""

from abc import ABCMeta, abstractmethod

from sourcerer.domain.access_credentials.entities import Credentials


class BaseCredentialsRepository(metaclass=ABCMeta):
    """Base abstract class for credentials repository implementations.

    Defines the interface for storing and retrieving credentials.
    """

    @abstractmethod
    def create(self, credentials: Credentials):
        """Create new credentials entry in the repository.

        Args:
            credentials (Credentials): The credentials object to store

        Raises:
            NotImplementedError: Method must be implemented by concrete classes
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, uuid):
        """Retrieve credentials by UUID.

        Args:
            uuid: Unique identifier for the credentials

        Returns:
            Credentials: The credentials object if found, None otherwise

        Raises:
            NotImplementedError: Method must be implemented by concrete classes
        """
        raise NotImplementedError

    @abstractmethod
    def list(self, active_only: bool | None = None):
        """List all credentials in the repository.

        Args:
            active_only (bool|None, optional): If True, return only active credentials.
                If False, return all credentials. Defaults to None.

        Returns:
            List[Credentials]: List of credentials objects

        Raises:
            NotImplementedError: Method must be implemented by concrete classes
        """
        raise NotImplementedError

    @abstractmethod
    def activate(self, uuid):
        """Activate credentials by UUID.

        Args:
            uuid: Unique identifier for the credentials to activate

        Raises:
            NotImplementedError: Method must be implemented by concrete classes
        """
        raise NotImplementedError

    @abstractmethod
    def deactivate(self, uuid):
        """Deactivate credentials by UUID.

        Args:
            uuid: Unique identifier for the credentials to deactivate

        Raises:
            NotImplementedError: Method must be implemented by concrete classes
        """
        raise NotImplementedError
