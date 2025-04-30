"""
Dependency injection container configuration for the Sourcerer application.

This module defines the dependency injection container that manages the application's
dependencies and their lifecycle. It provides a centralized way to configure
and access services, repositories, and other components throughout the application.
"""

from pathlib import Path

from dependency_injector import containers, providers

from sourcerer.infrastructure.access_credentials.repositories import (
    SQLAlchemyCredentialsRepository,
)
from sourcerer.infrastructure.db.config import Database
from sourcerer.infrastructure.file_system.services import FileSystemService
from sourcerer.settings import APP_DIR, DB_NAME

DB_URL = f"sqlite:////{APP_DIR}/{DB_NAME}"


class DiContainer(containers.DeclarativeContainer):
    """
    Dependency injection container for the Sourcerer application.

    This container manages the application's dependencies including:
    - Database configuration and connection
    - Session factory for database operations
    - Credentials repository for managing access credentials
    - File system service for local file operations

    The container uses the dependency_injector library to provide
    a clean way to manage dependencies and their lifecycle.
    """

    config = providers.Configuration()

    db = providers.Singleton(Database, db_url=DB_URL)
    session_factory = providers.Factory(Database.session_factory, db=db)

    credentials_repository = providers.Factory(
        SQLAlchemyCredentialsRepository, session_factory
    )

    file_system_service = providers.Factory(FileSystemService, Path.home())
