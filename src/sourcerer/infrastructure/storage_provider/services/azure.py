"""
Implementation of Azure storage provider services.

This module provides concrete implementations of the BaseStorageProviderService
interface for various cloud storage providers.
"""
import asyncio
import base64
import os.path
import shutil
import tempfile
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from azure.mgmt.storage import StorageManagementClient
from azure.storage.blob import (
    BlobBlock,
    BlobSasPermissions,
    BlobServiceClient,
    generate_blob_sas,
)
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
    PresignedUrlError,
    ReadStorageItemsError,
    UploadStorageItemsError,
)
from sourcerer.infrastructure.storage_provider.registry import storage_provider
from sourcerer.infrastructure.utils import generate_uuid, is_text_file, join_non_empty
from sourcerer.settings import (
    DEFAULT_DOWNLOAD_CHUNK_SIZE_MB,
    DEFAULT_PRESIGNED_URL_TTL_SECONDS,
    DEFAULT_UPLOAD_CHUNK_SIZE_MB,
)


@storage_provider(StorageProvider.AzureStorage)
class AzureStorageProviderService(BaseStorageProviderService):
    MAX_CACHE_SIZE = 10

    def __init__(
        self,
        credentials: Any,
        upload_chunk_size=DEFAULT_UPLOAD_CHUNK_SIZE_MB,
        download_chunk_size=DEFAULT_DOWNLOAD_CHUNK_SIZE_MB,
        presigned_url_ttl_seconds=DEFAULT_PRESIGNED_URL_TTL_SECONDS,
    ):
        """
        Initialize the service with Azure credentials.

        Args:
            credentials (Any): Azure client or credentials object
            upload_chunk_size (int): upload chunk size
            download_chunk_size (int): download chunk size

        """
        self.credentials = credentials.credentials
        self.subscription_id = credentials.subscription_id
        self.cloud_suffix = credentials.cloud_suffix

        self._storage_management_client: StorageManagementClient | None = None
        self._blob_service_clients_lock = threading.Lock()
        self._blob_service_clients: LRUCache[str, BlobServiceClient] = LRUCache(
            maxsize=self.MAX_CACHE_SIZE
        )

        self.upload_chunk_size = upload_chunk_size * 1024 * 1024
        self.download_chunk_size = download_chunk_size * 1024 * 1024
        self.presigned_url_expiration_period = presigned_url_ttl_seconds

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
            parent_path = ""
            prefix = prefix.strip("/")

            if not path:
                folders.update([i.name for i in containers_client.list_containers()])

            else:
                path_parts = path.split("/", 1)
                container = path_parts[0]

                blobs_client = containers_client.get_container_client(container)

                base_path = "" if len(path_parts) == 1 else path_parts[1] + "/"

                prefix_dirs = prefix.rsplit("/", 1)[0] if "/" in prefix else ""
                parent_path = join_non_empty(
                    [
                        container.strip("/"),
                        base_path.strip("/"),
                        prefix_dirs.strip("/"),
                    ],
                    "/",
                )
                parent_path = parent_path.rstrip("/") + "/"

                for blob in blobs_client.walk_blobs(
                    name_starts_with=base_path + prefix, delimiter="/"
                ):
                    remaining_path = blob.name[
                        len(base_path) + len(prefix_dirs) :
                    ].lstrip("/")

                    if "/" in remaining_path:
                        folder_name = remaining_path.split("/")[0]
                        folders.add(folder_name)
                        continue  # skip subfolders

                    files.append(
                        File(
                            generate_uuid(),
                            remaining_path,
                            size=blob.size,  # type: ignore
                            date_modified=blob.last_modified,  # type: ignore
                            is_text=is_text_file(blob.name),
                            parent_path=parent_path,
                        )
                    )
            return StorageContent(
                files=files,
                folders=[Folder(key.strip("/"), parent_path) for key in folders],
            )
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
            if len(path_parts) != 2:
                raise ValueError("Invalid key format")
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
            if len(path_parts) != 2:
                raise ValueError("Invalid key format")
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

            if source_path.stat().st_size <= self.upload_chunk_size:
                blob_client = containers_client.get_container_client(container)
                with open(source_path, "rb") as file_handle:
                    blob_client.upload_blob(
                        blob_name or source_path.name, file_handle, overwrite=True
                    )
                if progress_callback:
                    progress_callback(source_path.stat().st_size)
            else:
                try:
                    run_async_sync_safe(
                        self.upload_multipart(
                            containers_client,
                            container,
                            source_path,
                            blob_name,
                            self.upload_chunk_size,
                            cancel_event,
                            progress_callback,
                        )
                    )
                except Exception:
                    raise
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
        download_tmp_path = None
        try:
            download_path = Path(user_downloads_dir()) / Path(key).name
            suffix = Path(key).suffix
            download_tmp_path = (
                Path(user_downloads_dir())
                / f"{next(tempfile._get_candidate_names())}{suffix}"  # type: ignore
            )

            containers_client = self.get_containers_client(storage)
            path_parts = key.split("/", 1)
            if len(path_parts) != 2:
                raise ValueError("Invalid key format")
            container, blob_name = path_parts
            blob_client = containers_client.get_container_client(container)
            blob_stream = blob_client.download_blob(blob_name)
            total_bytes = blob_stream.properties.size

            with open(download_tmp_path, "wb") as file:
                if total_bytes <= self.download_chunk_size:
                    file.write(blob_stream.readall())
                else:
                    downloaded = 0
                    while downloaded < total_bytes:
                        if cancel_event and cancel_event.is_set():
                            raise Exception("Download cancelled")

                        chunk = blob_stream.read(self.download_chunk_size)
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
            if download_tmp_path and download_tmp_path.exists():
                download_tmp_path.unlink()
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
            if len(path_parts) != 2:
                raise ValueError("Invalid key format")
            container, blob_name = path_parts
            blob_client = containers_client.get_blob_client(container, blob_name)
            props = blob_client.get_blob_properties()
            return props.size
        except Exception as ex:
            raise ReadStorageItemsError(str(ex)) from ex

    def get_download_presigned_url(self, storage: str, key: str) -> str:
        """Generate a presigned URL to share an Azure object

        Args:
            storage (str): The bucket name
            key (str): The key/path of the item

        Returns:
            str: Presigned URL for accessing the blob
        """

        try:
            account_name = storage

            containers_client = self.get_containers_client(storage)
            path_parts = key.split("/", 1)
            if len(path_parts) != 2:
                raise ValueError("Invalid key format")
            container, blob_name = path_parts

            user_delegation_key = containers_client.get_user_delegation_key(
                key_start_time=datetime.utcnow(),
                key_expiry_time=datetime.utcnow()
                + timedelta(seconds=self.presigned_url_expiration_period),
            )

            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=container,
                blob_name=blob_name,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow()
                + timedelta(seconds=self.presigned_url_expiration_period),
                user_delegation_key=user_delegation_key,
            )
            url = f"https://{account_name}.blob.core.windows.net/{container}/{blob_name}?{sas_token}"

        except Exception as ex:
            raise PresignedUrlError(str(ex)) from ex

        return url

    async def upload_multipart(
        self,
        client,
        container: str,
        source_path: Path,
        blob_name: str,
        block_size: int,
        cancel_event=None,
        progress_callback=None,
    ):
        max_workers = 8

        blob_client = client.get_blob_client(container, blob_name)
        semaphore = asyncio.Semaphore(max_workers)

        async def upload_block(offset, data):
            async with semaphore:
                block_id = f"{offset:08d}"
                encoded_block_id = base64.b64encode(block_id.encode()).decode()
                blob_client.stage_block(block_id=encoded_block_id, data=data)
                if progress_callback:
                    progress_callback(len(data))
                if cancel_event and cancel_event.is_set():
                    raise Exception("Upload cancelled")
                return BlobBlock(block_id=encoded_block_id)

        async def read_and_upload():
            tasks = []
            with open(source_path, "rb") as f:
                offset = 0
                while chunk := f.read(block_size):
                    tasks.append(upload_block(offset, chunk))
                    offset += len(chunk)
                    if cancel_event and cancel_event.is_set():
                        raise Exception("Upload cancelled")
            return await asyncio.gather(*tasks)

        block_ids = await read_and_upload()
        blob_client.commit_block_list(block_ids)


# Todo: tmp solution, we need to move to async
def run_async_sync_safe(coro):
    def runner():
        return asyncio.run(coro)

    with ThreadPoolExecutor(1) as executor:
        future = executor.submit(runner)
        return future.result()
