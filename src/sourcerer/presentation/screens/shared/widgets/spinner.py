from collections.abc import Iterator
from enum import Enum
from itertools import cycle

from textual.app import RenderResult
from textual.widgets import Static


class SpinnerType(Enum):
    """Enumeration of various spinner animations."""

    dots_1 = "⣷⣯⣟⡿⢿⣻⣽⣾"
    dots_2 = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    dots_3 = "⠋⠙⠚⠞⠖⠦⠴⠲⠳⠓"
    dots_4 = "⠄⠆⠇⠋⠙⠸⠰⠠⠰⠸⠙⠋⠇⠆"
    dots_5 = "⠈⠐⠠⢀⡀⠄⠂⠁"
    dots_6 = "⋯⋱⋮⋰"
    circles = "◐◓◑◒"
    angles = "┐┤┘┴└├┌┬"
    arrows = "←↖↑↗→↘↓↙"
    moon = "🌑🌒🌓🌔🌕🌖🌗🌘"
    clock = "🕛🕐🕑🕒🕓🕔🕕🕖🕗🕘🕙🕚"
    histogram = "▁▃▄▅▆▇█▇▆▅▄▃"
    shade = "░▒▓█▓▒░"
    colors = "🟨🟨🟧🟧🟥🟥🟦🟦🟪🟪🟩🟩"
    triangles = "◢◣◤◥"


class Spinner(Static):
    """A loading spinner widget for Textual apps."""

    DEFAULT_CSS = """
    Spinner {
        color: #9E53E0;
    }
    """

    def __init__(self, spinner: SpinnerType = SpinnerType.dots_1, interval: float = 0.1, **kwargs):
        """
        Initialize the Loader widget.

        Args:
            spinner (SpinnerType): The spinner animation type.
            interval (float): Time in seconds between frames.
            **kwargs: Additional keyword arguments for Static.
        """
        super().__init__(**kwargs)
        self._frames: Iterator[str] = cycle(spinner.value)
        self._interval = interval

    def render(self) -> RenderResult:
        return next(self._frames)

    def on_mount(self) -> None:
        self.auto_refresh = self._interval
