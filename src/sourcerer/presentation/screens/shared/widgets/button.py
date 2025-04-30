from dataclasses import dataclass

from textual import events
from textual.message import Message
from textual.widgets import Label


class Button(Label):
    """
    A Button widget that extends the Label class to include click event handling.

    Attributes:
        Click (Message): A nested dataclass representing a click event with an action attribute.

    Methods:
        __init__(*args, **kwargs): Initializes the Button with optional arguments and ensures a 'name' attribute is
        provided.
        on_click(_: events.Click) -> None: Handles click events by posting a Click message with the button's name.
    """

    DEFAULT_CSS = """
    Button {
        &:hover {
            color: white;
        }
        &:focus {
            color: white;
        }
    }
    """

    @dataclass
    class Click(Message):
        action: str

    def __init__(self, *args, **kwargs):
        """
        Initialize the Button with optional arguments and ensure a 'name' attribute is provided.

        Raises:
            ValueError: If 'name' is not included in the keyword arguments.
        """
        super().__init__(*args, **kwargs)
        if "name" not in kwargs:
            raise ValueError("Name is required attribute for button")

    def on_click(self, _: events.Click) -> None:
        """
        Handle a click event by posting a Click message with the button's name.

        Args:
            _: An instance of events.Click representing the click event.
        """
        self.post_message(self.Click(self.name))  # type: ignore
