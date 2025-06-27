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
from sourcerer.infrastructure.access_credentials.services import CredentialsService
from sourcerer.infrastructure.db.config import Database
from sourcerer.infrastructure.file_system.services import FileSystemService
from sourcerer.infrastructure.package_meta.services import PackageMetaService
from sourcerer.infrastructure.settings.repositories import SQLAlchemySettingsRepository
from sourcerer.infrastructure.settings.services import SettingsService
from sourcerer.infrastructure.storage.repositories import SQLAlchemyStoragesRepository
from sourcerer.infrastructure.storage.services import StoragesService
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

    storages_repository = providers.Factory(
        SQLAlchemyStoragesRepository, session_factory
    )

    settings_repository = providers.Factory(
        SQLAlchemySettingsRepository, session_factory
    )

    credentials_service = providers.Factory(
        CredentialsService, repository=credentials_repository
    )
    storages_service = providers.Factory(
        StoragesService,
        repository=storages_repository,
    )

    file_system_service = providers.Factory(FileSystemService, Path.home())

    package_meta_service = providers.Factory(PackageMetaService)
    settings_service = providers.Factory(
        SettingsService,
        repository=settings_repository,
    )
