from msgspec._core import Struct


class Settings(Struct):
    theme: str = "github-dark"
    group_by_access_credentials: bool = False


class SettingsFields:
    theme = "theme"
    group_by_access_credentials = "group_by_access_credentials"
