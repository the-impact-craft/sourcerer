"""
Storage provider entity classes.

This module defines data classes representing cloud storage entities
such as storage containers, files, folders, and permissions.
"""

from datetime import datetime

from msgspec._core import Struct


class Storage(Struct):
    """
    Represents a cloud storage container (bucket/container).

    Attributes:
        credentials_id (int): The ID of the associated credentials
        name (str): The storage name/identifier (e.g., bucket name)
        date_created (datetime): When the storage was created
    """

    name: str
    uuid: str
    date_created: datetime
    credentials_id: int | None = None
    credentials_name: str | None = None
