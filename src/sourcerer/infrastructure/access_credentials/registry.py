"""
Registry for access credential service implementations.

This module provides a registry system for managing different types of
access credential services for various cloud providers.
"""

import functools
from dataclasses import dataclass

from sourcerer.domain.access_credentials.services import BaseAccessCredentialsService
from sourcerer.infrastructure.utils import Singleton


@dataclass
class AccessCredentialsMethod:
    """
    Data class representing an access credentials method.

    Attributes:
        provider (str): The cloud provider identifier
        name (str): The name of the credentials method
    """

    provider: str
    name: str


class AccessCredentialsRegistry(metaclass=Singleton):
    """
    Registry for access credential service implementations.

    This singleton class maintains a registry of credential service implementations
    organized by provider and credential method name.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the registry with an empty dictionary."""
        super().__init__(*args, **kwargs)
        self._items_: dict[str, dict[str, type]] = {}  # type: ignore

    def register(
        self,
        access_credentials_method: AccessCredentialsMethod,
        cls: type[BaseAccessCredentialsService],
    ):
        """
        Register a credential service implementation.

        Args:
            access_credentials_method (AccessCredentialsMethod): The method descriptor
            cls (type[BaseAccessCredentialsService]): The service class to register
        """
        if access_credentials_method.provider not in self._items_:
            self._items_[access_credentials_method.provider] = {}
        self._items_[access_credentials_method.provider].update(
            {access_credentials_method.name: cls}
        )

    def get(self):
        """
        Get all registered credential services.

        Returns:
            dict: Dictionary of all registered credential services
        """
        return self._items_

    def get_by_provider(self, provider):
        """
        Get credential services for a specific provider.

        Args:
            provider (str): The provider identifier

        Returns:
            dict: Dictionary of credential services for the provider
        """
        return self._items_.get(provider)

    def get_by_provider_and_name(self, provider: str, name: str):
        """
        Get a specific credential service by provider and method name.

        Args:
            provider (str): The provider identifier
            name (str): The method name

        Returns:
            Type[BaseAccessCredentialsService]: The credential service class
        """
        return self._items_.get(provider, {}).get(name)


def access_credentials_method(access_credentials_method: AccessCredentialsMethod):
    """
    Decorator for registering credential service implementations.

    Args:
        access_credentials_method (AccessCredentialsMethod): The method descriptor

    Returns:
        callable: Decorator function
    """

    def wrapper(cls):
        access_credential_method_registry.register(access_credentials_method, cls)

        @functools.wraps(cls)
        def wrapped(*args, **kwargs):
            return cls(*args, **kwargs)

        return wrapped

    return wrapper


# Singleton registry instance
access_credential_method_registry = AccessCredentialsRegistry()
