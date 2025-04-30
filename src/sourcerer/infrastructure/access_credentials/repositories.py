"""
SQLAlchemy implementation of the credentials repository.

This module provides a concrete implementation of the BaseCredentialsRepository
interface using SQLAlchemy for database access.
"""

from sourcerer.domain.access_credentials.entities import Credentials
from sourcerer.domain.access_credentials.repositories import BaseCredentialsRepository
from sourcerer.infrastructure.db.models import Credentials as DBCredentials


class SQLAlchemyCredentialsRepository(BaseCredentialsRepository):
    """
    SQLAlchemy implementation of the credentials repository.

    This class provides methods for storing and retrieving credentials
    using SQLAlchemy as the database access layer.
    """

    def __init__(self, db):
        """
        Initialize the repository with a database session factory.

        Args:
            db: Database session factory
        """
        self.db = db

    def create(self, credentials: Credentials):
        """
        Create new credentials in the database.

        Args:
            credentials (Credentials): The credentials object to store
        """
        credentials = DBCredentials(
            uuid=credentials.uuid,
            name=credentials.name,
            provider=credentials.provider,
            credentials_type=credentials.credentials_type,
            credentials=credentials.credentials,
            active=credentials.active,
        )
        with self.db() as session:
            session.add(credentials)
            session.commit()

    def get(self, uuid: str):
        """
        Retrieve credentials by UUID.

        Args:
            uuid (str): Unique identifier for the credentials

        Returns:
            DBCredentials: The credentials object from the database
        """
        with self.db() as session:
            return (
                session.query(DBCredentials).filter(DBCredentials.uuid == uuid).first()
            )

    def list(self, active_only: bool | None = None):
        """
        List all credentials in the repository.

        Args:
            active_only (bool|None, optional): If True, return only active credentials.
                If False, return all credentials. Defaults to None.

        Returns:
            List[Credentials]: List of credentials objects
        """
        with self.db() as session:
            credentials_query = session.query(DBCredentials)
            if active_only:
                credentials_query = credentials_query.filter(
                    DBCredentials.active == True  # noqa: E712
                )
            return [
                Credentials(
                    uuid=credential.uuid,
                    name=credential.name,
                    provider=credential.provider,
                    credentials_type=credential.credentials_type,
                    credentials=credential.credentials,
                    active=credential.active,
                )
                for credential in credentials_query.all()
            ]

    def activate(self, uuid):
        """
        Activate credentials by UUID.

        Args:
            uuid (str): Unique identifier for the credentials to activate
        """
        with self.db() as session:
            credentials = (
                session.query(DBCredentials).filter(DBCredentials.uuid == uuid).first()
            )
            credentials.active = True
            session.commit()

    def deactivate(self, uuid):
        """
        Deactivate credentials by UUID.

        Args:
            uuid (str): Unique identifier for the credentials to deactivate
        """
        with self.db() as session:
            credentials = (
                session.query(DBCredentials).filter(DBCredentials.uuid == uuid).first()
            )
            credentials.active = False
            session.commit()
