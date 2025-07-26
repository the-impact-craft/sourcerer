import contextlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import humanize
from dependency_injector.wiring import Provide
from rich.syntax import Syntax
from textual import events, on
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Horizontal
from textual.css.query import NoMatches
from textual.document._document import Selection
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Input, Label, LoadingIndicator, Rule, TextArea

from sourcerer.infrastructure.access_credentials.services import CredentialsService
from sourcerer.infrastructure.storage_provider.exceptions import (
    ReadStorageItemsError,
)
from sourcerer.presentation.di_container import DiContainer
from sourcerer.presentation.screens.preview_content.text_area_style import (
    SOURCERER_THEME_NAME,
    sourcerer_text_area_theme,
)
from sourcerer.presentation.screens.shared.modal_screens import ExitBoundModalScreen
from sourcerer.presentation.screens.shared.widgets.button import Button
from sourcerer.presentation.utils import get_provider_service_by_access_uuid
from sourcerer.settings import PREVIEW_LENGTH_LIMIT, PREVIEW_LIMIT_SIZE


@dataclass
class HighlightResult(Message):
    line: int
    start: int
    end: int


@dataclass
class HideSearchBar(Message):
    pass


class ClickableLabel(Label):
    @dataclass
    class Click(Message):
        name: str

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_click(self, _: events.Click) -> None:
        self.post_message(self.Click(name=self.name))  # type: ignore


class Search(Container):
    total = reactive(0, recompose=False)
    current = reactive(0, recompose=False)
    content = reactive("", recompose=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.search_result_lines = []
        self.search_value = ""

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Horizontal(id="left"):
                yield Label("Search:")
                yield Input(placeholder="...")

            with Horizontal(id="right"):
                yield ClickableLabel(
                    "◀", id="previous", name="previous", classes="search-button"
                )
                yield Label(f"{self.current}/{self.total}", id="search-result")
                yield ClickableLabel(
                    "▶", id="next", name="next", classes="search-button"
                )
                yield ClickableLabel(
                    "❌", id="hide", name="hide", classes="search-button"
                )
        yield Rule()

    @on(Input.Submitted)
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submitted events."""
        if not event.value or not self.content:
            self.total = 0
            self.current = 0
            self.search_value = ""
            self.search_result_lines = []
            return
        if event.value == self.search_value:
            self._increment_current()
            return

        self.search_value = event.value
        lines = self.content.split("\n")
        search_pattern = event.value.lower()

        self.search_result_lines = [
            (line_n, index)
            for line_n, line in enumerate(lines)
            if search_pattern in line.lower()
            for index in [
                match.start()
                for match in re.finditer(rf"(?i){re.escape(search_pattern)}", line)
            ]
        ]

        if not self.search_result_lines:
            self.notify("No matches found", severity="warning")
            self.total, self.current = 0, 0
            return

        self.total = len(self.search_result_lines)
        self.current = 1

    @on(ClickableLabel.Click)
    def on_click(self, event: ClickableLabel.Click) -> None:
        if event.name == "next":
            self._increment_current()
        elif event.name == "previous":
            self._decrement_current()
        elif event.name == "hide":
            self.post_message(HideSearchBar())

    def _increment_current(self):
        self.current = self.current + 1 if self.current < self.total else 1

    def _decrement_current(self):
        self.current = self.current - 1 if self.current > 1 else self.total

    def watch_current(self):
        with contextlib.suppress(NoMatches):
            search_result = self.query_one("#search-result", Label)
            search_result.update(f"{self.current}/{self.total}")
        if not self.search_result_lines:
            return
        line, start = self.search_result_lines[self.current - 1]
        self.post_message(
            HighlightResult(line, start=start, end=start + len(self.search_value))
        )


class PreviewContentScreen(ExitBoundModalScreen):
    CSS_PATH = "styles.tcss"

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel", "Close the screen"),
    ]

    def __init__(
        self,
        storage_name,
        key,
        file_size,
        access_credentials_uuid,
        settings,
        *args,
        credentials_service: CredentialsService = Provide[
            DiContainer.credentials_repository
        ],
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.storage_name = storage_name
        self.key = key
        self.file_size = file_size
        self.access_credentials_uuid = access_credentials_uuid
        self.credentials_service = credentials_service
        self.settings = settings
        self.content = None

    def compose(self) -> ComposeResult:
        with Container(id="PreviewContentScreen"):
            yield Search(id="search-bar")
            yield LoadingIndicator(id="loading")
            yield TextArea(read_only=True, show_line_numbers=True)
            with Horizontal(id="controls"):
                yield Button("Close", name="cancel")

    def on_mount(self) -> None:
        """Called when the DOM is ready."""
        search = self.query_one(Search)
        text_log = self.query_one(TextArea)
        text_log.register_theme(sourcerer_text_area_theme)
        text_log.theme = SOURCERER_THEME_NAME

        provider_service = get_provider_service_by_access_uuid(
            self.access_credentials_uuid,
            self.credentials_service,
            self.settings,
        )
        if not provider_service:
            self.notify("Could not read file :(", severity="error")
            return
        try:
            self.content = provider_service.read_storage_item(
                self.storage_name, self.key
            )
            if self.file_size > PREVIEW_LIMIT_SIZE:
                self.content = self.content[:PREVIEW_LENGTH_LIMIT]
                self.notify(
                    f"The file size {humanize.naturalsize(self.file_size)} "
                    f"exceeds {humanize.naturalsize(PREVIEW_LIMIT_SIZE)} preview limit. "
                    f"The content is truncated to {PREVIEW_LENGTH_LIMIT} characters.",
                    severity="warning",
                )
            search.content = self.content
        except ReadStorageItemsError:
            self.notify("Could not read file :(", severity="error")
            return
        self.query_one("#loading").remove()
        if self.content is None:
            self.notify("Empty file", severity="warning")
            return

        extension = Path(self.key).suffix

        lexer = (
            "json"
            if extension == ".tfstate"
            else Syntax.guess_lexer(self.key, self.content)
        )
        if lexer in text_log.available_languages:
            text_log.language = lexer
        else:
            text_log.language = "python"
        text_log.blur()
        text_log.load_text(self.content)

    @on(Button.Click)
    def on_button_click(self, event: Button.Click) -> None:
        """Handle button click events."""
        if event.action == "cancel":
            self.action_cancel_screen()

    @on(HideSearchBar)
    def on_hide_search_bar(self, _: HideSearchBar) -> None:
        """Handle hide search bar events."""
        search_bar = self.query_one("#search-bar", Search)
        search_bar.remove_class("-visible")
        search_bar.query_one(Input).value = ""
        search_bar.total = 0
        search_bar.current = 0
        search_bar.search_result_lines = []
        search_bar.search_value = ""

    @on(HighlightResult)
    def on_highlight_result(self, event: HighlightResult) -> None:
        """Handle highlight result events."""

        text_area = self.query_one(TextArea)
        text_area.selection = Selection(
            start=(event.line, event.start), end=(event.line, event.end)
        )

    def action_find(self):
        self.query_one("#search-bar").add_class("-visible")
        self.query_one(Input).focus()

    def action_cancel(self):
        self.action_cancel_screen()

    def on_key(self, event: events.Key) -> None:
        if event.key in ("ctrl+f", "super+f"):
            self.action_find()
