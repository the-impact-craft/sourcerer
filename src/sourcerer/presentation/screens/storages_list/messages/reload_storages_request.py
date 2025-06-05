from dataclasses import dataclass

from textual.message import Message


@dataclass
class ReloadStoragesRequest(Message):
    pass
