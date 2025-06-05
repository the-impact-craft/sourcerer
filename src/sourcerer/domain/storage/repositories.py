from abc import ABCMeta, abstractmethod

from sourcerer.domain.storage.entities import Storage


class BaseStoragesRepository(metaclass=ABCMeta):
    @abstractmethod
    def create(self, storage: Storage) -> None:
        """Create a new storage entry in the repository.
        Args:
            storage (Storage): The storage object to store
        """
        raise NotImplementedError()

    @abstractmethod
    def list(self, provider_id: int | None = None) -> list[Storage]:
        """List all storage entries in the repository.
        Args:
            provider_id (int | None): The provider ID to filter by. If None, all entries are returned.
        Returns:
            List[Storage]: A list of storage entries
        """
        raise NotImplementedError()

    @abstractmethod
    def delete(self, uuid: str) -> None:
        """Delete a storage entry by UUID.
        Args:
            uuid (str): The UUID of the storage entry to delete
        """
        raise NotImplementedError()
