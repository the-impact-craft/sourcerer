"""
Implementation of Azure storage provider services.

This module provides concrete implementations of the BaseStorageProviderService
interface for various cloud storage providers.
"""

import os.path
import shutil
import tempfile
import threading
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from azure.mgmt.storage import StorageManagementClient
from azure.storage.blob import BlobBlock, BlobServiceClient
from cachetools import LRUCache
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
from sourcerer.settings import DOWNLOAD_BLOCK_SIZE, MULTIPART_UPLOAD_BLOCK_SIZE


@storage_provider(StorageProvider.AzureStorage)
class AzureStorageProviderService(BaseStorageProviderService):
    MAX_CACHE_SIZE = 10

    def __init__(self, credentials: Any):
        """
        Initialize the service with Azure credentials.

        Args:
            credentials (Any): Azure client or credentials object
        """
        self.credentials = credentials.credentials
        self.subscription_id = credentials.subscription_id
        self.cloud_suffix = credentials.cloud_suffix

        self._storage_management_client: StorageManagementClient | None = None
        self._blob_service_clients_lock = threading.Lock()
        self._blob_service_clients: LRUCache[str, BlobServiceClient] = LRUCache(
            maxsize=self.MAX_CACHE_SIZE
        )

    def get_accounts_client(self) -> StorageManagementClient:
        """
        Get the Azure accounts client.

        Returns:
            Any: Azure accounts client
        """
        if self._storage_management_client:
            return self._storage_management_client

        self._storage_management_client = StorageManagementClient(
            self.credentials, self.subscription_id
        )
        return self._storage_management_client

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
        with self._blob_service_clients_lock:
            if (client := self._blob_service_clients.get(storage)) is not None:
                return client

        account_url = "https://{account}.{cloud_suffix}"
        client = BlobServiceClient(
            account_url.format(account=storage, cloud_suffix=self.cloud_suffix),
            credential=self.credentials,
            retry_connect=0,
        )
        with self._blob_service_clients_lock:
            self._blob_service_clients[storage] = client
        return client

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
                Storage(StorageProvider.AzureStorage, i.name, i.creation_time)
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
                            size=blob.size,
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
        cancel_event: threading.Event | None = None,
        progress_callback: Callable | None = None,
    ) -> None:
        """
        Upload a file to the specified Azure container path.
        Args:
            storage (str): The container name
            storage_path (str): The path within the container to upload
            source_path (Path): Local file path to upload
            dest_path (str, optional): Destination path in storage. Defaults to None.
            cancel_event (threading.Event, optional): Event to signal upload cancellation. Defaults to None.
            progress_callback (Callable, optional): Callback function for progress updates. Defaults to None.
        """
        try:
            if not storage_path:
                raise AzureMissingContainerError(
                    "Container is required for Azure storage"
                )

            containers_client = self.get_containers_client(storage)

            storage_path_parts = storage_path.split("/", 1)

            container = storage_path_parts[0]

            storage_path = storage_path_parts[1] if len(storage_path_parts) > 1 else ""
            blob_name = os.path.join(storage_path, dest_path or source_path.name)

            if source_path.stat().st_size > MULTIPART_UPLOAD_BLOCK_SIZE:
                self._upload_storage_multipart(
                    containers_client,
                    container,
                    source_path,
                    blob_name,
                    MULTIPART_UPLOAD_BLOCK_SIZE,
                    cancel_event,
                    progress_callback,
                )
            else:
                blob_client = containers_client.get_container_client(container)
                with open(source_path, "rb") as file_handle:
                    blob_client.upload_blob(
                        blob_name or source_path.name, file_handle, overwrite=True
                    )
        except Exception as ex:
            raise UploadStorageItemsError(str(ex)) from ex

    def download_storage_item(
        self,
        storage: str,
        key: str,
        progress_callback: Callable | None = None,
        cancel_event: threading.Event | None = None,
    ) -> str:
        """
        Download a file from Azure to the local filesystem.

        Args:
            storage (str): The container name
            key (str): The key/path of the item to download
            progress_callback (Callable, optional): Callback function for progress updates. Defaults to None.
            cancel_event (threading.Event, optional): Event to signal download cancellation. Defaults to None.
        """
        download_path = None
        try:
            download_path = Path(user_downloads_dir()) / Path(key).name
            suffix = Path(key).suffix
            download_tmp_path = (
                Path(user_downloads_dir())
                / f"{next(tempfile._get_candidate_names())}{suffix}"  # type: ignore
            )

            containers_client = self.get_containers_client(storage)
            path_parts = key.split("/", 1)
            container, blob_name = path_parts
            blob_client = containers_client.get_container_client(container)
            blob_stream = blob_client.download_blob(blob_name)
            total_bytes = blob_stream.properties.size

            downloaded = 0
            with open(download_path, "wb") as file:
                while downloaded < total_bytes:
                    if cancel_event and cancel_event.is_set():
                        raise Exception("Download cancelled")

                    chunk = blob_stream.read(DOWNLOAD_BLOCK_SIZE)
                    if not chunk:
                        break

                    file.write(chunk)

                    chunk_size = len(chunk)
                    downloaded += chunk_size

                    if progress_callback:
                        progress_callback(chunk_size)
            shutil.move(download_tmp_path, download_path)
            return str(download_path)
        except Exception as ex:
            if download_path and download_path.exists():
                download_path.unlink()
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

    def _upload_storage_multipart(
        self,
        client,
        container,
        source_path,
        blob_name,
        block_size,
        cancel_event: threading.Event | None = None,
        progress_callback: Callable | None = None,
    ):
        """
        Upload a file to Azure Blob Storage in multiple parts.

        Args:
            client (BlobServiceClient): The Azure Blob Service Client
            container (str): The name of the Azure container
            source_path (Path): Local file path to upload
            blob_name (str): The name of the blob in Azure
            block_size (int): Size of each block in bytes
            cancel_event (threading.Event, optional): Event to signal upload cancellation. Defaults to None.
            progress_callback (Callable, optional): Callback function for progress updates. Defaults to None.
        """
        block_ids = []
        blob_client = client.get_blob_client(container=container, blob=blob_name)
        with open(source_path, "rb") as file_handle:
            while chunk := file_handle.read(block_size):
                if cancel_event and cancel_event.is_set():
                    raise UploadStorageItemsError("Upload cancelled")
                block_id = uuid.uuid4().hex
                encoded_block_id = block_id.encode("utf-8").hex()[:64]
                blob_client.stage_block(block_id=encoded_block_id, data=chunk)
                block_ids.append(BlobBlock(block_id=encoded_block_id))
                if progress_callback:
                    progress_callback(block_size)
        blob_client.commit_block_list(block_ids)
