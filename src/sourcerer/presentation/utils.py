"""
Utility functions for the presentation layer.

This module provides helper functions for the presentation layer,
particularly for retrieving and initializing storage provider services.
"""
from threading import Lock

from cachetools import LRUCache
from dependency_injector.wiring import Provide

from sourcerer.domain.access_credentials.repositories import BaseCredentialsRepository
from sourcerer.domain.settings.entities import Settings
from sourcerer.domain.storage_provider.services import BaseStorageProviderService
from sourcerer.infrastructure.access_credentials.exceptions import CredentialsAuthError
from sourcerer.infrastructure.access_credentials.registry import (
    access_credential_method_registry,
)
from sourcerer.infrastructure.storage_provider.registry import storage_provider_registry
from sourcerer.presentation.di_container import DiContainer
from sourcerer.settings import MAX_CREDENTIALS_CACHE_SIZE

_provider_service_cache: LRUCache = LRUCache(maxsize=MAX_CREDENTIALS_CACHE_SIZE)
_provider_service_cache_lock = Lock()


def get_provider_service_by_access_uuid(
    uuid, credentials_service, settings
) -> BaseStorageProviderService | None:
    """
    Retrieves the provider service associated with the given access credentials UUID.

    Args:
        uuid (str): The UUID of the access credentials.
        credentials_service: Credentials service
        settings(Settings): The settings associated with the access credentials.

    Returns:
        The provider service instance corresponding to the access credentials.
    """
    access_credentials = credentials_service.get(uuid)
    return get_provider_service_by_access_credentials(access_credentials, settings)


def _provider_service_cache_lru_key(credentials, settings: Settings):
    return "-".join(
        [
            credentials.uuid,
            str(settings.upload_chunk_size),
            str(settings.download_chunk_size),
            str(settings.presigned_url_ttl_seconds),
        ]
    )


def get_provider_service_by_access_credentials(
    credentials,
    settings: Settings,
    credentials_repo: BaseCredentialsRepository = Provide[
        DiContainer.credentials_repository
    ],
) -> BaseStorageProviderService | None:
    """
    Retrieves a storage provider service instance using the given access credentials.

    Args:
        credentials: An object containing provider and credentials type information.
        settings(Settings): The settings associated with the access credentials.
        credentials_repo: BaseCredentialsRepository

    Returns:
        An instance of the storage provider service if both the credentials service
        and provider service class are found; otherwise, returns None.

    Flow:
        1. Fetch the credentials service using the provider and credentials type.
        2. If the credentials service is not found, return None.
        3. Fetch the provider service class using the provider.
        4. If the provider service class is not found, return None.
        5. Authenticate the credentials using the credentials service.
        6. Return an instance of the provider service class initialized with the
           authenticated credentials.
    """

    cache_key = _provider_service_cache_lru_key(credentials, settings)
    with _provider_service_cache_lock:
        if cache_key in _provider_service_cache:
            return _provider_service_cache[cache_key]

    credentials_service = access_credential_method_registry.get_by_provider_and_name(
        credentials.provider, credentials.credentials_type
    )

    if not credentials_service:
        return None

    provider_service_class = storage_provider_registry.get_by_provider(
        credentials.provider
    )
    if not provider_service_class:
        return None

    try:
        auth_credentials = credentials_service(credentials_repo).authenticate(
            credentials.credentials
        )
    except CredentialsAuthError:
        return None
    service = provider_service_class(
        auth_credentials,
        settings.upload_chunk_size,
        settings.download_chunk_size,
        settings.presigned_url_ttl_seconds,
    )
    with _provider_service_cache_lock:
        _provider_service_cache[cache_key] = service
    return service
