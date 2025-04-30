import unittest
from datetime import datetime
from unittest.mock import patch

from sqlalchemy import Column, Integer, Boolean, DateTime, String
from sqlalchemy_utils.types.encrypted.encrypted_type import EncryptedType

from sourcerer.infrastructure.db.models import Base, Credentials
from sourcerer.settings import ENCRYPTION_KEY


class TestCredentialsModel(unittest.TestCase):
    """Test cases for the Credentials database model."""

    def test_tablename(self):
        """Test that the table name is set correctly."""
        self.assertEqual(Credentials.__tablename__, "credentials")

    def test_columns(self):
        """Test that the model has the expected columns with correct types."""
        # Get all columns from the model
        columns = Credentials.__table__.columns
        
        # Check that all expected columns exist with correct types
        self.assertIsInstance(columns.get("id").type, Integer)
        self.assertIsInstance(columns.get("uuid").type, String)
        self.assertIsInstance(columns.get("name").type, String)
        self.assertIsInstance(columns.get("provider").type, String)
        self.assertIsInstance(columns.get("credentials_type").type, String)
        self.assertIsInstance(columns.get("credentials").type, EncryptedType)
        self.assertIsInstance(columns.get("active").type, Boolean)
        self.assertIsInstance(columns.get("created_at").type, DateTime)
        self.assertIsInstance(columns.get("updated_at").type, DateTime)

    def test_column_constraints(self):
        """Test that columns have the expected constraints."""
        # Get all columns from the model
        columns = Credentials.__table__.columns
        
        # Check primary key
        self.assertTrue(columns.get("id").primary_key)
        
        # Check nullable constraints
        self.assertFalse(columns.get("uuid").nullable)
        self.assertFalse(columns.get("name").nullable)
        self.assertFalse(columns.get("provider").nullable)
        self.assertFalse(columns.get("credentials_type").nullable)
        self.assertFalse(columns.get("credentials").nullable)
        
        # Check unique constraints
        self.assertTrue(columns.get("uuid").unique)
        
        # Check default values
        self.assertTrue(columns.get("active").default.arg)  # Default is True

    def test_encryption_key(self):
        """Test that the credentials column uses the correct encryption key."""
        # Get the credentials column
        credentials_column = Credentials.__table__.columns.get("credentials")
        
        # Check that it's using the correct encryption key
        self.assertEqual(credentials_column.type.key, ENCRYPTION_KEY)


if __name__ == "__main__":
    unittest.main()