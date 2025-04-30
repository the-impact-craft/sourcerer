from dataclasses import dataclass

from textual.message import Message


@dataclass
class UncheckFilesRequest(Message):
    keys: list[str]
