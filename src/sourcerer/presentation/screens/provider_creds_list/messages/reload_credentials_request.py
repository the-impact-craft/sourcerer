from dataclasses import dataclass

from textual.message import Message


@dataclass
class ReloadCredentialsRequest(Message):
    pass
