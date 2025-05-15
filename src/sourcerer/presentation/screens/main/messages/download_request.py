from dataclasses import dataclass

from textual.message import Message


@dataclass
class DownloadRequest(Message):
    storage_name: str
    access_credentials_uuid: str
    path: str
    keys: list[str]
