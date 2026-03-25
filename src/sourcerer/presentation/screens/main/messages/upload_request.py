from dataclasses import dataclass
from typing import Optional

from textual.message import Message


@dataclass
class UploadRequest(Message):
    access_credentials_uuid: str
    storage: str
    path: Optional[str]
