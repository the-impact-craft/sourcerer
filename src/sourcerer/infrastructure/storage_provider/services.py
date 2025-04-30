"""
Implementation of storage provider services.

This module provides concrete implementations of the BaseStorageProviderService
interface for various cloud storage providers.
"""

from itertools import groupby
from pathlib import Path
from typing import List, Any, Callable

import humanize
from platformdirs import user_downloads_dir

from sourcerer.domain.shared.entities import StorageProvider
from sourcerer.domain.storage_provider.entities import (
    StoragePermissions,
    StorageContent,
    Folder,
    File,
    Storage,
)
from sourcerer.domain.storage_provider.services import BaseStorageProviderService
from sourcerer.infrastructure.storage_provider.exceptions import (
    ListStoragesException,
    StoragePermissionException,
    ListStorageItemsException,
    ReadStorageItemsException,
    DeleteStorageItemsException,
    UploadStorageItemsException,
    CredentialsNotFoundException,
)
from sourcerer.infrastructure.storage_provider.registry import storage_provider
from sourcerer.infrastructure.utils import generate_uuid, is_text_file
from sourcerer.settings import PATH_DELIMITER, PAGE_SIZE


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
            raise CredentialsNotFoundException()

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
            raise CredentialsNotFoundException()

        session = self.credentials.session

        client_args = {}
        if self.credentials.endpoint_url:
            client_args["endpoint_url"] = self.credentials.endpoint_url
        return session.resource("s3", **client_args)

    def list_storages(self) -> List[Storage]:
        """
        Return a list of available S3 buckets.

        Returns:
            List[Storage]: List of storage objects representing S3 buckets

        Raises:
            ListStoragesException: If an error occurs while listing buckets
        """
        try:
            response = self.client.list_buckets()
        except Exception as ex:
            raise ListStoragesException(str(ex)) from ex
        return [
            Storage(StorageProvider.S3, i.get("Name"), i.get("CreationDate"))
            for i in response.get("Buckets")
        ]

    def get_storage_permissions(self, storage: str) -> List[StoragePermissions]:
        """
        Return the permissions for the specified S3 bucket.

        Args:
            storage (str): The bucket name

        Returns:
            List[StoragePermissions]: List of permission objects for the bucket

        Raises:
            StoragePermissionException: If an error occurs while getting permissions
        """
        try:
            permissions = self.client.get_bucket_acl(Bucket=storage)
        except Exception as ex:
            raise StoragePermissionException(str(ex)) from ex
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
            ListStorageItemsException: If an error occurs while listing items
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
            raise ListStorageItemsException(str(ex)) from ex

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
            ReadStorageItemsException: If an error occurs while reading the item
        """
        try:
            content_object = self.resource.Object(storage, key)
            return content_object.get()["Body"].read().decode("utf-8")
        except Exception as ex:
            raise ReadStorageItemsException(str(ex)) from ex

    def delete_storage_item(self, storage: str, key: str) -> None:
        """
        Delete the specified S3 object.

        Args:
            storage (str): The bucket name
            key (str): The key/path of the item to delete

        Raises:
            DeleteStorageItemsException: If an error occurs while deleting the item
        """
        try:
            return self.resource.Object(storage, key).delete()
        except Exception as ex:
            raise DeleteStorageItemsException(str(ex)) from ex

    def upload_storage_item(
        self, storage: str, source_path: Path, dest_path: str | None = None
    ) -> None:
        """
        Upload a file to the specified S3 bucket path.

        Args:
            storage (str): The bucket name
            source_path (Path): Local file path to upload
            dest_path (str, optional): Destination path in S3. Defaults to None.

        Raises:
            UploadStorageItemsException: If an error occurs while uploading the item
        """
        try:
            self.client.upload_file(source_path, storage, dest_path or source_path.name)
        except Exception as ex:
            raise UploadStorageItemsException(str(ex)) from ex

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
            ReadStorageItemsException: If an error occurs while downloading the item
        """
        try:
            download_path = Path(user_downloads_dir()) / Path(key).name
            self.client.download_file(
                storage, key, download_path, Callback=progress_callback
            )
            return str(download_path)
        except Exception as ex:
            raise ReadStorageItemsException(str(ex)) from ex

    def get_file_size(self, storage: str, key: str) -> dict:
        """
        Get metadata for an S3 object without downloading content.

        Args:
            storage (str): The bucket name
            key (str): The key/path of the item

        Returns:
            dict: Metadata for the specified S3 object

        Raises:
            ReadStorageItemsException: If an error occurs while getting metadata
        """
        try:
            metadata = self.client.head_object(Bucket=storage, Key=key)
            return metadata.get("ContentLength")
        except Exception as ex:
            raise ReadStorageItemsException(str(ex)) from ex


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

    def list_storages(self) -> List[Storage]:
        """
        Return a list of available GCP buckets.

        Returns:
            List[Storage]: List of storage objects representing GCP buckets

        Raises:
            ListStoragesException: If an error occurs while listing buckets
        """
        try:
            return [
                Storage(StorageProvider.GoogleCloudStorage, i.name, i.time_created)
                for i in self.client.list_buckets()
            ]
        except Exception as ex:
            raise ListStoragesException(str(ex)) from ex

    def get_storage_permissions(self, storage: str) -> List[StoragePermissions]:
        """
        Return the permissions for the specified GCP bucket.

        Args:
            storage (str): The bucket name

        Returns:
            List[StoragePermissions]: List of permission objects for the bucket

        Raises:
            StoragePermissionException: If an error occurs while getting permissions
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
            raise StoragePermissionException(str(ex)) from ex

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
            ListStorageItemsException: If an error occurs while listing items
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
            raise ListStorageItemsException(
                f"Failed to list items in {storage}: {str(ex)}"
            ) from ex

    def read_storage_item(self, storage: str, key: str) -> str:
        """
        Read and return the content of the specified GCP object.

        Args:
            storage (str): The bucket name
            key (str): The key/path of the item to read

        Returns:
            bytes: The content of the GCP object

        Raises:
            ReadStorageItemsException: If an error occurs while reading the item
        """
        try:
            bucket = self.client.bucket(storage)
            blob = bucket.get_blob(key)
            content = blob.download_as_bytes()
            return content.decode("utf-8")
        except Exception as ex:
            raise ReadStorageItemsException(str(ex)) from ex

    def delete_storage_item(self, storage: str, key: str) -> None:
        """
        Delete the specified GCP object.

        Args:
            storage (str): The bucket name
            key (str): The key/path of the item to delete

        Raises:
            DeleteStorageItemsException: If an error occurs while deleting the item
        """
        try:
            bucket = self.client.bucket(storage)
            blob = bucket.get_blob(key)
            blob.delete()
        except Exception as ex:
            raise DeleteStorageItemsException(str(ex)) from ex

    def upload_storage_item(
        self, storage: str, source_path: Path, dest_path: str | None = None
    ) -> None:
        """
        Upload a file to the specified GCP bucket path.

        Args:
            storage (str): The bucket name
            source_path (Path): Local file path to upload
            dest_path (str, optional): Destination path in GCP. Defaults to None.

        Raises:
            UploadStorageItemsException: If an error occurs while uploading the item
        """
        try:
            bucket = self.client.bucket(storage)
            bucket.blob(dest_path or source_path.name).upload_from_filename(source_path)
        except Exception as ex:
            raise UploadStorageItemsException(str(ex)) from ex

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
            ReadStorageItemsException: If an error occurs while downloading the item
        """
        try:
            bucket = self.client.bucket(storage)
            blob = bucket.get_blob(key)
            download_path = Path(user_downloads_dir()) / Path(key).name
            blob.download_to_filename(str(download_path))
            return str(download_path)
        except Exception as ex:
            raise ReadStorageItemsException(str(ex)) from ex

    def get_file_size(self, storage: str, key: str) -> dict:
        """
        Get metadata for a GCP object without downloading content.

        Args:
            storage (str): The bucket name
            key (str): The key/path of the item

        Returns:
            dict: Metadata for the specified GCP object

        Raises:
            ReadStorageItemsException: If an error occurs while getting metadata
        """
        try:
            bucket = self.client.bucket(storage)
            blob = bucket.get_blob(key)
            return blob.size
        except Exception as ex:
            raise ReadStorageItemsException(str(ex)) from ex
