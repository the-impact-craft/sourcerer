from sourcerer.domain.settings.entities import Settings
from sourcerer.domain.settings.services import BaseSettingsService


class SettingsService(BaseSettingsService):
    def load_settings(self) -> Settings:
        """Load settings from the settings file."""
        return self.repository.get_settings()

    def get_setting(self, key: str) -> str:
        """Get the value of a setting by its key."""
        return self.repository.get_setting(key)

    def set_setting(self, key: str, value: str) -> None:
        """Set the value of a setting by its key."""
        self.repository.set_setting(key, value)
