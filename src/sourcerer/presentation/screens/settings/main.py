from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Checkbox, Rule, Select, Static

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
            with Horizontal(id="controls"):
                yield Button("Save", name="save")
                yield Button("Close", name="close")

    @on(Button.Click)
    def on_button_clicked(self, event: Button.Click) -> None:
        """Handle button clicked events."""
        if event.action == "close":
            self.action_cancel_screen()
        elif event.action == "save":
            self.dismiss(
                {
                    SettingsFields.theme: self.query_one("Select#theme", Select).value,
                    SettingsFields.group_by_access_credentials: self.query_one(
                        Checkbox
                    ).value,
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
