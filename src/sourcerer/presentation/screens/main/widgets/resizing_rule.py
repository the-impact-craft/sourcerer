from dataclasses import dataclass

from textual.events import MouseDown, MouseUp
from textual.reactive import reactive
from textual.widgets import Rule

from sourcerer.presentation.screens.main.messages.resizing_rule import (
    ResizingRuleMove,
    ResizingRuleRelease,
    ResizingRuleSelect,
)


@dataclass
class MoveEvent:
    timestamp: float
    delta: int


class ResizingRule(Rule, can_focus=True):
    dragging: reactive[bool] = reactive(False)
    position: reactive[MoveEvent | None] = reactive(None)

    def __init__(self, prev_component_id, next_component_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not kwargs.get("id"):
            raise ValueError("ResizingRule must have an id")
        self.prev_component_id = prev_component_id
        self.next_component_id = next_component_id

    def on_mouse_down(self, _: MouseDown) -> None:
        """Start dragging when the separator is clicked."""
        self.dragging = True
        self.post_message(ResizingRuleSelect(id=self.id))  # type: ignore

    def on_mouse_up(self, _: MouseUp) -> None:
        """Stop dragging when mouse is released."""
        self.cleanup()

    def watch_position(self):
        """
        Watch for changes in the position and post a ResizingRuleMove message if dragging is active.
        """
        if not self.dragging:
            return

        if self.position is None:
            return

        self.post_message(
            ResizingRuleMove(
                delta=self.position.delta,
                previous_component_id=self.prev_component_id,
                next_component_id=self.next_component_id,
                orientation=self.orientation,
            )
        )

    def cleanup(self):
        """
        Resets the dragging state and position, and posts a ResizingRuleRelease message to signal the end of a resize
        operation.
        """
        self.dragging = False
        self.position = None

        self.post_message(ResizingRuleRelease(id=self.id))  # type: ignore
