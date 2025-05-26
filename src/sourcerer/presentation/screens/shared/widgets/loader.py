from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static


class Loader(Container):
    stops = "⣷⣯⣟⡿⢿⣻⣽⣾"
    index = 0

    DEFAULT_CSS = """
    Loader {
        color: #9E53E0;
    }
    """

    def __init__(self, *args, **kwargs):
        self.label = Static(self.stops[self.index])
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        yield self.label

    def on_mount(self) -> None:
        self.auto_refresh = 1 / 10

    def automatic_refresh(self):
        self.index += 1
        if self.index >= len(self.stops):
            self.index = 0
        value = self.stops[self.index]
        self.label.update(value)
