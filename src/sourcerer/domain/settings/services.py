from sourcerer.domain.settings.entities import Settings
from sourcerer.domain.settings.repositories import BaseSettingsRepository


class BaseSettingsService:
    def __init__(self, repository: BaseSettingsRepository):
        self.repository = repository

    def load_settings(self) -> Settings:
        """Load settings from the settings file."""
        raise NotImplementedError("This method should be implemented by subclasses.")

    def get_setting(self, key: str) -> str:
        """Get the value of a setting by its key."""
        raise NotImplementedError("This method should be implemented by subclasses.")

    def set_setting(self, key: str, value: str) -> None:
        """Set the value of a setting by its key."""
        raise NotImplementedError("This method should be implemented by subclasses.")
