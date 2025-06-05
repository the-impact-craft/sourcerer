from sourcerer.domain.storage.entities import Storage
from sourcerer.domain.storage.repositories import BaseStoragesRepository
from sourcerer.infrastructure.db.models import Storage as DBStorage


class SQLAlchemyStoragesRepository(BaseStoragesRepository):
    def __init__(self, db):
        """
        Initialize the repository with a database session factory.

        Args:
            db: Database session factory
        """
        self.db = db

    def create(self, storage: Storage) -> None:
        """
        Create a new storage entity in the database.

        Args:
            storage (Storage): The storage entity to be created
        """
        entry = DBStorage(
            uuid=storage.uuid,
            name=storage.name,
            credentials_id=storage.credentials_id,
            created_at=storage.date_created,
        )
        with self.db() as session:
            session.add(entry)
            session.commit()

    def list(self, provider_id: int | None = None) -> list[Storage]:
        """
        List all storages, optionally filtered by provider ID.

        Args:
            provider_id (int | None): The ID of the provider to filter by

        Returns:
            list[Storage]: List of storage entities
        """
        with self.db() as session:
            query = session.query(DBStorage)
            if provider_id is not None:
                query = query.filter(DBStorage.credentials_id == provider_id)
            return [
                Storage(
                    name=storage.name,
                    uuid=storage.uuid,
                    credentials_id=storage.credentials_id,
                    date_created=storage.created_at,
                    credentials_name=storage.credentials and storage.credentials.name,
                )
                for storage in query.all()
            ]

    def delete(self, uuid: str) -> None:
        """
        Delete a storage entity by its UUID.

        Args:
            uuid (str): The UUID of the storage entity to be deleted
        """
        with self.db() as session:
            storage = (
                session.query(DBStorage).filter(DBStorage.uuid == uuid).one_or_none()
            )
            if storage is None:
                return
            session.delete(storage)
            session.commit()
