"""
Storage provider exception classes.

This module defines exception classes for handling errors that occur
during interactions with cloud storage providers.
"""

from sourcerer.domain.storage_provider.exceptions import BaseStorageProviderException


class CredentialsNotFoundException(BaseStorageProviderException):
    """
    Exception raised when credentials are not found for a cloud storage provider.

    This exception is a specific case of BaseStorageProviderException
    and should be used to indicate that the required credentials for
    accessing a cloud storage service are missing or not configured.
    """


class ListStoragesException(BaseStorageProviderException):
    """
    Exception raised for errors that occur during the listing of cloud storage services.

    This exception is a specific case of BaseStorageProviderException
    and is used to indicate issues encountered when attempting to retrieve
    a list of available storage services from a cloud provider.
    """


class StoragePermissionException(BaseStorageProviderException):
    """
    Exception raised for permission-related errors in cloud storage operations.

    This exception is triggered when there is an issue with permissions
    while accessing or modifying resources in a cloud storage service.
    """


class ListStorageItemsException(BaseStorageProviderException):
    """
    Exception raised when an error occurs while listing items in cloud storage.

    This exception is a specific case of BaseStorageProviderException
    and is used to indicate issues encountered during the retrieval of
    storage items from a cloud storage provider.
    """


class ReadStorageItemsException(BaseStorageProviderException):
    """
    Exception raised for errors encountered while reading items from cloud storage.

    This exception is a specific case of BaseStorageProviderException
    and should be used to indicate issues that occur during the retrieval
    of data from cloud storage services.
    """


class DeleteStorageItemsException(BaseStorageProviderException):
    """
    Exception raised for errors that occur during the deletion of storage items.

    This exception is a specific type of BaseStorageProviderException
    and is used to indicate issues encountered when attempting to delete
    items from a cloud storage service.
    """


class UploadStorageItemsException(BaseStorageProviderException):
    """
    Exception raised for errors that occur during the upload of items
    to cloud storage.

    This exception is a specific case of BaseStorageProviderException
    and is used to signal issues encountered while uploading data to
    cloud storage services.
    """
