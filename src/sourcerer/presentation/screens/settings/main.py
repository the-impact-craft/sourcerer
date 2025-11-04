from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.validation import Number
from textual.widgets import Checkbox, Input, Rule, Select, Static

from sourcerer.domain.settings.entities import Settings, SettingsFields
from sourcerer.presentation.screens.shared.modal_screens import ExitBoundModalScreen
from sourcerer.presentation.screens.shared.widgets.button import Button


class SettingsScreen(ExitBoundModalScreen):
    """Screen with a parameter."""

    CSS_PATH = "styles.tcss"

    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self.settings = settings

    def compose(self) -> ComposeResult:
        with Container():
            with Horizontal():
                yield Static("Theme:")
                yield Select(
                    ((theme, theme) for theme in self.app._registered_themes),
                    id="theme",
                    value=self.settings.theme,
                    allow_blank=False,
                )

            yield Rule()
            with Horizontal():
                yield Checkbox(
                    "Group storage by access credentials",
                    value=self.settings.group_by_access_credentials,
                )

            yield Rule()
            with Horizontal():
                yield Static("Upload chunk size (MB):")
                yield Input(
                    type="integer",
                    id="upload_chunk_size",
                    value=str(self.settings.upload_chunk_size),
                    validators=[
                        Number(minimum=1, maximum=1000),
                    ],
                )
            with Horizontal():
                yield Static("Download chunk size (MB):")
                yield Input(
                    type="integer",
                    id="download_chunk_size",
                    value=str(self.settings.download_chunk_size),
                    validators=[
                        Number(minimum=1, maximum=1000),
                    ],
                )
            with Horizontal():
                yield Static("Presigned url ttl (sec):")
                yield Input(
                    type="integer",
                    id="presigned_url_ttl_seconds",
                    value=str(self.settings.presigned_url_ttl_seconds),
                    validators=[
                        Number(minimum=1, maximum=604800),
                    ],
                )

            yield Rule()
            with Horizontal(id="controls"):
                yield Button("Save", name="save")
                yield Button("Close", name="close")

    @on(Button.Click)
    def on_button_clicked(self, event: Button.Click) -> None:
        """Handle button clicked events."""
        if event.action == "close":
            self.action_cancel_screen()
        elif event.action == "save":
            upload_chunk_size = self.query_one("Input#upload_chunk_size", Input).value
            download_chunk_size = self.query_one(
                "Input#download_chunk_size", Input
            ).value
            presigned_url_ttl_seconds = self.query_one(
                "Input#presigned_url_ttl_seconds", Input
            ).value

            if not upload_chunk_size.isdigit():
                self.notify("Invalid upload chunk size", severity="error")
                return
            if not download_chunk_size.isdigit():
                self.notify("Invalid download chunk size", severity="error")
                return
            if not presigned_url_ttl_seconds.isdigit():
                self.notify("Invalid presigned url ttl", severity="error")
                return

            self.dismiss(
                {
                    SettingsFields.theme: self.query_one("Select#theme", Select).value,
                    SettingsFields.group_by_access_credentials: self.query_one(
                        Checkbox
                    ).value,
                    SettingsFields.upload_chunk_size: int(upload_chunk_size),
                    SettingsFields.download_chunk_size: int(download_chunk_size),
                    SettingsFields.presigned_url_ttl_seconds: int(
                        presigned_url_ttl_seconds
                    ),
                }
            )

    def action_cancel_screen(self):
        self.dismiss(
            {
                SettingsFields.theme: self.settings.theme,
                SettingsFields.group_by_access_credentials: self.settings.group_by_access_credentials,
            }
        )

    @on(Select.Changed)
    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select changed events."""
        if event.select.id == "theme":
            self.app.theme = event.value  # type: ignore[assignment]
