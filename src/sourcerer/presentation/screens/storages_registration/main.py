from dataclasses import dataclass
from enum import Enum

from dependency_injector.wiring import Provide
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.widgets import Label, Select

from sourcerer.infrastructure.access_credentials.services import CredentialsService
from sourcerer.presentation.di_container import DiContainer
from sourcerer.presentation.screens.shared.modal_screens import ExitBoundModalScreen
from sourcerer.presentation.screens.shared.widgets.button import Button
from sourcerer.presentation.screens.shared.widgets.labeled_input import LabeledInput


class ControlsEnum(Enum):
    CANCEL = "Cancel"
    CREATE = "Create"


@dataclass
class StorageEntry:
    name: str
    credentials_uuid: str


class StoragesRegistrationScreen(ExitBoundModalScreen):
    CSS_PATH = "styles.tcss"

    MAIN_CONTAINER_ID = "StoragesRegistrationScreen"
    SETTINGS_CONTAINER_ID = "settings"
    CREDENTIALS_SELECTOR_ID = "credentials_selector"

    PROVIDERS_NAME = "credentials"

    def __init__(
        self,
        credentials_service: CredentialsService = Provide[
            DiContainer.credentials_repository
        ],
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.credentials = credentials_service.list()
        self.auth_method = None

    def compose(self) -> ComposeResult:
        with Container(id=self.MAIN_CONTAINER_ID):
            with VerticalScroll(id=self.SETTINGS_CONTAINER_ID):
                yield LabeledInput(
                    "storage_name",
                    "Name:",
                    True,
                    multiline=False,
                    id="storage_name",
                )
                yield Label("* Credentials:", classes="form_label")
                yield Select(
                    options=((item.name, item.uuid) for item in self.credentials),
                    name=self.PROVIDERS_NAME,
                    id=self.CREDENTIALS_SELECTOR_ID,
                )
            with Horizontal(id="controls"):
                yield Button(ControlsEnum.CANCEL.value, name=ControlsEnum.CANCEL.name)
                yield Button(ControlsEnum.CREATE.value, name=ControlsEnum.CREATE.name)

    @on(Button.Click)
    def on_control_button_click(self, event: Button.Click):
        """
        Handle click events for control buttons on the registration screen.

        Depending on the action associated with the button click event, either dismiss
        the screen or gather authentication fields and then dismiss the screen with
        the collected data.

        Args:
            event (Button.Click): The click event containing the action to be performed.

        Flow:
            1. Check if the event.action is ControlsEnum.cancel.name. If true, dismiss the screen.
            2. If event.action is ControlsEnum.create.name, gather authentication fields. Dismiss the screen with the
               collected authentication fields.
        """
        if event.action == ControlsEnum.CANCEL.name:
            self.action_cancel_screen()
        elif event.action == ControlsEnum.CREATE.name:
            storage_name = self.query_one("#storage_name", LabeledInput).get().value
            if not storage_name:
                self.notify("Storage name is required", severity="error")
                return
            credentials_uuid = self.query_one(
                f"#{self.CREDENTIALS_SELECTOR_ID}", Select
            ).value
            if not credentials_uuid or credentials_uuid == Select.BLANK:
                self.notify("Credentials are required", severity="error")
                return

            self.dismiss(StorageEntry(storage_name, credentials_uuid))  # type: ignore
