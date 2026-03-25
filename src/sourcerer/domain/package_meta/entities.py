from typing import Optional

from msgspec._core import Struct


class PackageMeta(Struct):
    version: str
    latest_version: Optional[str]
    has_available_update: bool
    system_version: str
    platform: str
