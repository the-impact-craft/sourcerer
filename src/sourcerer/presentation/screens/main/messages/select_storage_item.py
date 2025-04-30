from dataclasses import dataclass

from textual.message import Message


@dataclass
class SelectStorageItem(Message):
    name: str
    path: str | None = None
    access_credentials_uuid: str | None = None
    prefix: str | None = None
