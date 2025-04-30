import unittest
from unittest.mock import MagicMock, patch

from sourcerer.domain.access_credentials.entities import Credentials
from sourcerer.infrastructure.access_credentials.repositories import SQLAlchemyCredentialsRepository
from sourcerer.infrastructure.db.models import Credentials as DBCredentials


class TestSQLAlchemyCredentialsRepository(unittest.TestCase):
    """Test cases for SQLAlchemyCredentialsRepository."""

    def setUp(self):
        """Set up test fixtures."""
        self.session = MagicMock()
        self.db_factory = MagicMock()
        self.db_factory.return_value.__enter__.return_value = self.session
        self.repository = SQLAlchemyCredentialsRepository(self.db_factory)
        
        # Sample credentials for testing
        self.sample_credentials = Credentials(
            uuid="test-uuid",
            name="test-name",
            provider="test-provider",
            credentials_type="key_pair",
            credentials={"key": "value"},
            active=True
        )
        
        # Sample DB credentials for testing
        self.db_credentials = DBCredentials(
            uuid="test-uuid",
            name="test-name",
            provider="test-provider",
            credentials_type="key_pair",
            credentials={"key": "value"},
            active=True
        )

    def test_create(self):
        """Test creating credentials."""
        # Act
        self.repository.create(self.sample_credentials)
        
        # Assert
        self.session.add.assert_called_once()
        self.session.commit.assert_called_once()
        
        # Get the credentials object that was added to the session
        added_credentials = self.session.add.call_args[0][0]
        self.assertEqual(added_credentials.uuid, self.sample_credentials.uuid)
        self.assertEqual(added_credentials.name, self.sample_credentials.name)
        self.assertEqual(added_credentials.provider, self.sample_credentials.provider)
        self.assertEqual(added_credentials.credentials_type, self.sample_credentials.credentials_type)
        self.assertEqual(added_credentials.credentials, self.sample_credentials.credentials)
        self.assertEqual(added_credentials.active, self.sample_credentials.active)

    def test_get(self):
        """Test retrieving credentials by UUID."""
        # Arrange
        self.session.query.return_value.filter.return_value.first.return_value = self.db_credentials
        
        # Act
        result = self.repository.get("test-uuid")
        
        # Assert
        self.session.query.assert_called_once_with(DBCredentials)
        self.session.query.return_value.filter.assert_called_once()
        self.assertEqual(result, self.db_credentials)

    def test_list_all(self):
        """Test listing all credentials."""
        # Arrange
        self.session.query.return_value.all.return_value = [self.db_credentials]
        
        # Act
        result = self.repository.list()
        
        # Assert
        self.session.query.assert_called_once_with(DBCredentials)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].uuid, self.sample_credentials.uuid)
        self.assertEqual(result[0].name, self.sample_credentials.name)
        self.assertEqual(result[0].provider, self.sample_credentials.provider)
        self.assertEqual(result[0].credentials_type, self.sample_credentials.credentials_type)
        self.assertEqual(result[0].credentials, self.sample_credentials.credentials)
        self.assertEqual(result[0].active, self.sample_credentials.active)

    def test_list_active_only(self):
        """Test listing only active credentials."""
        # Arrange
        self.session.query.return_value.filter.return_value.all.return_value = [self.db_credentials]
        
        # Act
        result = self.repository.list(active_only=True)
        
        # Assert
        self.session.query.assert_called_once_with(DBCredentials)
        self.session.query.return_value.filter.assert_called_once()
        self.assertEqual(len(result), 1)

    def test_activate(self):
        """Test activating credentials."""
        # Arrange
        self.session.query.return_value.filter.return_value.first.return_value = self.db_credentials
        
        # Act
        self.repository.activate("test-uuid")
        
        # Assert
        self.session.query.assert_called_once_with(DBCredentials)
        self.session.query.return_value.filter.assert_called_once()
        self.assertTrue(self.db_credentials.active)
        self.session.commit.assert_called_once()

    def test_deactivate(self):
        """Test deactivating credentials."""
        # Arrange
        self.session.query.return_value.filter.return_value.first.return_value = self.db_credentials
        
        # Act
        self.repository.deactivate("test-uuid")
        
        # Assert
        self.session.query.assert_called_once_with(DBCredentials)
        self.session.query.return_value.filter.assert_called_once()
        self.assertFalse(self.db_credentials.active)
        self.session.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()