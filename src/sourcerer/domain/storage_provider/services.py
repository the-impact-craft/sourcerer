"""
Base storage provider service interface.

This module defines the abstract base class for storage provider services,
providing a common interface for cloud storage operations.
"""
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path

from sourcerer.domain.storage_provider.entities import (
    Storage,
    StorageContent,
    StoragePermissions,
)


class BaseStorageProviderService(ABC):
    """
    Abstract base class defining the interface for storage provider services.

    This class defines the contract that all storage provider implementations
    must follow to provide consistent access to different cloud storage systems.
    It specifies methods for listing, reading, creating, and deleting storage
    items across various cloud providers.
    """

    @abstractmethod
    def list_storages(self) -> list[Storage]:
        """
        Return a list of available storages.

        Returns:
            List[Storage]: A list of Storage objects representing available storage containers
        """

    @abstractmethod
    def get_storage_permissions(self, storage: str) -> list[StoragePermissions]:
        """
        Return the permissions for the specified storage.

        Args:
            storage (str): The storage identifier

        Returns:
            List[StoragePermissions]: A list of permission objects for the storage
        """

    @abstractmethod
    def list_storage_items(
        self, storage: str, path: str, prefix: str
    ) -> StorageContent:
        """
        List items in the specified storage path with the given prefix.

        Args:
            storage (str): The storage identifier
            path (str): The path within the storage to list
            prefix (str): Filter items by this prefix

        Returns:
            StorageContent: Object containing files and folders at the specified location
        """

    @abstractmethod
    def read_storage_item(self, storage: str, key: str) -> str:
        """
        Read and return the content of the specified storage item.

        Args:
            storage (str): The storage identifier
            key (str): The key/path of the item to read

        Returns:
            bytes: The content of the storage item
        """

    @abstractmethod
    def delete_storage_item(self, storage: str, key: str) -> None:
        """
        Delete the specified storage item.

        Args:
            storage (str): The storage identifier
            key (str): The key/path of the item to delete
        """

    @abstractmethod
    def upload_storage_item(
        self,
        storage: str,
        storage_path: str,
        source_path: Path,
        dest_path: str | None = None,
        cancel_event: threading.Event | None = None,
        progress_callback: Callable | None = None,
    ) -> None:
        """
        upload a file to the specified storage path.

        Args:
            storage (str): The storage identifier
            storage_path (str): The path within the storage to upload
            source_path (Path): Local file path to upload
            dest_path (str, optional): Destination path in storage. Defaults to None.
            cancel_event (threading.Event, optional): Event to signal upload cancellation. Defaults to None.
            progress_callback (callable, optional): Callback function for progress updates. Defaults to None.
        """

    @abstractmethod
    def download_storage_item(
        self,
        storage: str,
        key: str,
        progress_callback: Callable | None = None,
        cancel_event: threading.Event | None = None,
    ) -> str:
        """
        Download a file from storage to local filesystem.

        Args:
            storage (str): The storage identifier
            key (str): The key/path of the item to download
            progress_callback (callable, optional): Callback function for progress updates. Defaults to None.
            cancel_event (threading.Event, optional): Event to signal download cancellation. Defaults to None.
        Returns:
            str: Path to the downloaded file
        """

    @abstractmethod
    def get_file_size(self, storage: str, key: str) -> int:
        """
        Get metadata for a storage item without downloading content.

        Args:
            storage (str): The storage identifier
            key (str): The key/path of the item

        Returns:
            int: Size of the storage item in bytes
        """

    @abstractmethod
    def get_download_presigned_url(self, storage: str, key: str) -> str:
        """
        Create presigned url for file download

         Args:
            storage (str): The storage identifier
            key (str): The key/path of the item

        Returns:
            str: Presigned URL for accessing the blob

        """

    def _normalize_path(self, path: str | None) -> str:
        if path:
            return path.rstrip("/") + "/"
        return ""

    def _get_parent_path(self, path: str, prefix: str) -> tuple[str, int]:
        prefix = prefix.strip("/")
        prefix_dirs = prefix.rsplit("/", 1)[0] if "/" in prefix else ""
        parent_path = (path + prefix_dirs).rstrip("/") + "/"
        prefix_folders_len = len(parent_path.lstrip("/"))
        return parent_path, prefix_folders_len
