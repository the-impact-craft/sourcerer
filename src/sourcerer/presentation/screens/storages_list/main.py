import datetime
import uuid
from enum import Enum

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Label

from sourcerer.domain.storage.entities import Storage
from sourcerer.infrastructure.access_credentials.services import CredentialsService
from sourcerer.infrastructure.storage.services import StoragesService
from sourcerer.presentation.screens.question.main import QuestionScreen
from sourcerer.presentation.screens.shared.widgets.button import Button
from sourcerer.presentation.screens.storages_list.messages.reload_storages_request import (
    ReloadStoragesRequest,
)
from sourcerer.presentation.screens.storages_registration.main import (
    StorageEntry,
    StoragesRegistrationScreen,
)


class ControlsEnum(Enum):
    CANCEL = "Cancel"


class StorageRow(Horizontal):
    def __init__(self, storage: Storage, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.storage = storage

    def compose(self):
        yield Label(self.storage.name, classes="storage_name")
        yield Label(self.storage.credentials_name or "🚫", classes="credentials_name")
        yield Button(
            "❌",
            name="delete_storage",
            classes="storage_delete",
        )

    @on(Button.Click)
    def on_button_click(self, _: Button.Click):
        """
        Handle delete button click events by deleting the associated credentials using the credentials service.

        Args:
            _ (Button.Click): The button click event.
        """
        self.notify("delete_storage")
        self.app.push_screen(
            QuestionScreen(
                f"Are you sure you want to delete {self.storage.credentials_name} {self.storage.name} storage?"
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
        credentials_service = StoragesService()
        credentials_service.delete(self.storage.uuid)
        self.post_message(ReloadStoragesRequest())


class StoragesListScreen(ModalScreen):
    CSS_PATH = "styles.tcss"

    MAIN_CONTAINER_ID = "StoragesListScreen"
    SETTINGS_CONTAINER_ID = "settings"
    PROVIDER_SELECTOR_ID = "provider_selector"
    CREDENTIALS_TYPE_SELECTOR_ID = "credentials_type_select"
    CREDENTIALS_FIELDS_CONTAINER_ID = "credentials_fields_container"

    PROVIDERS_NAME = "providers"
    AUTH_METHODS_NAME = "auth_methods"

    storages_list = reactive([], recompose=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.storage_service = StoragesService()
        self.credentials_service = CredentialsService()

    def compose(self) -> ComposeResult:
        with Container(id=self.MAIN_CONTAINER_ID):
            yield Container(
                Button(
                    "+Add new storage",
                    name="add_storage",
                    classes="add_storage_button",
                ),
                id="right-top",
            )
            with VerticalScroll(id=self.SETTINGS_CONTAINER_ID):
                with Horizontal():
                    yield Label("Storage Name", classes="storage_name")
                    yield Label("Credentials Name", classes="credentials_name")
                    yield Label("Delete", classes="storage_delete")
                for storage in self.storages_list:
                    yield StorageRow(storage)
            with Horizontal(id="controls"):
                yield Button(ControlsEnum.CANCEL.value, name=ControlsEnum.CANCEL.name)

    def on_compose(self):
        """
        Initialize the screen by refreshing the credentials list when the screen is composed.
        """
        self.refresh_storages_list()

    def refresh_storages_list(self):
        """
        Refresh the storages list by retrieving the latest storages from the storage service.
        """
        self.storages_list = self.storage_service.list()

    @on(ReloadStoragesRequest)
    def on_reload_storages_request(self, _: ReloadStoragesRequest):
        """
        Handle the reload storages request by refreshing the storages list.

        Args:
            _: ReloadStoragesRequest: The reload storages request message.
        """
        self.refresh_storages_list()

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
            self.dismiss()
        if event.action == "add_storage":
            self.app.push_screen(
                StoragesRegistrationScreen(),
                callback=self.create_provider_creds_registration,  # type: ignore
            )

    def create_provider_creds_registration(self, storage: StorageEntry | None):
        """
        Create a new provider credentials registration.

        Stores the provided credentials entry using its associated service and refreshes the credentials list.
        """
        if storage is None:
            return

        credentials = self.credentials_service.get(storage.credentials_uuid)
        if not credentials:
            self.notify("Credentials not found", severity="error")
            return
        self.storage_service.create(
            Storage(
                uuid=str(uuid.uuid4()),
                name=storage.name,
                credentials_id=credentials.id,
                date_created=datetime.datetime.now(),
            )
        )
        self.refresh_storages_list()
