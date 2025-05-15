import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from sourcerer.domain.shared.entities import StorageProvider
from sourcerer.domain.storage_provider.entities import Folder, File, StorageContent
from sourcerer.infrastructure.storage_provider.exceptions import (
    ListStoragesError,
    StoragePermissionError,
    ListStorageItemsError,
    ReadStorageItemsError,
    DeleteStorageItemsError,
    UploadStorageItemsError
)
from sourcerer.infrastructure.storage_provider.services.gcp import GCPStorageProviderService
from sourcerer.infrastructure.storage_provider.services.s3 import S3ProviderService
from sourcerer.infrastructure.storage_provider.services.azure import AzureStorageProviderService
from sourcerer.settings import PAGE_SIZE


class DummyBlob:
    def __init__(self, name, size=123, updated=None):
        self.name = name
        self.size = size
        self.updated = updated or MagicMock(date=MagicMock(return_value="2024-01-01"))

class DummyBlobs:
    def __init__(self, blobs, prefixes=None):
        self._blobs = blobs
        self.prefixes = prefixes or []

    def __iter__(self):
        return iter(self._blobs)

class TestS3ProviderService(unittest.TestCase):
    """Test cases for S3ProviderService."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_credentials = MagicMock()
        self.mock_session = MagicMock()
        self.mock_credentials.session = self.mock_session
        self.mock_credentials.endpoint_url = None

        self.mock_client = MagicMock()
        self.mock_session.client.return_value = self.mock_client

        self.mock_resource = MagicMock()
        self.mock_session.resource.return_value = self.mock_resource

        self.service = S3ProviderService(self.mock_credentials)

        # Common test values
        self.test_bucket = "test-bucket"
        self.test_key = "test/path/file.txt"

    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.service.credentials, self.mock_credentials)

    def test_client_property(self):
        """Test client property."""
        # Act
        client = self.service.client

        # Assert
        self.mock_session.client.assert_called_once_with('s3')
        self.assertEqual(client, self.mock_client)

    def test_client_property_with_endpoint_url(self):
        """Test client property with endpoint URL."""
        # Arrange
        self.mock_credentials.endpoint_url = "https://custom-endpoint.com"

        # Act
        client = self.service.client

        # Assert
        self.mock_session.client.assert_called_once_with('s3', endpoint_url="https://custom-endpoint.com")
        self.assertEqual(client, self.mock_client)

    def test_resource_property(self):
        """Test resource property."""
        # Act
        resource = self.service.resource

        # Assert
        self.mock_session.resource.assert_called_once_with('s3')
        self.assertEqual(resource, self.mock_resource)

    def test_resource_property_with_endpoint_url(self):
        """Test resource property with endpoint URL."""
        # Arrange
        self.mock_credentials.endpoint_url = "https://custom-endpoint.com"

        # Act
        resource = self.service.resource

        # Assert
        self.mock_session.resource.assert_called_once_with('s3', endpoint_url="https://custom-endpoint.com")
        self.assertEqual(resource, self.mock_resource)

    def test_list_storages(self):
        """Test list_storages method."""
        # Arrange
        mock_response = {
            "Buckets": [
                {"Name": "bucket1", "CreationDate": "2023-01-01"},
                {"Name": "bucket2", "CreationDate": "2023-01-02"}
            ]
        }
        self.mock_client.list_buckets.return_value = mock_response

        # Act
        result = self.service.list_storages()

        # Assert
        self.mock_client.list_buckets.assert_called_once()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].storage, "bucket1")
        self.assertEqual(result[0].provider, StorageProvider.S3)
        self.assertEqual(result[0].date_created, "2023-01-01")
        self.assertEqual(result[1].storage, "bucket2")

    def test_list_storages_error(self):
        """Test list_storages method with error."""
        # Arrange
        self.mock_client.list_buckets.side_effect = Exception("Connection error")

        # Act & Assert
        with self.assertRaises(ListStoragesError):
            self.service.list_storages()

    def test_get_storage_permissions(self):
        """Test get_storage_permissions method."""
        # Arrange
        mock_response = {
            "Grants": [
                {"Grantee": {"DisplayName": "user1", "ID": "id1"}, "Permission": "READ"},
                {"Grantee": {"DisplayName": "user1", "ID": "id1"}, "Permission": "WRITE"},
                {"Grantee": {"DisplayName": "user2", "ID": "id2"}, "Permission": "READ"}
            ]
        }
        self.mock_client.get_bucket_acl.return_value = mock_response

        # Act
        result = self.service.get_storage_permissions(self.test_bucket)

        # Assert
        self.mock_client.get_bucket_acl.assert_called_once_with(Bucket=self.test_bucket)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].user, "user1")
        self.assertEqual(result[0].permissions, ["READ", "WRITE"])
        self.assertEqual(result[1].user, "user2")
        self.assertEqual(result[1].permissions, ["READ"])

    def test_get_storage_permissions_error(self):
        """Test get_storage_permissions method with error."""
        # Arrange
        self.mock_client.get_bucket_acl.side_effect = Exception("Access denied")

        # Act & Assert
        with self.assertRaises(StoragePermissionError):
            self.service.get_storage_permissions(self.test_bucket)

    def test_list_storage_items(self):
        """Test list_storage_items method."""
        # Arrange
        mock_response = {
            "CommonPrefixes": [
                {"Prefix": "test/folder1/"},
                {"Prefix": "test/folder2/"}
            ],
            "Contents": [
                {"Key": "test/file1.txt", "Size": 1024, "LastModified": "2023-01-01"},
                {"Key": "test/file2.txt", "Size": 2048, "LastModified": "2023-01-02"}
            ]
        }
        self.mock_client.list_objects_v2.return_value = mock_response

        # Act
        result = self.service.list_storage_items(self.test_bucket, "test/", "")

        # Assert
        self.mock_client.list_objects_v2.assert_called_once_with(
            Bucket=self.test_bucket,
            Prefix="test/",
            Delimiter="/",
            MaxKeys=PAGE_SIZE
        )
        self.assertEqual(len(result.folders), 2)
        self.assertEqual(result.folders[0].key, "folder1/")
        self.assertEqual(result.folders[1].key, "folder2/")
        self.assertEqual(len(result.files), 2)
        self.assertEqual(result.files[0].key, "file1.txt")
        self.assertEqual(result.files[1].key, "file2.txt")

    def test_list_storage_items_error(self):
        """Test list_storage_items method with error."""
        # Arrange
        self.mock_client.list_objects_v2.side_effect = Exception("Access denied")

        # Act & Assert
        with self.assertRaises(ListStorageItemsError):
            self.service.list_storage_items(self.test_bucket, "test/", "")

    def test_read_storage_item(self):
        """Test read_storage_item method."""
        # Arrange
        mock_body = MagicMock()
        mock_body.read.return_value = b"test content"

        mock_get_response = {"Body": mock_body}

        mock_object = MagicMock()
        mock_object.get.return_value = mock_get_response

        self.mock_resource.Object.return_value = mock_object

        # Act
        result = self.service.read_storage_item(self.test_bucket, self.test_key)

        # Assert
        self.mock_resource.Object.assert_called_once_with(self.test_bucket, self.test_key)
        mock_object.get.assert_called_once()
        self.assertEqual(result, "test content")

    def test_read_storage_item_error(self):
        """Test read_storage_item method with error."""
        # Arrange
        mock_object = MagicMock()
        mock_object.get.side_effect = Exception("File not found")

        self.mock_resource.Object.return_value = mock_object

        # Act & Assert
        with self.assertRaises(ReadStorageItemsError):
            self.service.read_storage_item(self.test_bucket, self.test_key)

    def test_delete_storage_item(self):
        """Test delete_storage_item method."""
        # Arrange
        mock_object = MagicMock()
        self.mock_resource.Object.return_value = mock_object

        # Act
        self.service.delete_storage_item(self.test_bucket, self.test_key)

        # Assert
        self.mock_resource.Object.assert_called_once_with(self.test_bucket, self.test_key)
        mock_object.delete.assert_called_once()

    def test_delete_storage_item_error(self):
        """Test delete_storage_item method with error."""
        # Arrange
        mock_object = MagicMock()
        mock_object.delete.side_effect = Exception("Access denied")

        self.mock_resource.Object.return_value = mock_object

        # Act & Assert
        with self.assertRaises(DeleteStorageItemsError):
            self.service.delete_storage_item(self.test_bucket, self.test_key)

    def test_upload_storage_item(self):
        """Test upload_storage_item method."""
        # Arrange
        source_path = Path("/test/source/file.txt")
        dest_path = "test/dest/file.txt"

        # Act
        self.service.upload_storage_item(self.test_bucket, '', source_path, dest_path)

        # Assert
        self.mock_client.upload_file.assert_called_once_with(source_path, self.test_bucket, dest_path)

    def test_upload_storage_item_default_dest(self):
        """Test upload_storage_item method with default destination path."""
        # Arrange
        source_path = Path("/test/source/file.txt")

        # Act
        self.service.upload_storage_item(self.test_bucket, '', source_path)

        # Assert
        self.mock_client.upload_file.assert_called_once_with(source_path, self.test_bucket, source_path.name)

    def test_upload_storage_item_error(self):
        """Test upload_storage_item method with error."""
        # Arrange
        source_path = Path("/test/source/file.txt")
        self.mock_client.upload_file.side_effect = Exception("Upload failed")

        # Act & Assert
        with self.assertRaises(UploadStorageItemsError):
            self.service.upload_storage_item(self.test_bucket, '', source_path)

    @patch('sourcerer.infrastructure.storage_provider.services.s3.user_downloads_dir')
    def test_download_storage_item(self, mock_user_downloads_dir):
        """Test download_storage_item method."""
        # Arrange
        mock_user_downloads_dir.return_value = "/test/downloads"

        # Act
        self.service.download_storage_item(self.test_bucket, self.test_key)

        # Assert
        self.mock_client.download_file.assert_called_once_with(
            self.test_bucket,
            self.test_key,
            Path("/test/downloads/file.txt"),
            Callback=None
        )

    def test_get_file_size(self):
        """Test get_file_size method."""
        # Arrange
        mock_response = {"ContentLength": 1024}
        self.mock_client.head_object.return_value = mock_response

        # Act
        result = self.service.get_file_size(self.test_bucket, self.test_key)

        # Assert
        self.mock_client.head_object.assert_called_once_with(Bucket=self.test_bucket, Key=self.test_key)
        self.assertEqual(result, 1024)

    def test_get_file_size_error(self):
        """Test get_file_size method with error."""
        # Arrange
        self.mock_client.head_object.side_effect = Exception("File not found")

        # Act & Assert
        with self.assertRaises(ReadStorageItemsError):
            self.service.get_file_size(self.test_bucket, self.test_key)


class TestGCPStorageProviderService(unittest.TestCase):
    """Test cases for GCPStorageProviderService."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.service = GCPStorageProviderService(self.mock_client)

        # Common test values
        self.test_bucket = "test-bucket"
        self.test_key = "test/path/file.txt"

    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.service.client, self.mock_client)

    def test_list_storages(self):
        """Test list_storages method."""
        # Arrange
        mock_bucket1 = MagicMock()
        mock_bucket1.name = "bucket1"
        mock_bucket1.time_created = "2023-01-01"

        mock_bucket2 = MagicMock()
        mock_bucket2.name = "bucket2"
        mock_bucket2.time_created = "2023-01-02"

        self.mock_client.list_buckets.return_value = [mock_bucket1, mock_bucket2]

        # Act
        result = self.service.list_storages()

        # Assert
        self.mock_client.list_buckets.assert_called_once()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].storage, "bucket1")
        self.assertEqual(result[0].provider, StorageProvider.GoogleCloudStorage)
        self.assertEqual(result[0].date_created, "2023-01-01")
        self.assertEqual(result[1].storage, "bucket2")

    def test_list_storages_error(self):
        """Test list_storages method with error."""
        # Arrange
        self.mock_client.list_buckets.side_effect = Exception("Connection error")

        # Act & Assert
        with self.assertRaises(ListStoragesError):
            self.service.list_storages()

    def test_get_storage_permissions(self):
        """Test get_storage_permissions method."""
        # Arrange
        mock_bucket = MagicMock()
        mock_policy = {
            "role1": ["user:user1@example.com", "user:user2@example.com"],
            "role2": ["user:user1@example.com"]
        }
        mock_bucket.get_iam_policy.return_value = mock_policy
        self.mock_client.get_bucket.return_value = mock_bucket

        # Act
        result = self.service.get_storage_permissions(self.test_bucket)

        # Assert
        self.mock_client.get_bucket.assert_called_once_with(self.test_bucket)
        mock_bucket.get_iam_policy.assert_called_once()
        self.assertEqual(len(result), 2)

        # Check user1 has both roles
        user1 = next(r for r in result if r.user == "user1@example.com")
        self.assertEqual(len(user1.permissions), 2)
        self.assertIn("role1", user1.permissions)
        self.assertIn("role2", user1.permissions)

        # Check user2 has only role1
        user2 = next(r for r in result if r.user == "user2@example.com")
        self.assertEqual(len(user2.permissions), 1)
        self.assertIn("role1", user2.permissions)

    def test_get_storage_permissions_error(self):
        """Test get_storage_permissions method with error."""
        # Arrange
        self.mock_client.get_bucket.side_effect = Exception("Access denied")

        # Act & Assert
        with self.assertRaises(StoragePermissionError):
            self.service.get_storage_permissions(self.test_bucket)

    def test_list_storage_items(self):
        """Test list_storage_items method."""
        # Arrange
        bucket = MagicMock()
        self.mock_client.bucket.return_value = bucket
        blobs = [
            DummyBlob("folder1/file1.txt", size=100),
            DummyBlob("folder1/file2.bin", size=200),
        ]
        prefixes = ["folder1/subfolder1/"]
        dummy_blobs = DummyBlobs(blobs, prefixes)
        bucket.list_blobs.return_value = dummy_blobs

        # Act
        result = self.service.list_storage_items("my-bucket", path="folder1")

        # Assert
        assert isinstance(result, StorageContent)
        assert len(result.files) == 2
        assert result.files[0].key == "file1.txt"
        assert result.files[0].is_text is True
        assert result.files[1].key == "file2.bin"
        assert result.files[1].is_text is False
        assert len(result.folders) == 1
        assert result.folders[0].key == "subfolder1/"


    def test_list_storage_items_error(self):
        """Test list_storage_items method with error."""
        # Arrange
        self.mock_client.bucket.side_effect = Exception("Access denied")

        # Act & Assert
        with self.assertRaises(ListStorageItemsError):
            self.service.list_storage_items(self.test_bucket, "test/", "")

    def test_read_storage_item(self):
        """Test read_storage_item method."""
        # Arrange
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.download_as_bytes.return_value = b"test content"

        self.mock_client.bucket.return_value = mock_bucket
        mock_bucket.get_blob.return_value = mock_blob

        # Act
        result = self.service.read_storage_item(self.test_bucket, self.test_key)

        # Assert
        self.mock_client.bucket.assert_called_once_with(self.test_bucket)
        mock_bucket.get_blob.assert_called_once_with(self.test_key)
        mock_blob.download_as_bytes.assert_called_once()
        self.assertEqual(result, "test content")

    def test_read_storage_item_error(self):
        """Test read_storage_item method with error."""
        # Arrange
        mock_bucket = MagicMock()
        mock_bucket.get_blob.side_effect = Exception("File not found")

        self.mock_client.bucket.return_value = mock_bucket

        # Act & Assert
        with self.assertRaises(ReadStorageItemsError):
            self.service.read_storage_item(self.test_bucket, self.test_key)

    def test_delete_storage_item(self):
        """Test delete_storage_item method."""
        # Arrange
        mock_bucket = MagicMock()
        mock_blob = MagicMock()

        self.mock_client.bucket.return_value = mock_bucket
        mock_bucket.get_blob.return_value = mock_blob

        # Act
        self.service.delete_storage_item(self.test_bucket, self.test_key)

        # Assert
        self.mock_client.bucket.assert_called_once_with(self.test_bucket)
        mock_bucket.get_blob.assert_called_once_with(self.test_key)
        mock_blob.delete.assert_called_once()

    def test_delete_storage_item_error(self):
        """Test delete_storage_item method with error."""
        # Arrange
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.delete.side_effect = Exception("Access denied")

        self.mock_client.bucket.return_value = mock_bucket
        mock_bucket.get_blob.return_value = mock_blob

        # Act & Assert
        with self.assertRaises(DeleteStorageItemsError):
            self.service.delete_storage_item(self.test_bucket, self.test_key)

    def test_upload_storage_item(self):
        """Test upload_storage_item method."""
        # Arrange
        source_path = Path("/test/source/file.txt")
        dest_path = "test/dest/file.txt"

        mock_bucket = MagicMock()
        mock_blob = MagicMock()

        self.mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        # Act
        self.service.upload_storage_item(self.test_bucket, '', source_path, dest_path)

        # Assert
        self.mock_client.bucket.assert_called_once_with(self.test_bucket)
        mock_bucket.blob.assert_called_once_with(dest_path)
        mock_blob.upload_from_filename.assert_called_once_with(source_path)

    def test_upload_storage_item_default_dest(self):
        """Test upload_storage_item method with default destination path."""
        # Arrange
        source_path = Path("/test/source/file.txt")

        mock_bucket = MagicMock()
        mock_blob = MagicMock()

        self.mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        # Act
        self.service.upload_storage_item(self.test_bucket, '', source_path)

        # Assert
        self.mock_client.bucket.assert_called_once_with(self.test_bucket)
        mock_bucket.blob.assert_called_once_with(source_path.name)
        mock_blob.upload_from_filename.assert_called_once_with(source_path)

    def test_upload_storage_item_error(self):
        """Test upload_storage_item method with error."""
        # Arrange
        source_path = Path("/test/source/file.txt")

        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.upload_from_filename.side_effect = Exception("Upload failed")

        self.mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        # Act & Assert
        with self.assertRaises(UploadStorageItemsError):
            self.service.upload_storage_item(self.test_bucket, '', source_path)

    @patch('sourcerer.infrastructure.storage_provider.services.gcp.user_downloads_dir')
    def test_download_storage_item(self, mock_user_downloads_dir):
        """Test download_storage_item method."""
        # Arrange
        mock_user_downloads_dir.return_value = "/test/downloads"

        mock_bucket = MagicMock()
        mock_blob = MagicMock()

        self.mock_client.bucket.return_value = mock_bucket
        mock_bucket.get_blob.return_value = mock_blob

        # Act
        self.service.download_storage_item(self.test_bucket, self.test_key)

        # Assert
        self.mock_client.bucket.assert_called_once_with(self.test_bucket)
        mock_bucket.get_blob.assert_called_once_with(self.test_key)
        mock_blob.download_to_filename.assert_called_once_with("/test/downloads/file.txt")

    def test_get_file_size(self):
        """Test get_file_size method."""
        # Arrange
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.size = 1024

        self.mock_client.bucket.return_value = mock_bucket
        mock_bucket.get_blob.return_value = mock_blob

        # Act
        result = self.service.get_file_size(self.test_bucket, self.test_key)

        # Assert
        self.mock_client.bucket.assert_called_once_with(self.test_bucket)
        mock_bucket.get_blob.assert_called_once_with(self.test_key)
        self.assertEqual(result, 1024)

    def test_get_file_size_error(self):
        """Test get_file_size method with error."""
        # Arrange
        mock_bucket = MagicMock()
        mock_bucket.get_blob.side_effect = Exception("File not found")

        self.mock_client.bucket.return_value = mock_bucket

        # Act & Assert
        with self.assertRaises(ReadStorageItemsError):
            self.service.get_file_size(self.test_bucket, self.test_key)


class TestAzureStorageProviderService(unittest.TestCase):
    """Test cases for AzureStorageProviderService."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_credentials = MagicMock()
        self.mock_credentials.credentials = MagicMock()
        self.mock_credentials.subscription_id = "test-subscription-id"
        self.mock_credentials.cloud_suffix = "blob.core.windows.net"

        # Mock for StorageManagementClient
        self.mock_storage_management_client = MagicMock()
        self.mock_storage_accounts = MagicMock()
        self.mock_storage_management_client.storage_accounts = self.mock_storage_accounts

        # Mock for BlobServiceClient
        self.mock_blob_service_client = MagicMock()
        self.mock_container_client = MagicMock()
        self.mock_blob_service_client.get_container_client.return_value = self.mock_container_client
        self.mock_blob_client = MagicMock()
        self.mock_blob_service_client.get_blob_client.return_value = self.mock_blob_client

        # Create service instance
        self.service = AzureStorageProviderService(self.mock_credentials)

        # Common test values
        self.test_storage = "test-storage"
        self.test_container = "test-container"
        self.test_blob_name = "test/path/file.txt"
        self.test_key = f"{self.test_container}/{self.test_blob_name}"

    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.service.credentials, self.mock_credentials.credentials)
        self.assertEqual(self.service.subscription_id, "test-subscription-id")

    @patch('sourcerer.infrastructure.storage_provider.services.azure.StorageManagementClient')
    def test_get_accounts_client(self, mock_storage_management_client_class):
        """Test get_accounts_client method."""
        # Arrange
        mock_storage_management_client_class.return_value = self.mock_storage_management_client

        # Act
        result = self.service.get_accounts_client()

        # Assert
        mock_storage_management_client_class.assert_called_once_with(
            self.mock_credentials.credentials, 
            self.mock_credentials.subscription_id
        )
        self.assertEqual(result, self.mock_storage_management_client)

    @patch('sourcerer.infrastructure.storage_provider.services.azure.BlobServiceClient')
    def test_get_containers_client(self, mock_blob_service_client_class):
        """Test get_containers_client method."""
        # Arrange
        mock_blob_service_client_class.return_value = self.mock_blob_service_client

        # Act
        result = self.service.get_containers_client(self.test_storage)

        # Assert
        mock_blob_service_client_class.assert_called_once_with(
            f"https://{self.test_storage}.blob.core.windows.net", 
            credential=self.mock_credentials.credentials,
            retry_connect=0,
        )
        self.assertEqual(result, self.mock_blob_service_client)

    def test_list_storages(self):
        """Test list_storages method."""
        # Arrange
        mock_account1 = MagicMock()
        mock_account1.name = "account1"
        mock_account1.creation_time = "2023-01-01"

        mock_account2 = MagicMock()
        mock_account2.name = "account2"
        mock_account2.creation_time = "2023-01-02"

        self.mock_storage_accounts.list.return_value = [mock_account1, mock_account2]

        with patch.object(self.service, 'get_accounts_client', return_value=self.mock_storage_management_client):
            # Act
            result = self.service.list_storages()

            # Assert
            self.mock_storage_accounts.list.assert_called_once()
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0].storage, "account1")
            self.assertEqual(result[0].provider, StorageProvider.AzureStorage)
            self.assertEqual(result[0].date_created, "2023-01-01")
            self.assertEqual(result[1].storage, "account2")

    def test_list_storages_error(self):
        """Test list_storages method with error."""
        # Arrange
        self.mock_storage_accounts.list.side_effect = Exception("Connection error")

        with patch.object(self.service, 'get_accounts_client', return_value=self.mock_storage_management_client):
            # Act & Assert
            with self.assertRaises(ListStoragesError):
                self.service.list_storages()

    def test_list_storage_items(self):
        """Test list_storage_items method."""
        # Arrange
        # Mock for container listing
        mock_container1 = MagicMock()
        mock_container1.name = "container1"
        mock_container2 = MagicMock()
        mock_container2.name = "container2"
        self.mock_blob_service_client.list_containers.return_value = [mock_container1, mock_container2]

        # Mock for blob listing
        mock_blob1 = MagicMock()
        mock_blob1.name = "file1.txt"
        mock_blob1.size = 1024
        mock_blob1.last_modified = "2023-01-01"

        mock_blob2 = MagicMock()
        mock_blob2.name = "subfolder/file2.txt"
        mock_blob2.size = 2048
        mock_blob2.last_modified = "2023-01-02"

        self.mock_container_client.walk_blobs.return_value = [mock_blob1, mock_blob2]

        with patch.object(self.service, 'get_containers_client', return_value=self.mock_blob_service_client):
            # Act - Test listing containers (empty path)
            result1 = self.service.list_storage_items(self.test_storage, "", "")

            # Assert
            self.mock_blob_service_client.list_containers.assert_called_once()
            self.assertEqual(len(result1.folders), 2)
            self.assertIn("container1", [i.key for i in result1.folders])
            self.assertIn("container2", [i.key for i in result1.folders])

            # Act - Test listing blobs in a container
            self.service.list_storage_items(self.test_storage, self.test_container, "")

            # Assert
            self.mock_blob_service_client.get_container_client.assert_called_with(self.test_container)
            self.mock_container_client.walk_blobs.assert_called_with(name_starts_with="", delimiter='/')

    def test_list_storage_items_error(self):
        """Test list_storage_items method with error."""
        # Arrange
        with patch.object(self.service, 'get_containers_client', side_effect=Exception("Access denied")):
            # Act & Assert
            with self.assertRaises(ListStorageItemsError):
                self.service.list_storage_items(self.test_storage, "", "")

    def test_read_storage_item(self):
        """Test read_storage_item method."""
        # Arrange
        mock_download_blob = MagicMock()
        mock_download_blob.readall.return_value = b"test content"
        self.mock_container_client.download_blob.return_value = mock_download_blob

        with patch.object(self.service, 'get_containers_client', return_value=self.mock_blob_service_client):
            # Act
            result = self.service.read_storage_item(self.test_storage, self.test_key)

            # Assert
            self.mock_blob_service_client.get_container_client.assert_called_with(self.test_container)
            self.mock_container_client.download_blob.assert_called_with(self.test_blob_name)
            self.assertEqual(result, "test content")

    def test_read_storage_item_error(self):
        """Test read_storage_item method with error."""
        # Arrange
        self.mock_container_client.download_blob.side_effect = Exception("File not found")

        with patch.object(self.service, 'get_containers_client', return_value=self.mock_blob_service_client):
            # Act & Assert
            with self.assertRaises(ReadStorageItemsError):
                self.service.read_storage_item(self.test_storage, self.test_key)

    def test_delete_storage_item(self):
        """Test delete_storage_item method."""
        # Arrange
        with patch.object(self.service, 'get_containers_client', return_value=self.mock_blob_service_client):
            # Act
            self.service.delete_storage_item(self.test_storage, self.test_key)

            # Assert
            self.mock_blob_service_client.get_container_client.assert_called_with(self.test_container)
            self.mock_container_client.delete_blob.assert_called_with(self.test_blob_name)

    def test_delete_storage_item_error(self):
        """Test delete_storage_item method with error."""
        # Arrange
        self.mock_container_client.delete_blob.side_effect = Exception("Access denied")

        with patch.object(self.service, 'get_containers_client', return_value=self.mock_blob_service_client):
            # Act & Assert
            with self.assertRaises(DeleteStorageItemsError):
                self.service.delete_storage_item(self.test_storage, self.test_key)

    def test_upload_storage_item(self):
        """Test upload_storage_item method."""
        # Arrange
        source_path = Path("/test/source/file.txt")
        dest_path = "test/dest/file.txt"

        with patch.object(self.service, 'get_containers_client', return_value=self.mock_blob_service_client):
            with patch('builtins.open', unittest.mock.mock_open(read_data=b'test content')):
                # Act
                self.service.upload_storage_item(self.test_storage, self.test_container, source_path, dest_path)

                # Assert
                self.mock_blob_service_client.get_container_client.assert_called_with(self.test_container)
                self.mock_container_client.upload_blob.assert_called_once()

    def test_upload_storage_item_default_dest(self):
        """Test upload_storage_item method with default destination path."""
        # Arrange
        source_path = Path("/test/source/file.txt")

        with patch.object(self.service, 'get_containers_client', return_value=self.mock_blob_service_client):
            with patch('builtins.open', unittest.mock.mock_open(read_data=b'test content')):
                # Act
                self.service.upload_storage_item(self.test_storage, self.test_container, source_path)

                # Assert
                self.mock_blob_service_client.get_container_client.assert_called_with(self.test_container)
                self.mock_container_client.upload_blob.assert_called_once()

    def test_upload_storage_item_error(self):
        """Test upload_storage_item method with error."""
        # Arrange
        source_path = Path("/test/source/file.txt")
        self.mock_container_client.upload_blob.side_effect = Exception("Upload failed")

        with patch.object(self.service, 'get_containers_client', return_value=self.mock_blob_service_client):
            with patch('builtins.open', unittest.mock.mock_open(read_data=b'test content')):
                # Act & Assert
                with self.assertRaises(UploadStorageItemsError):
                    self.service.upload_storage_item(self.test_storage, self.test_container, source_path)

    @patch('sourcerer.infrastructure.storage_provider.services.azure.user_downloads_dir')
    def test_download_storage_item(self, mock_user_downloads_dir):
        """Test download_storage_item method."""
        # Arrange
        mock_user_downloads_dir.return_value = "/test/downloads"
        mock_download_stream = MagicMock()
        mock_download_stream.readall.return_value = b"test content"
        self.mock_container_client.download_blob.return_value = mock_download_stream

        with patch.object(self.service, 'get_containers_client', return_value=self.mock_blob_service_client):
            with patch('builtins.open', unittest.mock.mock_open()) as mock_file:
                # Act
                result = self.service.download_storage_item(self.test_storage, self.test_key)

                # Assert
                self.mock_blob_service_client.get_container_client.assert_called_with(self.test_container)
                self.mock_container_client.download_blob.assert_called_with(self.test_blob_name)
                mock_file.assert_called_once()
                mock_file().write.assert_called_once_with(b"test content")
                self.assertTrue("/test/downloads/file.txt" in result)

    def test_get_file_size(self):
        """Test get_file_size method."""
        # Arrange
        mock_props = MagicMock()
        mock_props.size = 1024
        self.mock_blob_client.get_blob_properties.return_value = mock_props

        with patch.object(self.service, 'get_containers_client', return_value=self.mock_blob_service_client):
            # Act
            result = self.service.get_file_size(self.test_storage, self.test_key)

            # Assert
            self.mock_blob_service_client.get_blob_client.assert_called_with(self.test_container, self.test_blob_name)
            self.mock_blob_client.get_blob_properties.assert_called_once()
            self.assertEqual(result, 1024)

    def test_get_file_size_error(self):
        """Test get_file_size method with error."""
        # Arrange
        self.mock_blob_client.get_blob_properties.side_effect = Exception("File not found")

        with patch.object(self.service, 'get_containers_client', return_value=self.mock_blob_service_client):
            # Act & Assert
            with self.assertRaises(ReadStorageItemsError):
                self.service.get_file_size(self.test_storage, self.test_key)


if __name__ == "__main__":
    unittest.main()
