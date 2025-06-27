from typing import get_type_hints

from sourcerer.domain.settings.entities import Settings
from sourcerer.domain.settings.repositories import BaseSettingsRepository
from sourcerer.infrastructure.db.models import Settings as DBSettings


class SQLAlchemySettingsRepository(BaseSettingsRepository):
    def __init__(self, db):
        """
        Initialize the repository with a database session factory.

        Args:
            db: Database session factory
        """
        self.db = db

    def get_settings(self) -> Settings:
        """Retrieve all settings as a Settings."""

        with self.db() as session:
            settings = session.query(DBSettings).all()
        type_hints = get_type_hints(Settings)
        return Settings(
            **{
                setting.key: self.parse_value(
                    setting.key, setting.value, type_hints.get(setting.key, str)
                )
                for setting in settings
            }
        )

    def get_setting(self, key: str) -> str:
        """Retrieve a setting by its key."""
        with self.db() as session:
            setting = session.query(DBSettings).filter(DBSettings.key == key).first()
            if setting is None:
                raise KeyError(f"Setting '{key}' not found.")
            return setting.value

    def set_setting(self, key: str, value: str) -> None:
        """Set a setting with a given key and value."""
        with self.db() as session:
            setting = session.query(DBSettings).filter(DBSettings.key == key).first()
            if setting is None:
                setting = DBSettings(key=key, value=value)
                session.add(setting)
            else:
                setting.value = value
            session.commit()

    def parse_value(self, key: str, value: str, expected_type):
        if expected_type is bool:
            return value.lower() in ("true", "1", "yes", "on")
        if expected_type is int:
            return int(value)
        if expected_type is float:
            return float(value)
        return value  # Assume string or leave as-is
