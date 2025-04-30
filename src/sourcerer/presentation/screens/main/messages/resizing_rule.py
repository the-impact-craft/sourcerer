from dataclasses import dataclass

from textual.message import Message


@dataclass
class ResizingRuleMove(Message):
    orientation: str
    delta: int
    previous_component_id: str
    next_component_id: str


@dataclass
class ResizingRuleSelect(Message):
    id: str


@dataclass
class ResizingRuleRelease(Message):
    id: str
