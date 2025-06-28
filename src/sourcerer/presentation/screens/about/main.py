from dependency_injector.wiring import Provide
from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Static

from sourcerer.domain.package_meta.services import BasePackageMetaService
from sourcerer.presentation.di_container import DiContainer
from sourcerer.presentation.screens.shared.modal_screens import ExitBoundModalScreen
from sourcerer.presentation.screens.shared.widgets.button import Button


class AboutScreen(ExitBoundModalScreen):
    """Screen with a parameter."""

    CSS_PATH = "styles.tcss"

    def __init__(
        self,
        package_meta_service: BasePackageMetaService = Provide[
            DiContainer.package_meta_service
        ],
    ) -> None:
        super().__init__()
        self.package_meta_service = package_meta_service

    def compose(self) -> ComposeResult:
        package_meta = self.package_meta_service.get_package_meta()

        with Container():
            yield Static(Text("Sourcerer", style="bold cyan", justify="center"))
            yield Static(
                Text(
                    f"Version: {package_meta.version}"
                    f"{' (newer version is available)' if package_meta.has_available_update else ''}",
                    style="dim",
                    justify="center",
                )
            )
            yield Static(
                Text(
                    f"Platform: {package_meta.platform}", style="dim", justify="center"
                )
            )
            yield Static(
                Text(
                    f"System Version: {package_meta.system_version}",
                    style="dim",
                    justify="center",
                )
            )
            with Horizontal(id="controls"):
                yield Button("Close", name="close")

    @on(Button.Click)
    def on_button_clicked(self, event: Button.Click) -> None:
        """Handle button clicked events."""
        if event.action == "close":
            self.action_cancel_screen()
