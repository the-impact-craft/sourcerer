"""
Implementation of Azure storage provider services.

This module provides concrete implementations of the BaseStorageProviderService
interface for various cloud storage providers.
"""

import os.path
from collections.abc import Callable
from pathlib import Path
from typing import Any

import humanize
from azure.mgmt.storage import StorageManagementClient
from azure.storage.blob import BlobServiceClient
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
    AzureMissingContainerError,
    DeleteStorageItemsError,
    ListStorageItemsError,
    ListStoragesError,
    ReadStorageItemsError,
    UploadStorageItemsError,
)
from sourcerer.infrastructure.storage_provider.registry import storage_provider
from sourcerer.infrastructure.utils import generate_uuid, is_text_file


@storage_provider(StorageProvider.AzureStorage)
class AzureStorageProviderService(BaseStorageProviderService):

    def __init__(self, credentials: Any):
        """
        Initialize the service with Azure credentials.

        Args:
            credentials (Any): Azure client or credentials object
        """
        self.credentials = credentials.credentials
        self.subscription_id = credentials.subscription_id
        self.cloud_suffix = credentials.cloud_suffix

    def get_accounts_client(self) -> StorageManagementClient:
        """
        Get the Azure accounts client.

        Returns:
            Any: Azure accounts client
        """
        return StorageManagementClient(self.credentials, self.subscription_id)

    def get_containers_client(self, storage: str):
        """
        Retrieves a BlobServiceClient instance for interacting with a specific Azure Blob
        Storage account.

        Parameters:
            storage (str): The name of the Azure storage account to connect to.

        Returns:
            BlobServiceClient: An instance of the BlobServiceClient, configured with the
            account URL and credentials.
        """
        account_url = "https://{account}.{cloud_suffix}"
        return BlobServiceClient(
            account_url.format(account=storage, cloud_suffix=self.cloud_suffix),
            credential=self.credentials,
            retry_connect=0,
        )

    def list_storages(self) -> list[Storage]:
        """
        Return a list of available Azure containers.

        Returns:
            List[Storage]: List of storage objects representing Azure containers

        Raises:
            ListStoragesError: If an error occurs while listing buckets
        """
        try:
            accounts_client = self.get_accounts_client()
            return [
                Storage(StorageProvider.AzureStorage, i.name, i.creation_time)  # type: ignore
                for i in accounts_client.storage_accounts.list()
            ]
        except Exception as ex:
            raise ListStoragesError(str(ex)) from ex

    def get_storage_permissions(self, storage: str) -> list[StoragePermissions]:
        raise NotImplementedError("Not implemented")

    def list_storage_items(
        self, storage: str, path: str, prefix: str
    ) -> StorageContent:
        """
        List items in the specified Azure container path with the given prefix.

        Args:
            storage (str): The container name
            path (str): The path within the container to list
            prefix (str): Filter items by this prefix
        """
        try:
            containers_client = self.get_containers_client(storage)
            files = []

            folders = set()
            if not path:
                folders.update([i.name for i in containers_client.list_containers()])
            else:
                path_parts = path.split("/", 1)
                if len(path_parts) > 1:
                    path, prefix = path_parts[0], path_parts[1] + "/" + prefix
                blobs_client = containers_client.get_container_client(path)
                for blob in blobs_client.walk_blobs(
                    name_starts_with=prefix, delimiter="/"
                ):
                    remaining_path = blob.name[len(prefix) :]
                    if "/" in remaining_path:
                        folder_name = remaining_path.split("/")[0]
                        if folder_name not in folders:
                            folders.add(folder_name)
                        continue  # skip subfolders

                    files.append(
                        File(
                            generate_uuid(),
                            remaining_path,
                            size=humanize.naturalsize(blob.size),
                            date_modified=blob.last_modified,
                            is_text=is_text_file(blob.name),
                        )
                    )
            return StorageContent(files=files, folders=[Folder(key) for key in folders])
        except Exception as ex:
            raise ListStorageItemsError(str(ex)) from ex

    def read_storage_item(self, storage: str, key: str) -> str:
        """
        Read and return the content of the specified Azure object.

        Args:
            storage (str): The container name
            key (str): The key/path of the item to read
        """
        try:
            containers_client = self.get_containers_client(storage)
            path_parts = key.split("/", 1)
            container, blob_name = path_parts
            blobs_client = containers_client.get_container_client(container)
            content = blobs_client.download_blob(blob_name).readall()
            return content.decode("utf-8")
        except Exception as ex:
            raise ReadStorageItemsError(str(ex)) from ex

    def delete_storage_item(self, storage: str, key: str) -> None:
        """
        Delete the specified Azure object.

        Args:
            storage (str): The container name
            key (str): The key/path of the item to delete
        """
        try:
            containers_client = self.get_containers_client(storage)
            path_parts = key.split("/", 1)
            container, blob_name = path_parts
            blob_client = containers_client.get_container_client(container)
            blob_client.delete_blob(blob_name)
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
        Upload a file to the specified Azure container path.
        Args:
            storage (str): The container name
            storage_path (str): The path within the container to upload
            source_path (Path): Local file path to upload
            dest_path (str, optional): Destination path in storage. Defaults to None.
        """
        try:
            if not storage_path:
                raise AzureMissingContainerError("Container is required for Azure storage")

            containers_client = self.get_containers_client(storage)           

            storage_path_parts = storage_path.split("/", 1)

            container = storage_path_parts[0]

            storage_path = storage_path_parts[1] if len(storage_path_parts) > 1 else ""
            blob_name = os.path.join(storage_path, dest_path or source_path.name)

            blob_client = containers_client.get_container_client(container)
            with open(source_path, "rb") as file_handle:
                blob_client.upload_blob(
                    blob_name or source_path.name, file_handle, overwrite=True
                )
        except Exception as ex:
            raise UploadStorageItemsError(str(ex)) from ex

    def download_storage_item(
        self, storage: str, key: str, progress_callback: Callable | None = None
    ) -> str:
        """
        Download a file from Azure to the local filesystem.

        Args:
            storage (str): The container name
            key (str): The key/path of the item to download
            progress_callback (Callable, optional): Callback function for progress updates. Defaults to None.
        """
        try:
            download_path = Path(user_downloads_dir()) / Path(key).name

            containers_client = self.get_containers_client(storage)
            path_parts = key.split("/", 1)
            container, blob_name = path_parts
            blob_client = containers_client.get_container_client(container)
            with open(download_path, "wb") as file:
                download_stream = blob_client.download_blob(blob_name)
                file.write(download_stream.readall())
            return str(download_path)
        except Exception as ex:
            raise ReadStorageItemsError(str(ex)) from ex

    def get_file_size(self, storage: str, key: str) -> int:
        """
        Get metadata for an Azure object without downloading content.

        Args:
            storage (str): The container name
            key (str): The key/path of the item
        """
        try:
            containers_client = self.get_containers_client(storage)
            path_parts = key.split("/", 1)
            container, blob_name = path_parts
            blob_client = containers_client.get_blob_client(container, blob_name)
            props = blob_client.get_blob_properties()
            return props.size
        except Exception as ex:
            raise ReadStorageItemsError(str(ex)) from ex
