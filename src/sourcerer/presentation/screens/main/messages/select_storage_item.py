from dataclasses import dataclass
from typing import Optional

from textual.message import Message


@dataclass
class SelectStorageItem(Message):
    name: str
    path: Optional[str] = None
    access_credentials_uuid: Optional[str] = None
    prefix: Optional[str] = None
    focus_content: bool = False
