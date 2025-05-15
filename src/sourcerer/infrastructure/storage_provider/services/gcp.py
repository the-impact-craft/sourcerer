"""
Implementation of GCP storage provider services.

This module provides concrete implementations of the BaseStorageProviderService
interface for various cloud storage providers.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import humanize
from platformdirs import user_downloads_dir

from sourcerer.domain.shared.entities import StorageProvider
from sourcerer.domain.storage_provider.entities import (
    File,
    Folder,
    Storage,
    StorageContent,
    StoragePermissions,
)
from sourcerer.domain.storage_provider.services import BaseStorageProviderService
from sourcerer.infrastructure.storage_provider.exceptions import (
    BlobNotFoundError,
    DeleteStorageItemsError,
    ListStorageItemsError,
    ListStoragesError,
    ReadStorageItemsError,
    StoragePermissionError,
    UploadStorageItemsError,
)
from sourcerer.infrastructure.storage_provider.registry import storage_provider
from sourcerer.infrastructure.utils import generate_uuid, is_text_file
from sourcerer.settings import PAGE_SIZE, PATH_DELIMITER


@storage_provider(StorageProvider.GoogleCloudStorage)
class GCPStorageProviderService(BaseStorageProviderService):
    """
    Google Cloud Platform storage provider service implementation.

    This class provides methods for interacting with GCP Cloud Storage,
    implementing the BaseStorageProviderService interface.
    """

    def __init__(self, credentials: Any):
        """
        Initialize the service with GCP credentials.

        Args:
            credentials (Any): GCP client or credentials object
        """
        self.client = credentials

    def list_storages(self) -> list[Storage]:
        """
        Return a list of available GCP buckets.

        Returns:
            List[Storage]: List of storage objects representing GCP buckets

        Raises:
            ListStoragesError: If an error occurs while listing buckets
        """
        try:
            return [
                Storage(StorageProvider.GoogleCloudStorage, i.name, i.time_created)
                for i in self.client.list_buckets()
            ]
        except Exception as ex:
            raise ListStoragesError(str(ex)) from ex

    def get_storage_permissions(self, storage: str) -> list[StoragePermissions]:
        """
        Return the permissions for the specified GCP bucket.

        Args:
            storage (str): The bucket name

        Returns:
            List[StoragePermissions]: List of permission objects for the bucket

        Raises:
            StoragePermissionError: If an error occurs while getting permissions
        """
        try:
            bucket = self.client.get_bucket(storage)
            policy = bucket.get_iam_policy()

            result = {}
            for role, members in policy.items():
                for member in members:
                    member = member.split(":")[-1]
                    if member not in result:
                        result[member] = set()
                    result[member].add(role)
            return [
                StoragePermissions(member, roles) for member, roles in result.items()
            ]
        except Exception as ex:
            raise StoragePermissionError(str(ex)) from ex

    def list_storage_items(
        self, storage: str, path: str = "", prefix: str = ""
    ) -> StorageContent:
        """
        List items in the specified GCP bucket path with the given prefix.

        Args:
            storage (str): The bucket name
            path (str, optional): The path within the bucket. Defaults to ''.
            prefix (str, optional): Filter items by this prefix. Defaults to ''.

        Returns:
            StorageContent: Object containing files and folders at the specified location

        Raises:
            ListStorageItemsError: If an error occurs while listing items
        """
        try:

            files = []
            folders = []
            if path and not path.endswith("/"):
                path += "/"

            bucket = self.client.bucket(storage)

            blobs = bucket.list_blobs(
                prefix=path + prefix, delimiter=PATH_DELIMITER, max_results=PAGE_SIZE
            )

            for blob in blobs:
                files.append(
                    File(
                        generate_uuid(),
                        blob.name[len(path) :],
                        size=humanize.naturalsize(blob.size),
                        date_modified=blob.updated.date(),
                        is_text=is_text_file(blob.name),
                    )
                )

            for folder in blobs.prefixes:
                relative_path = folder[len(path) :]
                folders.append(Folder(relative_path))

            return StorageContent(files=files, folders=folders)

        except Exception as ex:
            raise ListStorageItemsError(
                f"Failed to list items in {storage}: {str(ex)}"
            ) from ex

    def read_storage_item(self, storage: str, key: str) -> str:
        """
        Read and return the content of the specified GCP object.

        Args:
            storage (str): The bucket name
            key (str): The key/path of the item to read

        Returns:
            str: The UTF-8 decoded content of the GCP object

        Raises:
            ReadStorageItemsError: If an error occurs while reading the item
        """
        try:
            bucket = self.client.bucket(storage)
            blob = bucket.get_blob(key)
            if not blob:
                raise BlobNotFoundError(key)
            content = blob.download_as_bytes()
            return content.decode("utf-8")
        except Exception as ex:
            raise ReadStorageItemsError(str(ex)) from ex

    def delete_storage_item(self, storage: str, key: str) -> None:
        """
        Delete the specified GCP object.

        Args:
            storage (str): The bucket name
            key (str): The key/path of the item to delete

        Raises:
            DeleteStorageItemsError: If an error occurs while deleting the item
        """
        try:
            bucket = self.client.bucket(storage)
            blob = bucket.get_blob(key)
            if not blob:
                raise BlobNotFoundError(key)
            blob.delete()
        except Exception as ex:
            raise DeleteStorageItemsError(str(ex)) from ex

    def upload_storage_item(
        self,
        storage: str,
        storage_path: str,
        source_path: Path,
        dest_path: str | None = None,
    ) -> None:
        """
        Upload a file to the specified GCP bucket path.

        Args:
            storage (str): The bucket name
            storage_path (str): The path within the bucket
            source_path (Path): Local file path to upload
            dest_path (str, optional): Destination path in GCP. Defaults to None.

        Raises:
            UploadStorageItemsError: If an error occurs while uploading the item
        """
        try:
            bucket = self.client.bucket(storage)
            storage_path = str(
                Path(storage_path or "") / (dest_path or source_path.name)
            )
            bucket.blob(storage_path).upload_from_filename(source_path)
        except Exception as ex:
            raise UploadStorageItemsError(str(ex)) from ex

    def download_storage_item(
        self, storage: str, key: str, progress_callback: Callable | None = None
    ) -> str:
        """
        Download a file from GCP to the local filesystem.

        Args:
            storage (str): The bucket name
            key (str): The key/path of the item to download
            progress_callback (Callable, optional): Callback function for progress updates. Defaults to None.

        Returns:
            str: Path to the downloaded file

        Raises:
            ReadStorageItemsError: If an error occurs while downloading the item
        """
        try:
            bucket = self.client.bucket(storage)
            blob = bucket.get_blob(key)
            if not blob:
                raise BlobNotFoundError(key)
            download_path = Path(user_downloads_dir()) / Path(key).name
            blob.download_to_filename(str(download_path))
            return str(download_path)
        except Exception as ex:
            raise ReadStorageItemsError(str(ex)) from ex

    def get_file_size(self, storage: str, key: str) -> int:
        """
        Get metadata for a GCP object without downloading content.

        Args:
            storage (str): The bucket name
            key (str): The key/path of the item

        Returns:
            int: Size of the storage item in bytes

        Raises:
            ReadStorageItemsError: If an error occurs while getting metadata
        """
        try:
            bucket = self.client.bucket(storage)
            blob = bucket.get_blob(key)
            if not blob:
                raise BlobNotFoundError(key)
            return blob.size
        except Exception as ex:
            raise ReadStorageItemsError(str(ex)) from ex
