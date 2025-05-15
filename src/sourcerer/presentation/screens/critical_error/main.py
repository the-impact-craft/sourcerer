import platform
import sys
import webbrowser

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widgets import Label, RichLog

from sourcerer import __version__
from sourcerer.presentation.screens.shared.widgets.button import Button


class CriticalErrorScreen(ModalScreen[bool]):
    """Screen with a parameter."""

    CSS_PATH = "styles.tcss"

    def __init__(self, error: str, traceback: str) -> None:
        self.error = error
        self.traceback = traceback
        super().__init__()

    def compose(self) -> ComposeResult:
        with Container(id="CriticalErrorScreen"):
            yield Label(self.error)
            yield RichLog(highlight=True, markup=True)
            with Horizontal():
                yield Button("Report", name="report")
                yield Button("Dismiss", name="dismiss")

    def on_mount(self) -> None:
        """
        Called when the screen is mounted.
        """
        self.query_one("#CriticalErrorScreen").border_title = "Critical Error"
        try:
            text_log = self.query_one(RichLog)
        except NoMatches:
            return

        text_log.write(self.traceback)

    @on(Button.Click)
    def on_button_click(self, event: Button.Click) -> None:
        """
        Handle button click events.
        """
        if event.action == "report":
            webbrowser.open(self._build_github_issue_url(), new=0, autoraise=True)
        elif event.action == "dismiss":
            self.dismiss()  # type: ignore

    def _build_github_issue_url(self) -> str:
        """
        Build the GitHub issue URL.
        """

        error_body = f"""
Operating System: {platform.system()}({platform.release()})
Python Version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}
Sourcerer Version: {__version__}
Steps to Reproduce:
…
…
…
Traceback:
```{self.traceback}```
        """

        return (
            f"https://github.com/the-impact-craft/sourcerer/issues/new?"
            f"title=Runtime issue:{self.error}&"
            f"body={error_body}"
        )
