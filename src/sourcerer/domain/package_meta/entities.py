from msgspec._core import Struct


class PackageMeta(Struct):
    version: str
    latest_version: str | None
    has_available_update: bool
    system_version: str
    platform: str
