"""
Database models for the application.

This module defines SQLAlchemy models representing database tables
and their relationships.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import backref, declarative_base, relationship
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


class Storage(Base):
    """
    SQLAlchemy model for storing storage information.

    This model represents the storage table in the database,
    storing information about different storage containers.

    Attributes:
        id (int): Primary key
        uuid (str): Unique identifier for the storage
        name (str): Name of the storage
        credentials_id (int): Foreign key referencing the credentials table
        created_at (datetime): Timestamp when the storage was created
    """

    __tablename__ = "storages"
    id = Column(Integer, primary_key=True)
    uuid = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    credentials_id = Column(
        Integer, ForeignKey("credentials.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    credentials = relationship(
        "Credentials",
        cascade="save-update",
        backref=backref("storages", passive_deletes=True),
    )


class Settings(Base):
    """
    SQLAlchemy model for storing application settings.

    This model represents the settings table in the database,
    storing key-value pairs for application configuration.

    Attributes:
        id (int): Primary key
        key (str): Setting key
        value (str): Setting value
        created_at (datetime): Timestamp when the setting was created
        updated_at (datetime): Timestamp when the setting was last updated
    """

    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
