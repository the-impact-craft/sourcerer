from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

from dependency_injector.wiring import Provide
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Horizontal, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Checkbox, Label

from sourcerer.domain.access_credentials.entities import Credentials
from sourcerer.domain.access_credentials.repositories import BaseCredentialsRepository
from sourcerer.infrastructure.access_credentials.services import CredentialsService
from sourcerer.presentation.di_container import DiContainer
from sourcerer.presentation.screens.provider_creds_list.messages.reload_credentials_request import (
    ReloadCredentialsRequest,
)
from sourcerer.presentation.screens.provider_creds_registration.main import (
    ProviderCredentialsEntry,
    ProviderCredsRegistrationScreen,
)
from sourcerer.presentation.screens.question.main import QuestionScreen
from sourcerer.presentation.screens.shared.modal_screens import (
    RefreshTriggerableModalScreen,
)
from sourcerer.presentation.screens.shared.widgets.button import Button


class ControlsEnum(Enum):
    CANCEL = "Cancel"


class ProviderCredentialsRow(Horizontal):
    @dataclass
    class ChangeActiveStatus(Message):
        uuid: str
        active: bool

    def __init__(
        self, row: Credentials, credentials_service: CredentialsService, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.row = row
        self.credentials_service = credentials_service

    def compose(self) -> ComposeResult:
        yield Checkbox(
            value=self.row.active, classes="credentials_active", name=self.row.uuid
        )
        yield Label(self.row.name, classes="credentials_name")
        yield Label(self.row.provider, classes="credentials_provider")
        yield Label(self.row.credentials_type, classes="credentials_auth_method")
        yield Button("❌", name="delete", classes="credentials_auth_delete")

    def on_mouse_move(self, _) -> None:
        """Change background color when hovered."""
        self.add_class("active")

    def on_leave(self, _) -> None:
        """Reset background color when mouse leaves."""
        self.remove_class("active")

    @on(Checkbox.Changed)
    def on_checkbox_change(self, event: Checkbox.Changed):
        """
        Handle checkbox state changes by updating the row's active status and posting a ChangeActiveStatus message.

        Args:
            event (Checkbox.Changed): The checkbox change event containing the new value.
        """
        self.row.active = event.value
        self.post_message(self.ChangeActiveStatus(self.row.uuid, self.row.active))

    @on(Button.Click)
    def on_delete_button_click(self, _: Button.Click):
        """
        Handle delete button click events by deleting the associated credentials using the credentials service.

        Args:
            _ (Button.Click): The button click event.
        """
        self.app.push_screen(
            QuestionScreen(
                f"Are you sure you want to delete {self.row.provider} {self.row.name} credentials?"
            ),
            callback=self.delete_callback,  # type: ignore
        )

    def delete_callback(self, result: bool):
        """
        Callback function to handle the result of the confirmation screen.

        Args:
            result (bool): True if the user confirmed, False otherwise.
        """
        if not result:
            return
        self.credentials_service.delete(self.row.uuid)
        self.post_message(ReloadCredentialsRequest())


class ProviderCredsListScreen(RefreshTriggerableModalScreen):
    CSS_PATH = "styles.tcss"

    MAIN_CONTAINER_ID = "ProviderCredsListScreen"
    SETTINGS_CONTAINER_ID = "settings"
    PROVIDER_SELECTOR_ID = "provider_selector"
    CREDENTIALS_TYPE_SELECTOR_ID = "credentials_type_select"
    CREDENTIALS_FIELDS_CONTAINER_ID = "credentials_fields_container"

    PROVIDERS_NAME = "providers"
    AUTH_METHODS_NAME = "auth_methods"

    BINDINGS: ClassVar[list[BindingType]] = [
        *RefreshTriggerableModalScreen.BINDINGS,
        Binding("ctrl+n", "add_credentials", "Add new credentials"),
    ]

    credentials_list = reactive([], recompose=True)

    def __init__(
        self,
        credentials_service: CredentialsService = Provide[
            DiContainer.credentials_service
        ],
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.credentials_service = credentials_service

    def compose(self) -> ComposeResult:
        with Container(id=self.MAIN_CONTAINER_ID):
            yield Container(
                Button(
                    "+Add new registration",
                    name="add_registration",
                    classes="add_registration_button",
                ),
                id="right-top",
            )
            with VerticalScroll(id=self.SETTINGS_CONTAINER_ID):
                with Horizontal():
                    yield Label("Active", classes="credentials_active")
                    yield Label("Name", classes="credentials_name")
                    yield Label("Provider", classes="credentials_provider")
                    yield Label("Auth method", classes="credentials_auth_method")
                    yield Label("Delete", classes="credentials_auth_delete")
                for row in self.credentials_list:
                    yield ProviderCredentialsRow(
                        row, self.credentials_service, classes="credentials_row"
                    )
            with Horizontal(id="controls"):
                yield Button(ControlsEnum.CANCEL.value, name=ControlsEnum.CANCEL.name)

    def on_compose(self):
        """
        Initialize the screen by refreshing the credentials list when the screen is composed.
        """
        self.refresh_credentials_list(set_refresh_flag=False)

    def refresh_credentials_list(self, set_refresh_flag: bool = True):
        """
        Refresh the credentials list by retrieving the latest credentials from the credentials service.
        """
        self.credentials_list = self.credentials_service.list()
        if set_refresh_flag:
            self._requires_storage_refresh = True

    def create_provider_creds_registration(
        self,
        credentials_entry: ProviderCredentialsEntry,
        credentials_repo: BaseCredentialsRepository = Provide[
            DiContainer.credentials_repository
        ],
    ):
        """
        Create a new provider credentials registration.

        Stores the provided credentials entry using its associated service and refreshes the credentials list.

        Args:
            credentials_entry (ProviderCredentialsEntry): The credentials entry to register.
            credentials_repo (BaseCredentialsRepository): The repository to store the credentials.
        """
        if not credentials_entry:
            return
        service = credentials_entry.cloud_storage_provider_credentials_service(
            credentials_repo
        )
        service.store(credentials_entry.name, credentials_entry.fields)
        self.refresh_credentials_list()

    @on(Button.Click)
    def on_control_button_click(self, event: Button.Click):
        """
        Handle click events for control buttons.

        Dismisses the screen if the cancel button is clicked, or opens the provider credentials registration screen if
        the add registration button is clicked.

        Args:
            event (Button.Click): The button click event.
        """
        if event.action == ControlsEnum.CANCEL.name:
            self.action_cancel_screen()
        if event.action == "add_registration":
            self.action_add_credentials()

    @on(ProviderCredentialsRow.ChangeActiveStatus)
    def on_change_active_status(self, event: ProviderCredentialsRow.ChangeActiveStatus):
        """
        Handle changes to the active status of a provider credentials row.

        Activates or deactivates the credentials based on the event, then refreshes the credentials list.

        Args:
            event (ProviderCredentialsRow.ChangeActiveStatus): Event containing the credentials UUID and new status.
        """
        if event.active:
            self.credentials_service.activate(event.uuid)
        else:
            self.credentials_service.deactivate(event.uuid)
        self.refresh_credentials_list()

    @on(ReloadCredentialsRequest)
    def on_reload_credentials_request(self, _: ReloadCredentialsRequest):
        """
        Handle reload credentials request events by refreshing the credentials list.

        Args:
            _ (ReloadCredentialsRequest): The reload credentials request event.
        """
        self.refresh_credentials_list()

    def action_add_credentials(self):
        self.app.push_screen(
            ProviderCredsRegistrationScreen(),
            callback=self.create_provider_creds_registration,  # type: ignore
        )
