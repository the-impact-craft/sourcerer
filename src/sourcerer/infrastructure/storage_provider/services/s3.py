"""
Implementation of S3 compatible storage provider services.

This module provides concrete implementations of the BaseStorageProviderService
interface for various cloud storage providers.
"""

from collections.abc import Callable
from itertools import groupby
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
    CredentialsNotFoundError,
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


@storage_provider(StorageProvider.S3)
class S3ProviderService(BaseStorageProviderService):
    """
    AWS S3 storage provider service implementation.

    This class provides methods for interacting with AWS S3 storage,
    implementing the BaseStorageProviderService interface.
    """

    def __init__(self, credentials: Any):
        """
        Initialize the service with AWS credentials.

        Args:
            credentials (Any): AWS session or credentials object
        """
        self.credentials = credentials

    @property
    def client(self):
        """
        Get the S3 client.

        Returns:
            boto3.client: S3 client object
        """
        if not self.credentials:
            raise CredentialsNotFoundError()

        session = self.credentials.session

        client_args = {}
        if self.credentials.endpoint_url:
            client_args["endpoint_url"] = self.credentials.endpoint_url

        return session.client("s3", **client_args)

    @property
    def resource(self):
        """
        Get the S3 resource.

        Returns:
            boto3.resource: S3 resource object
        """
        if not self.credentials:
            raise CredentialsNotFoundError()

        session = self.credentials.session

        client_args = {}
        if self.credentials.endpoint_url:
            client_args["endpoint_url"] = self.credentials.endpoint_url
        return session.resource("s3", **client_args)

    def list_storages(self) -> list[Storage]:
        """
        Return a list of available S3 buckets.

        Returns:
            List[Storage]: List of storage objects representing S3 buckets

        Raises:
            ListStoragesError: If an error occurs while listing buckets
        """
        try:
            response = self.client.list_buckets()
        except Exception as ex:
            raise ListStoragesError(str(ex)) from ex
        return [
            Storage(StorageProvider.S3, i.get("Name"), i.get("CreationDate"))
            for i in response.get("Buckets")
        ]

    def get_storage_permissions(self, storage: str) -> list[StoragePermissions]:
        """
        Return the permissions for the specified S3 bucket.

        Args:
            storage (str): The bucket name

        Returns:
            List[StoragePermissions]: List of permission objects for the bucket

        Raises:
            StoragePermissionError: If an error occurs while getting permissions
        """
        try:
            permissions = self.client.get_bucket_acl(Bucket=storage)
        except Exception as ex:
            raise StoragePermissionError(str(ex)) from ex
        return [
            StoragePermissions(name, [i["Permission"] for i in items])
            for name, items in groupby(
                permissions["Grants"],
                key=lambda x: x["Grantee"]["DisplayName"] or x["Grantee"]["ID"],
            )
        ]

    def list_storage_items(
        self, storage: str, path: str = "", prefix: str = ""
    ) -> StorageContent:
        """
        List items in the specified S3 bucket path with the given prefix.

        Args:
            storage (str): The bucket name
            path (str, optional): The path within the bucket. Defaults to ''.
            prefix (str, optional): Filter items by this prefix. Defaults to ''.

        Returns:
            StorageContent: Object containing files and folders at the specified location

        Raises:
            ListStorageItemsError: If an error occurs while listing items
        """
        if path and not path.endswith("/"):
            path += "/"
        try:
            result = self.client.list_objects_v2(
                Bucket=storage,
                Prefix=path + prefix,
                Delimiter=PATH_DELIMITER,
                MaxKeys=PAGE_SIZE,
            )
        except Exception as ex:
            raise ListStorageItemsError(str(ex)) from ex

        folders = [
            Folder(i.get("Prefix").replace(path, ""))
            for i in result.get("CommonPrefixes", [])
            if i.get("Prefix")
        ]
        files = [
            File(
                generate_uuid(),
                i.get("Key").replace(path, ""),
                humanize.naturalsize(i.get("Size")),
                is_text_file(i.get("Key")),
                i.get("LastModified"),
            )
            for i in result.get("Contents", [])
            if i.get("Key").replace(path, "")
        ]
        return StorageContent(files=files, folders=folders)

    def read_storage_item(self, storage: str, key: str) -> str:
        """
        Read and return the content of the specified S3 object.

        Args:
            storage (str): The bucket name
            key (str): The key/path of the item to read

        Returns:
            bytes: The content of the S3 object

        Raises:
            ReadStorageItemsError: If an error occurs while reading the item
        """
        try:
            content_object = self.resource.Object(storage, key)
            return content_object.get()["Body"].read().decode("utf-8")
        except Exception as ex:
            raise ReadStorageItemsError(str(ex)) from ex

    def delete_storage_item(self, storage: str, key: str) -> None:
        """
        Delete the specified S3 object.

        Args:
            storage (str): The bucket name
            key (str): The key/path of the item to delete

        Raises:
            DeleteStorageItemsError: If an error occurs while deleting the item
        """
        try:
            return self.resource.Object(storage, key).delete()
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
        Upload a file to the specified S3 bucket path.

        Args:
            storage (str): The bucket name
            storage_path (str): The path within the bucket
            source_path (Path): Local file path to upload
            dest_path (str, optional): Destination path in S3. Defaults to None.

        Raises:
            UploadStorageItemsError: If an error occurs while uploading the item
        """
        try:
            dest_path = str(Path(storage_path or "") / (dest_path or source_path.name))
            self.client.upload_file(source_path, storage, dest_path)
        except Exception as ex:
            raise UploadStorageItemsError(str(ex)) from ex

    def download_storage_item(
        self, storage: str, key: str, progress_callback: Callable | None = None
    ) -> str:
        """
        Download a file from S3 to local filesystem.

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
            download_path = Path(user_downloads_dir()) / Path(key).name
            self.client.download_file(
                storage, key, download_path, Callback=progress_callback
            )
            return str(download_path)
        except Exception as ex:
            raise ReadStorageItemsError(str(ex)) from ex

    def get_file_size(self, storage: str, key: str) -> int:
        """
        Get metadata for an S3 object without downloading content.

        Args:
            storage (str): The bucket name
            key (str): The key/path of the item

        Returns:
            int: Size of the storage item in bytes

        Raises:
            ReadStorageItemsError: If an error occurs while getting metadata
        """
        try:
            metadata = self.client.head_object(Bucket=storage, Key=key)
            return metadata.get("ContentLength")
        except Exception as ex:
            raise ReadStorageItemsError(str(ex)) from ex
