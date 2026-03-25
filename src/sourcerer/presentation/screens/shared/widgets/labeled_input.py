from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Input, Label, TextArea


class LabeledInput(Container):
    """
    A container widget that combines a label and an input field.

    Attributes:
        DEFAULT_CSS (str): Default CSS styling for the widget.

    Args:
        key (str): The placeholder text for the input field.
        label (str): The text to display as the label.
        required (bool): Indicates if the input is required, adding an asterisk to the label if true.
        *args: Additional positional arguments for the container.
        **kwargs: Additional keyword arguments for the container.

    Methods:
        compose() -> ComposeResult: Yields a label and an input field for the widget.
    """

    DEFAULT_CSS = """
    LabeledInput {
        height: auto;
        margin-bottom: 1;
    }
    """

    @dataclass
    class Value:
        name: str
        value: str

    def __init__(self, key, label, required, multiline, *args, **kwargs):
        """
        Initializes a LabeledInput instance with a label and input field.

        Args:
            key (str): The placeholder text for the input field.
            label (str): The text to display as the label.
            required (bool): Indicates if the input is required, adding an asterisk to the label if true.
            multiline (bool): Indicates if input may contain multiple lines
            *args: Additional positional arguments for the container.
            **kwargs: Additional keyword arguments for the container.
        """
        super().__init__(*args, **kwargs)
        self.key = key
        self.label = label
        self.required = required
        self.multiline = multiline

    def compose(self) -> ComposeResult:
        """
        Yields a label and an input field for the LabeledInput widget.

        The label includes an asterisk if the input is required. The input field
        uses the provided key as its placeholder text.
        """
        label = f"* {self.label}" if self.required else self.label
        yield Label(label)
        if self.multiline:
            yield TextArea(show_line_numbers=False, classes="form_input")
        else:
            yield Input(placeholder=self.key, classes="form_input")

    def get(self):
        """
        Retrieves the value from the input field.

        Returns:
            Value: A dataclass containing the name and value of the input field.

        """
        input_area = self.query_one(".form_input")
        text = input_area.document.text if isinstance(input_area, TextArea) else input_area.value  # type: ignore
        return self.Value(name=self.key, value=text)
