"""
Database configuration and session management.

This module provides classes and utilities for configuring and
managing database connections and sessions.
"""

import contextlib

import sqlalchemy
from sqlalchemy.orm import scoped_session, sessionmaker

from sourcerer.infrastructure.db.models import Base


class Database:
    """
    Acts as a connection pool and session factory.

    This class manages database connections and provides
    session management for database operations.
    """

    def __init__(self, db_url):
        """
        Initialize the database with a connection URL.

        Args:
            db_url (str): Database connection URL
        """
        self.db_url = db_url
        self.engine = sqlalchemy.create_engine(db_url)
        self.scoped_session = scoped_session(sessionmaker(bind=self.engine))  # type: ignore

    def prepare_db(self):
        """
        Prepare the database by creating tables based on model definitions.
        """
        # Prepare mappings
        Base.metadata.create_all(self.engine)

    @contextlib.contextmanager
    def session(self):
        """
        Context manager for database sessions.

        Yields:
            Session: A database session

        Raises:
            Exception: Any exception that occurs during session use
        """
        session = self.scoped_session()
        try:
            yield session
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    @staticmethod
    def session_factory(db):
        """
        Create a session factory for the given database.

        Args:
            db (Session): Database instance

        Returns:
            callable: Session factory function
        """
        return db.session
