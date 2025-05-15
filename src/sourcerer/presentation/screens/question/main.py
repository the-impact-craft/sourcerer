from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Label

from sourcerer.presentation.screens.shared.widgets.button import Button


class QuestionScreen(ModalScreen[bool]):
    """Screen with a parameter."""

    CSS_PATH = "styles.tcss"

    def __init__(self, question: str) -> None:
        self.question = question
        super().__init__()

    def compose(self) -> ComposeResult:
        with Container():
            yield Label(self.question)
            with Horizontal():
                yield Button("Yes", name="yes")
                yield Button("No", name="no")

    @on(Button.Click)
    def on_button_click(self, event: Button.Click) -> None:
        """
        Handle button click events.
        """
        self.dismiss(event.action)  # type: ignore
