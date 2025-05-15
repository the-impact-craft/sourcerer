"""
Database models for the application.

This module defines SQLAlchemy models representing database tables
and their relationships.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import declarative_base
from sqlalchemy_utils.types.encrypted.encrypted_type import EncryptedType

from sourcerer.settings import ENCRYPTION_KEY

Base = declarative_base()


class Credentials(Base):
    """
    SQLAlchemy model for storing access credentials.

    This model represents the credentials table in the database,
    storing encrypted credential information for various providers.

    Attributes:
        id (int): Primary key
        uuid (str): Unique identifier for the credentials
        name (str): Name of the credentials
        provider (str): Name of the service provider
        credentials_type (str): Type of credentials (e.g., key_pair)
        credentials (str): Encrypted credentials data
        active (bool): Indicates if the credentials are active
        created_at (datetime): Timestamp when the credentials were created
        updated_at (datetime): Timestamp when the credentials were last updated
    """

    __tablename__ = "credentials"
    id = Column(Integer, primary_key=True)
    uuid = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    credentials_type = Column(String, nullable=False)
    credentials = Column(EncryptedType(String, ENCRYPTION_KEY), nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
