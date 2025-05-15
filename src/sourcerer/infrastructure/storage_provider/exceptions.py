"""
Storage provider exception classes.

This module defines exception classes for handling errors that occur
during interactions with cloud storage providers.
"""

from sourcerer.domain.storage_provider.exceptions import BaseStorageProviderError


class CredentialsNotFoundError(BaseStorageProviderError):
    """
    Exception raised when credentials are not found for a cloud storage provider.

    This exception is a specific case of BaseStorageProviderException
    and should be used to indicate that the required credentials for
    accessing a cloud storage service are missing or not configured.
    """


class ListStoragesError(BaseStorageProviderError):
    """
    Exception raised for errors that occur during the listing of cloud storage services.

    This exception is a specific case of BaseStorageProviderException
    and is used to indicate issues encountered when attempting to retrieve
    a list of available storage services from a cloud provider.
    """


class StoragePermissionError(BaseStorageProviderError):
    """
    Exception raised for permission-related errors in cloud storage operations.

    This exception is triggered when there is an issue with permissions
    while accessing or modifying resources in a cloud storage service.
    """


class ListStorageItemsError(BaseStorageProviderError):
    """
    Exception raised when an error occurs while listing items in cloud storage.

    This exception is a specific case of BaseStorageProviderException
    and is used to indicate issues encountered during the retrieval of
    storage items from a cloud storage provider.
    """


class BlobNotFoundError(BaseStorageProviderError):
    """
    Exception raised when a blob (file) is not found in cloud storage.

    This exception is a specific case of BaseStorageProviderException
    and should be used to indicate that the requested blob could not
    be located in the specified cloud storage service.
    """


class ReadStorageItemsError(BaseStorageProviderError):
    """
    Exception raised for errors encountered while reading items from cloud storage.

    This exception is a specific case of BaseStorageProviderException
    and should be used to indicate issues that occur during the retrieval
    of data from cloud storage services.
    """


class DeleteStorageItemsError(BaseStorageProviderError):
    """
    Exception raised for errors that occur during the deletion of storage items.

    This exception is a specific type of BaseStorageProviderException
    and is used to indicate issues encountered when attempting to delete
    items from a cloud storage service.
    """


class UploadStorageItemsError(BaseStorageProviderError):
    """
    Exception raised for errors that occur during the upload of items
    to cloud storage.

    This exception is a specific case of BaseStorageProviderException
    and is used to signal issues encountered while uploading data to
    cloud storage services.
    """


class AzureMissingContainerError(BaseStorageProviderError):
    """
    Exception raised when a container is not found in Azure cloud storage.

    This exception is a specific case of BaseStorageProviderException
    and should be used to indicate that the requested container could not
    be located in the specified Azure cloud storage service.
    """
