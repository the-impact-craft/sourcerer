from abc import ABCMeta, abstractmethod

from sourcerer.domain.settings.entities import Settings


class BaseSettingsRepository(metaclass=ABCMeta):
    @abstractmethod
    def get_settings(self) -> Settings:
        """Retrieve all settings as a Settings."""
        raise NotImplementedError()

    @abstractmethod
    def get_setting(self, key: str) -> str:
        """Retrieve a setting by its key."""
        raise NotImplementedError()

    @abstractmethod
    def set_setting(self, key: str, value: str) -> None:
        """Set a setting with a given key and value."""
        raise NotImplementedError()
