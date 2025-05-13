import json
import unittest
from unittest.mock import MagicMock, patch

from sourcerer.domain.access_credentials.entities import Credentials, AzureCredentials
from sourcerer.domain.access_credentials.repositories import BaseCredentialsRepository
from sourcerer.domain.shared.entities import StorageProvider
from sourcerer.infrastructure.access_credentials.exceptions import CredentialsAuthError
from sourcerer.infrastructure.access_credentials.services import (
    CredentialsService,
    S3AccessKeySecretKeyPair,
    S3ProfileName,
    GCPCredentialsService,
    AzureClientSecretCredentialsService
)


class TestCredentialsService(unittest.TestCase):
    """Test cases for CredentialsService."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_repo = MagicMock(spec=BaseCredentialsRepository)
        self.service = CredentialsService(self.mock_repo)
        
        # Sample credentials for testing
        self.sample_credentials = Credentials(
            uuid="test-uuid",
            name="test-name",
            provider="test-provider",
            credentials_type="key_pair",
            credentials=json.dumps({"key": "value"}),
            active=True
        )

    def test_list(self):
        """Test listing credentials."""
        # Arrange
        self.mock_repo.list.return_value = [self.sample_credentials]
        
        # Act
        result = self.service.list()
        
        # Assert
        self.mock_repo.list.assert_called_once_with(False)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], self.sample_credentials)

    def test_list_active_only(self):
        """Test listing only active credentials."""
        # Arrange
        self.mock_repo.list.return_value = [self.sample_credentials]
        
        # Act
        result = self.service.list(active_only=True)
        
        # Assert
        self.mock_repo.list.assert_called_once_with(True)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], self.sample_credentials)

    def test_get(self):
        """Test getting credentials by UUID."""
        # Arrange
        self.mock_repo.get.return_value = self.sample_credentials
        
        # Act
        result = self.service.get("test-uuid")
        
        # Assert
        self.mock_repo.get.assert_called_once_with("test-uuid")
        self.assertEqual(result, self.sample_credentials)

    def test_activate(self):
        """Test activating credentials."""
        # Act
        self.service.activate("test-uuid")
        
        # Assert
        self.mock_repo.activate.assert_called_once_with("test-uuid")

    def test_deactivate(self):
        """Test deactivating credentials."""
        # Act
        self.service.deactivate("test-uuid")
        
        # Assert
        self.mock_repo.deactivate.assert_called_once_with("test-uuid")


class TestS3AccessKeySecretKeyPair(unittest.TestCase):
    """Test cases for S3AccessKeySecretKeyPair."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_repo = MagicMock(spec=BaseCredentialsRepository)
        self.service = S3AccessKeySecretKeyPair(self.mock_repo)
        
        # Sample credentials for testing
        self.credentials_dict = {
            "aws_access_key_id": "test-access-key",
            "aws_secret_access_key": "test-secret-key",
            "endpoint_url": "https://test-endpoint.com"
        }
        
        self.sample_credentials = Credentials(
            uuid="test-uuid",
            name="test-name",
            provider=StorageProvider.S3,
            credentials_type="key_pair",
            credentials=json.dumps(self.credentials_dict),
            active=True
        )

    def test_store(self):
        """Test storing credentials."""
        # Arrange
        self.mock_repo.create.return_value = self.sample_credentials
        
        # Act
        self.service.store("test-name", self.credentials_dict)
        
        # Assert
        self.mock_repo.create.assert_called_once()
        created_credentials = self.mock_repo.create.call_args[0][0]
        self.assertEqual(created_credentials.name, "test-name")
        self.assertEqual(created_credentials.provider, StorageProvider.S3)
        self.assertEqual(created_credentials.credentials_type, "key_pair")
        self.assertEqual(created_credentials.credentials, json.dumps(self.credentials_dict))

    def test_extract(self):
        """Test extracting credentials."""
        # Arrange
        self.mock_repo.get.return_value = self.sample_credentials
        
        # Act
        result = self.service.extract("test-uuid")
        
        # Assert
        self.mock_repo.get.assert_called_once_with("test-uuid")
        self.assertIsInstance(result, Credentials)
        self.assertEqual(json.loads(result.credentials).get('aws_access_key_id'), "test-access-key")
        self.assertEqual(json.loads(result.credentials).get('aws_secret_access_key'), "test-secret-key")
        self.assertEqual(json.loads(result.credentials).get('endpoint_url'), "https://test-endpoint.com")


    @patch('sourcerer.infrastructure.access_credentials.services.boto3.Session')
    def test_authenticate_success(self, mock_session_class):
        """Test successful authentication."""
        # Arrange
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        # Act
        self.service.authenticate(json.dumps(self.credentials_dict))
        
        # Assert
        mock_session_class.assert_called_once_with(
            aws_access_key_id="test-access-key",
            aws_secret_access_key="test-secret-key"
        )

    @patch('sourcerer.infrastructure.access_credentials.services.boto3.Session')
    def test_authenticate_error(self, mock_session_class):
        """Test authentication error."""
        # Arrange
        mock_session_class.side_effect = Exception("Authentication failed")
        
        # Act & Assert
        with self.assertRaises(CredentialsAuthError):
            self.service.authenticate(json.dumps(self.credentials_dict))

    def test_auth_fields(self):
        """Test auth_fields method."""
        # Act
        result = self.service.auth_fields()
        
        # Assert
        self.assertEqual(len(result), 4)
        self.assertEqual(result[0].key, "aws_access_key_id")
        self.assertEqual(result[1].key, "aws_secret_access_key")
        self.assertEqual(result[2].key, "region")
        self.assertEqual(result[3].key, "endpoint_url")


class TestS3ProfileName(unittest.TestCase):
    """Test cases for S3ProfileName."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_repo = MagicMock(spec=BaseCredentialsRepository)
        self.service = S3ProfileName(self.mock_repo)
        
        # Sample credentials for testing
        self.credentials_dict = {
            "profile_name": "test-profile",
            "endpoint_url": "https://test-endpoint.com"
        }
        
        self.sample_credentials = Credentials(
            uuid="test-uuid",
            name="test-name",
            provider=StorageProvider.S3,
            credentials_type="profile",
            credentials=json.dumps(self.credentials_dict),
            active=True
        )

    def test_store(self):
        """Test storing credentials."""
        # Arrange
        self.mock_repo.create.return_value = self.sample_credentials
        
        # Act
        self.service.store("test-name", self.credentials_dict)
        
        # Assert
        self.mock_repo.create.assert_called_once()
        created_credentials = self.mock_repo.create.call_args[0][0]
        self.assertEqual(created_credentials.name, "test-name")
        self.assertEqual(created_credentials.provider, StorageProvider.S3)
        self.assertEqual(created_credentials.credentials_type, "profile_name")
        self.assertEqual(created_credentials.credentials, json.dumps(self.credentials_dict))

    def test_extract(self):
        """Test extracting credentials."""
        # Arrange
        self.mock_repo.get.return_value = self.sample_credentials
        
        # Act
        result = self.service.extract("test-uuid")
        
        # Assert
        self.mock_repo.get.assert_called_once_with("test-uuid")
        self.assertIsInstance(result, Credentials)
   
        self.assertEqual(json.loads(result.credentials).get('profile_name'), "test-profile")
        self.assertEqual(json.loads(result.credentials).get('endpoint_url'), "https://test-endpoint.com")

    def test_authenticate_success(self):
        """Test successful authentication."""
        # Arrange
        mock_session = MagicMock()
        
        # Act
        with patch('boto3.Session', return_value=mock_session) as mock_session_class:
            result = self.service.authenticate(json.dumps(self.credentials_dict))
        
            # Assert
            mock_session_class.assert_called_once_with(profile_name="test-profile")

    @patch('sourcerer.infrastructure.access_credentials.services.boto3.Session')
    def test_authenticate_error(self, mock_session_class):
        """Test authentication error."""
        # Arrange
        mock_session_class.side_effect = Exception("Authentication failed")
        
        # Act & Assert
        with self.assertRaises(CredentialsAuthError):
            self.service.authenticate(json.dumps(self.credentials_dict))

    def test_auth_fields(self):
        """Test auth_fields method."""
        # Act
        result = self.service.auth_fields()
        
        # Assert
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].key, "profile_name")
        self.assertEqual(result[1].key, "endpoint_url")


class TestGCPCredentialsService(unittest.TestCase):
    """Test cases for GCPCredentialsService."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_repo = MagicMock(spec=BaseCredentialsRepository)
        self.service = GCPCredentialsService(self.mock_repo)
        
        # Sample credentials for testing
        self.credentials_dict = {
            "service_acc": '{"type": "service_account", "project_id": "test-project"}'
        }
        
        self.sample_credentials = Credentials(
            uuid="test-uuid",
            name="test-name",
            provider=StorageProvider.GoogleCloudStorage,
            credentials_type="service_account",
            credentials=json.dumps(self.credentials_dict),
            active=True
        )

    def test_store(self):
        """Test storing credentials."""
        # Arrange
        self.mock_repo.create.return_value = self.sample_credentials
        
        # Act
        self.service.store("test-name", self.credentials_dict)
        
        # Assert
        self.mock_repo.create.assert_called_once()
        created_credentials = self.mock_repo.create.call_args[0][0]
        self.assertEqual(created_credentials.name, "test-name")
        self.assertEqual(created_credentials.provider, StorageProvider.GoogleCloudStorage)
        self.assertEqual(created_credentials.credentials_type, "Service account")
        self.assertEqual(created_credentials.credentials, json.dumps(self.credentials_dict))

    def test_extract(self):
        """Test extracting credentials."""
        # Arrange
        self.mock_repo.get.return_value = self.sample_credentials
        
        # Act
        result = self.service.extract("test-uuid")
        
        # Assert
        self.mock_repo.get.assert_called_once_with("test-uuid")
        self.assertIsInstance(result, Credentials)
        self.assertEqual(result.credentials_type, "service_account")
        self.assertEqual(json.loads(json.loads(result.credentials)['service_acc'])["project_id"], "test-project")

    @patch('sourcerer.infrastructure.access_credentials.services.storage.Client')
    def test_authenticate_success(self, mock_client_class):
        """Test successful authentication."""
        # Arrange
        mock_client = MagicMock()
        mock_client_class.from_service_account_info.return_value = mock_client
        
        # Act
        result = self.service.authenticate(json.dumps(self.credentials_dict))
        
        # Assert
        mock_client_class.from_service_account_info.assert_called_once()
        self.assertEqual(result, mock_client)

    @patch('sourcerer.infrastructure.access_credentials.services.storage.Client')
    def test_authenticate_error(self, mock_client_class):
        """Test authentication error."""
        # Arrange
        mock_client_class.from_service_account_info.side_effect = Exception("Authentication failed")
        
        # Act & Assert
        with self.assertRaises(CredentialsAuthError):
            self.service.authenticate(json.dumps(self.credentials_dict))

    def test_auth_fields(self):
        """Test auth_fields method."""
        # Act
        result = self.service.auth_fields()
        
        # Assert
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].key, "service_acc")


class TestAzureClientSecretCredentialsService(unittest.TestCase):
    """Test cases for AzureClientSecretCredentialsService."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_repo = MagicMock(spec=BaseCredentialsRepository)
        self.service = AzureClientSecretCredentialsService(self.mock_repo)
        
        # Sample credentials for testing
        self.credentials_dict = {
            "tenant_id": "test-tenant-id",
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "subscription_id": "test-subscription-id"
        }
        
        self.sample_credentials = Credentials(
            uuid="test-uuid",
            name="test-name",
            provider=StorageProvider.AzureStorage,
            credentials_type="client_secret",
            credentials=json.dumps(self.credentials_dict),
            active=True
        )

    def test_store(self):
        """Test storing credentials."""
        # Arrange
        self.mock_repo.create.return_value = self.sample_credentials
        
        # Act
        self.service.store("test-name", self.credentials_dict)
        
        # Assert
        self.mock_repo.create.assert_called_once()
        created_credentials = self.mock_repo.create.call_args[0][0]
        self.assertEqual(created_credentials.name, "test-name")
        self.assertEqual(created_credentials.provider, StorageProvider.AzureStorage)
        self.assertEqual(created_credentials.credentials_type, "Client Secret Credentials")
        self.assertEqual(created_credentials.credentials, json.dumps(self.credentials_dict))


    def test_extract(self):
        """Test extracting credentials."""
        # Arrange
        self.mock_repo.get.return_value = self.sample_credentials
        
        # Act
        result = self.service.extract("test-uuid")
        
        # Assert
        self.mock_repo.get.assert_called_once_with("test-uuid")
        self.assertIsInstance(result, Credentials)
        self.assertEqual(json.loads(result.credentials).get('tenant_id'), "test-tenant-id")
        self.assertEqual(json.loads(result.credentials).get('client_id'), "test-client-id")
        self.assertEqual(json.loads(result.credentials).get('client_secret'), "test-client-secret")
        self.assertEqual(json.loads(result.credentials).get('subscription_id'), "test-subscription-id")

    @patch('sourcerer.infrastructure.access_credentials.services.ClientSecretCredential')
    def test_authenticate_success(self, mock_credential_class):
        """Test successful authentication."""
        # Arrange
        mock_credential = MagicMock()
        mock_credential_class.return_value = mock_credential
        
        # Act
        result = self.service.authenticate(json.dumps(self.credentials_dict))
        
        # Assert
        mock_credential_class.assert_called_once_with(
            tenant_id="test-tenant-id",
            client_id="test-client-id",
            client_secret="test-client-secret"
        )
        self.assertIsInstance(result, AzureCredentials)
        self.assertEqual(result.credentials, mock_credential)
        self.assertEqual(result.subscription_id, "test-subscription-id")

    @patch('sourcerer.infrastructure.access_credentials.services.ClientSecretCredential')
    def test_authenticate_error(self, mock_credential_class):
        """Test authentication error."""
        # Arrange
        mock_credential_class.side_effect = Exception("Authentication failed")
        
        # Act & Assert
        with self.assertRaises(CredentialsAuthError):
            self.service.authenticate(json.dumps(self.credentials_dict))

    def test_auth_fields(self):
        """Test auth_fields method."""
        # Act
        result = self.service.auth_fields()
        
        # Assert
        self.assertEqual(len(result), 5)
        self.assertEqual(result[0].key, "subscription_id")
        self.assertEqual(result[1].key, "tenant_id")
        self.assertEqual(result[2].key, "client_id")
        self.assertEqual(result[3].key, "client_secret")
        self.assertEqual(result[4].key, "cloud_suffix")

if __name__ == "__main__":
    unittest.main()