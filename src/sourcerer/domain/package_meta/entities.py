from msgspec._core import Struct


class PackageMeta(Struct):
    version: str
    latest_version: str
    has_available_update: bool
    system_version: str
    platform: str
