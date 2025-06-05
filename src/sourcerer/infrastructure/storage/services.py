from sourcerer.domain.storage.entities import Storage
from sourcerer.domain.storage.repositories import BaseStoragesRepository


class StoragesService:
    def __init__(
        self,
        repository: BaseStoragesRepository,
    ):
        self.repository = repository

    def create(self, storage: Storage) -> None:
        """
        Create a new storage entity.

        Args:
            storage (Storage): The storage object to be created
        """
        self.repository.create(storage)

    def list(self, provider_id: int | None = None) -> list[Storage]:
        """
        List all storage entities.

        Args:
            provider_id (int|None, optional): If provided, filter storage entities by provider ID
        """
        return self.repository.list(provider_id)

    def delete(self, uuid: str) -> None:
        """
        Delete a storage entity by its UUID.

        Args:
            uuid (str): The UUID of the storage entity to be deleted
        """
        self.repository.delete(uuid)
