from pathlib import Path

from rich.syntax import Syntax
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import LoadingIndicator, RichLog

from sourcerer.infrastructure.access_credentials.services import CredentialsService
from sourcerer.infrastructure.storage_provider.exceptions import (
    ReadStorageItemsError,
)
from sourcerer.presentation.screens.shared.widgets.button import Button
from sourcerer.presentation.utils import get_provider_service_by_access_uuid


class PreviewContentScreen(ModalScreen):
    CSS_PATH = "styles.tcss"

    def __init__(self, storage_name, key, access_credentials_uuid, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.storage_name = storage_name
        self.key = key
        self.access_credentials_uuid = access_credentials_uuid

    def compose(self) -> ComposeResult:
        with Container(id="PreviewContentScreen"):
            yield LoadingIndicator(id="loading")
            yield RichLog(highlight=True, markup=True, auto_scroll=False)
            with Horizontal(id="controls"):
                yield Button("Close", name="cancel")

    def on_mount(self) -> None:
        """Called when the DOM is ready."""

        credentials_service = CredentialsService()
        provider_service = get_provider_service_by_access_uuid(
            self.access_credentials_uuid, credentials_service
        )
        if not provider_service:
            self.notify("Could not read file :(", severity="error")
            return
        try:
            content = provider_service.read_storage_item(self.storage_name, self.key)
        except ReadStorageItemsError:
            self.notify("Could not read file :(", severity="error")
            return
        self.query_one("#loading").remove()
        if content is None:
            self.notify("Empty file", severity="warning")
            return

        text_log = self.query_one(RichLog)

        extension = Path(self.key).suffix
        match extension:
            case ".tfstate":
                lexer = "json"
            case _:
                lexer = Syntax.guess_lexer(self.key, content)
        content = Syntax(content, lexer, line_numbers=True, theme="ansi_dark")
        text_log.write(content)

    @on(Button.Click)
    def on_button_click(self, event: Button.Click) -> None:
        """Handle button click events."""
        if event.action == "cancel":
            self.dismiss()
