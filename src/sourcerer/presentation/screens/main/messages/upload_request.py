from dataclasses import dataclass

from textual.message import Message


@dataclass
class UploadRequest(Message):
    access_credentials_uuid: str
    storage: str
    path: str | None
