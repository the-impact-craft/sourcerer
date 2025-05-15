"""
Registry for storage provider service implementations.

This module provides a registry system for managing different types of
storage provider services.
"""

import functools

from sourcerer.domain.storage_provider.services import BaseStorageProviderService
from sourcerer.infrastructure.utils import Singleton


class StorageProviderRegistry(metaclass=Singleton):
    """
    Registry for storage provider service implementations.

    This singleton class maintains a registry of storage provider service
    implementations organized by provider identifier.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the registry with an empty dictionary."""
        super().__init__(*args, **kwargs)
        self._items_: dict[str, type] = {}

    def register(self, storage_provider: str, cls: type[BaseStorageProviderService]):
        """
        Register a storage provider service implementation.

        Args:
            storage_provider (str): The provider identifier
            cls (Type[BaseStorageProviderService]): The service class to register
        """
        self._items_[storage_provider] = cls

    def get(self):
        """
        Get all registered storage provider services.

        Returns:
            dict: Dictionary of all registered storage provider services
        """
        return self._items_

    def get_by_provider(self, provider):
        """
        Get a storage provider service by provider identifier.

        Args:
            provider (str): The provider identifier

        Returns:
            Type[BaseStorageProviderService]: The storage provider service class
        """
        return self._items_.get(provider)


def storage_provider(provider: str):
    """
    Decorator for registering storage provider service implementations.

    Args:
        provider (str): The provider identifier

    Returns:
        callable: Decorator function
    """

    def wrapper(cls):
        storage_provider_registry.register(provider, cls)

        @functools.wraps(cls)
        def wrapped(*args, **kwargs):
            return cls(*args, **kwargs)

        return wrapped

    return wrapper


# Singleton registry instance
storage_provider_registry = StorageProviderRegistry()
