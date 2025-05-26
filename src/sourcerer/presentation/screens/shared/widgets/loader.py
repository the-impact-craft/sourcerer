from textual.containers import Container


class Loader(Container):
    stops = "⣷⣯⣟⡿⢿⣻⣽⣾"
    index = 0

    DEFAULT_CSS = """
    Loader {
        color: #9E53E0;
    }
    """

    def on_mount(self) -> None:
        self.auto_refresh = 1 / 10

    def render(self):
        value = self.stops[self.index]
        self.index += 1
        if self.index >= len(self.stops):
            self.index = 0
        return value
