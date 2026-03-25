import datetime
import uuid
from enum import Enum
from typing import ClassVar

from dependency_injector.wiring import Provide
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Horizontal, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Label

from sourcerer.domain.storage.entities import Storage
from sourcerer.infrastructure.access_credentials.services import CredentialsService
from sourcerer.infrastructure.storage.services import StoragesService
from sourcerer.presentation.di_container import DiContainer
from sourcerer.presentation.screens.question.main import QuestionScreen
from sourcerer.presentation.screens.shared.modal_screens import (
    RefreshTriggerableModalScreen,
)
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
    ADD_STORAGE = "Add Storage"


class StorageRow(Horizontal):
    def __init__(
        self, storage: Storage, storages_service: StoragesService, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.storage = storage
        self.storages_service = storages_service

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
        Handle delete button click events by showing a confirmation dialog for storage deletion.
        Args:
            _ (Button.Click): The button click event.
        """
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
        self.storages_service.delete(self.storage.uuid)
        self.post_message(ReloadStoragesRequest())


class StoragesListScreen(RefreshTriggerableModalScreen):
    CSS_PATH = "styles.tcss"

    MAIN_CONTAINER_ID = "StoragesListScreen"
    SETTINGS_CONTAINER_ID = "settings"

    BINDINGS: ClassVar[list[BindingType]] = [
        *RefreshTriggerableModalScreen.BINDINGS,
        Binding("ctrl+n", "add_storage", "Add new storage"),
    ]

    storages_list = reactive([], recompose=True)

    def __init__(
        self,
        credentials_service: CredentialsService = Provide[
            DiContainer.credentials_service
        ],
        storages_service: StoragesService = Provide[DiContainer.storages_service],
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.storage_service = storages_service
        self.credentials_service = credentials_service

    def compose(self) -> ComposeResult:
        with Container(id=self.MAIN_CONTAINER_ID):
            yield Container(
                Button(
                    "+Add new storage",
                    name=ControlsEnum.ADD_STORAGE.name,
                    classes="add_storage_button",
                    id="add_storage_button",
                ),
                id="right-top",
            )
            with VerticalScroll(id=self.SETTINGS_CONTAINER_ID):
                with Horizontal():
                    yield Label("Storage Name", classes="storage_name")
                    yield Label("Credentials Name", classes="credentials_name")
                    yield Label("Delete", classes="storage_delete")
                for storage in self.storages_list:
                    yield StorageRow(storage, self.storage_service)
            with Horizontal(id="controls"):
                yield Button(ControlsEnum.CANCEL.value, name=ControlsEnum.CANCEL.name)

    def on_compose(self):
        """
        Initialize the screen by refreshing the credentials list when the screen is composed.
        """
        self.refresh_storages_list(set_refresh_flag=False)

    def refresh_storages_list(self, set_refresh_flag: bool = True):
        """
        Refresh the storages list by retrieving the latest storages from the storage service.
        """
        self.storages_list = self.storage_service.list()
        if set_refresh_flag:
            self._requires_storage_refresh = True

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
            self.action_cancel_screen()
        if event.action == ControlsEnum.ADD_STORAGE.name:
            self.action_add_storage()

    def create_storage_entry(self, storage: StorageEntry | None):
        """
        Create a new storage entry.

        Creates a new storage entry using the provided data and refreshes the storage list.
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

    def action_add_storage(self):
        self.app.push_screen(
            StoragesRegistrationScreen(),
            callback=self.create_storage_entry,  # type: ignore
        )
