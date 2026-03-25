"""
Implementation of GCP storage provider services.

This module provides concrete implementations of the BaseStorageProviderService
interface for various cloud storage providers.
"""
import datetime
import shutil
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

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
    PresignedUrlError,
    ReadStorageItemsError,
    StoragePermissionError,
    UploadStorageItemsError,
)
from sourcerer.infrastructure.storage_provider.registry import storage_provider
from sourcerer.infrastructure.utils import generate_uuid, is_text_file
from sourcerer.settings import (
    DEFAULT_DOWNLOAD_CHUNK_SIZE_MB,
    DEFAULT_PRESIGNED_URL_TTL_SECONDS,
    DEFAULT_UPLOAD_CHUNK_SIZE_MB,
    PAGE_SIZE,
    PATH_DELIMITER,
)


@storage_provider(StorageProvider.GoogleCloudStorage)
class GCPStorageProviderService(BaseStorageProviderService):
    """
    Google Cloud Platform storage provider service implementation.

    This class provides methods for interacting with GCP Cloud Storage,
    implementing the BaseStorageProviderService interface.
    """

    def __init__(
        self,
        credentials: Any,
        upload_chunk_size=DEFAULT_UPLOAD_CHUNK_SIZE_MB,
        download_chunk_size=DEFAULT_DOWNLOAD_CHUNK_SIZE_MB,
        presigned_url_ttl_seconds=DEFAULT_PRESIGNED_URL_TTL_SECONDS,
    ):
        """
        Initialize the service with GCP credentials.

        Args:
            credentials (Any): GCP client or credentials object
            upload_chunk_size (int): upload chunk size
            download_chunk_size (int): download chunk size
        """
        self.client = credentials
        self.upload_chunk_size = upload_chunk_size * 1024 * 1024
        self.download_chunk_size = download_chunk_size * 1024 * 1024
        self.presigned_url_expiration_period = presigned_url_ttl_seconds

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
            path = self._normalize_path(path)
            parent_path, prefix_folders_len = self._get_parent_path(path, prefix)

            bucket = self.client.bucket(storage)

            blobs = bucket.list_blobs(
                prefix=(path + prefix).lstrip("/"),
                delimiter=PATH_DELIMITER,
                max_results=PAGE_SIZE,
            )

            files = [
                File(
                    generate_uuid(),
                    blob.name[prefix_folders_len:],
                    size=blob.size,
                    date_modified=blob.updated.date(),
                    is_text=is_text_file(blob.name),
                    parent_path=parent_path,
                )
                for blob in blobs
            ]

            folders = [
                Folder(
                    key=folder[prefix_folders_len:].strip("/"), parent_path=parent_path
                )
                for folder in blobs.prefixes
            ]

            return StorageContent(files=files, folders=folders)

        except Exception as ex:
            raise ListStorageItemsError(
                f"Failed to list items in {storage}: {ex}"
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
        cancel_event: threading.Event | None = None,
        progress_callback: Callable | None = None,
    ) -> None:
        """
        Upload a file to the specified GCP bucket path.

        Args:
            storage (str): The bucket name
            storage_path (str): The path within the bucket
            source_path (Path): Local file path to upload
            dest_path (str, optional): Destination path in GCP. Defaults to None.
            cancel_event (threading.Event, optional): Event to signal upload cancellation. Defaults to None.
            progress_callback (Callable, optional): Callback function for progress updates. Defaults to None.

        Raises:
            UploadStorageItemsError: If an error occurs while uploading the item
        """
        try:
            bucket = self.client.bucket(storage)
            storage_path = str(
                Path(storage_path or "") / (dest_path or source_path.name)
            )
            blob = bucket.blob(storage_path)
            if source_path.stat().st_size <= self.upload_chunk_size:
                blob.upload_from_filename(source_path)
            else:
                self._upload_storage_item_multipart(
                    blob, source_path, cancel_event, progress_callback=progress_callback
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
        Download a file from GCP to the local filesystem.

        Args:
            storage (str): The bucket name
            key (str): The key/path of the item to download
            progress_callback (Callable, optional): Callback function for progress updates. Defaults to None.
            cancel_event (threading.Event, optional): Event to signal download cancellation. Defaults to None.
        Returns:
            str: Path to the downloaded file

        Raises:
            ReadStorageItemsError: If an error occurs while downloading the item
        """
        download_path = None
        try:
            bucket = self.client.bucket(storage)
            blob = bucket.get_blob(key)
            if not blob:
                raise BlobNotFoundError(key)

            download_path = Path(user_downloads_dir()) / Path(key).name

            suffix = Path(key).suffix
            download_tmp_path = (
                Path(user_downloads_dir())
                / f"{next(tempfile._get_candidate_names())}{suffix}"  # type: ignore
            )

            downloaded = 0

            with open(download_tmp_path, "wb") as file:
                reader = blob.open("rb")  # streaming mode
                while True:
                    if cancel_event and cancel_event.is_set():
                        raise Exception("Download cancelled")

                    chunk = reader.read(self.download_chunk_size)
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
            if download_path and Path(download_path).exists():
                Path(download_path).unlink()
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

    def get_download_presigned_url(self, storage: str, key: str) -> str:
        """Generate a presigned URL to share an GCP object

        Args:
            storage (str): The bucket name
            key (str): The key/path of the item

        Returns:
            str: Presigned URL for accessing the blob
        """

        try:
            bucket = self.client.bucket(storage)
            blob = bucket.get_blob(key)
            if not blob:
                raise BlobNotFoundError(key)

            response = blob.generate_signed_url(
                version="v4",
                expiration=datetime.timedelta(
                    seconds=self.presigned_url_expiration_period
                ),
                method="GET",
            )
        except Exception as ex:
            raise PresignedUrlError(str(ex)) from ex

        return response

    def _upload_storage_item_multipart(
        self,
        blob,
        source_path,
        cancel_event: threading.Event | None = None,
        progress_callback: Callable | None = None,
    ):
        """
        Upload a file to the specified GCP bucket path using multipart upload.

        This method is not implemented in the current version.
        """
        blob.chunk_size = self.upload_chunk_size

        with CancelableFileReader(
            source_path,
            cancel_event,
            chunk_size=self.upload_chunk_size,
            progress_callback=progress_callback,
        ) as stream:
            blob.upload_from_file(
                stream,
                rewind=True,  # allow re-seek to beginning if needed
                content_type="application/octet-stream",
            )


class CancelableFileReader:
    def __init__(
        self,
        file_path,
        cancel_event: threading.Event | None,
        chunk_size,
        progress_callback: Callable | None = None,
    ):
        self.file_path = file_path
        self.file = None
        self.cancel_event = cancel_event
        self.chunk_size = chunk_size
        self.progress_callback = progress_callback

    def read(self, size=None):
        if self.cancel_event and self.cancel_event.is_set():
            raise RuntimeError("Upload cancelled")

        if self.file is None:
            raise RuntimeError("File is not opened")
        chunk_size = size or self.chunk_size
        data = self.file.read(chunk_size)
        if data and self.progress_callback:
            self.progress_callback(len(data))
        return data

    def seek(self, offset, whence=0):
        if self.file is None:
            raise RuntimeError("File is not opened")
        return self.file.seek(offset, whence)

    def tell(self):
        if self.file is None:
            raise RuntimeError("File is not opened")
        return self.file.tell()

    def close(self):
        if self.file is None:
            return None
        return self.file.close()

    def __enter__(self):
        self.file = open(self.file_path, "rb")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
