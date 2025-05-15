from dataclasses import dataclass
from enum import Enum

from dependency_injector.wiring import Provide
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Label, Select

from sourcerer.domain.access_credentials.services import (
    AuthField,
    BaseAccessCredentialsService,
)
from sourcerer.infrastructure.access_credentials.exceptions import (
    MissingAuthFieldsError,
)
from sourcerer.presentation.di_container import DiContainer
from sourcerer.presentation.screens.shared.widgets.button import Button
from sourcerer.presentation.screens.shared.widgets.labeled_input import LabeledInput


class ControlsEnum(Enum):
    CANCEL = "Cancel"
    CREATE = "Create"


@dataclass
class ProviderCredentialsEntry:
    name: str
    cloud_storage_provider_credentials_service: type[BaseAccessCredentialsService]
    fields: dict[str, str]


class ProviderCredsRegistrationScreen(ModalScreen):
    CSS_PATH = "styles.tcss"

    MAIN_CONTAINER_ID = "ProviderCredsRegistrationScreen"
    SETTINGS_CONTAINER_ID = "settings"
    PROVIDER_SELECTOR_ID = "provider_selector"
    CREDENTIALS_TYPE_SELECTOR_ID = "credentials_type_select"
    CREDENTIALS_FIELDS_CONTAINER_ID = "credentials_fields_container"

    PROVIDERS_NAME = "providers"
    AUTH_METHODS_NAME = "auth_methods"

    def __init__(
        self,
        *args,
        credentials_type_registry=Provide[
            DiContainer.config.access_credential_method_registry
        ],
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.provider_credentials_settings = credentials_type_registry.get()
        self.auth_method = None

    def compose(self) -> ComposeResult:
        with Container(id=self.MAIN_CONTAINER_ID):
            with VerticalScroll(id=self.SETTINGS_CONTAINER_ID):
                yield LabeledInput(
                    "Custom credentials label (suggest to set it unique)",
                    "Name:",
                    True,
                    multiline=False,
                    id="auth_name",
                )
                yield Label("* Provider:", classes="form_label")
                yield Select(
                    options=(
                        (provider, provider)
                        for provider in self.provider_credentials_settings
                    ),
                    name=self.PROVIDERS_NAME,
                    id=self.PROVIDER_SELECTOR_ID,
                )
            with Horizontal(id="controls"):
                yield Button(ControlsEnum.CANCEL.value, name=ControlsEnum.CANCEL.name)
                yield Button(ControlsEnum.CREATE.value, name=ControlsEnum.CREATE.name)

    async def _process_selected_provider(self, provider: str) -> None:
        """
        Processes the selected provider by removing any existing credential type selector
        and retrieving the available authentication methods for the provider. If multiple
        authentication methods are available, a selection dropdown is displayed. If only
        one method is available, it is set and its fields are mounted.

        Args:
            provider (str): The name of the selected provider.

        Returns:
            None

        Flow:
            1. Remove any existing credential type selector from the settings container.
            2. Retrieve authentication methods for the given provider.
            3. If multiple methods exist, display a dropdown for selection.
            4. If only one method exists, set it and mount its fields.
        """
        # Remove existing credential type selector
        await self.query_one(f"#{self.SETTINGS_CONTAINER_ID}").remove_children(
            f"#{self.CREDENTIALS_TYPE_SELECTOR_ID}"
        )

        # Retrieve authentication methods for the selected provider
        auth_methods = self.provider_credentials_settings.get(provider)
        if not auth_methods:
            return

        # If multiple authentication methods exist, display a selection dropdown
        if len(auth_methods) > 1:
            options = [(auth_type, auth_type) for auth_type in auth_methods]
            await self.query_one(f"#{self.SETTINGS_CONTAINER_ID}").mount(
                Container(
                    Label("Auth method:", classes="form_label"),
                    Select(options=options, name=self.AUTH_METHODS_NAME),
                    id=self.CREDENTIALS_TYPE_SELECTOR_ID,
                )
            )
            return

        # If only one authentication method exists, set it and mount its fields
        self.auth_method = next(iter(auth_methods.values()))
        cls: BaseAccessCredentialsService = self.auth_method
        await self._mount_credentials_fields(cls.auth_fields())

    @on(Select.Changed)
    async def select_changed(self, event: Select.Changed) -> None:
        """
        Handle changes in the selection of provider or authentication method.

        This method is triggered when a selection change event occurs in the
        provider or authentication method dropdowns. It clears existing credential
        fields and processes the selection based on the control that triggered the
        event.

        Args:
            event (Select.Changed): The event object containing details about the
            selection change.
        Flow:

            1. Clear existing credential fields.
            2. Process based on the control that triggered the event:
                - If the event is triggered by the provider dropdown, process the selected provider.
                - If the event is triggered by the authentication method dropdown, process the selected provider
                  and authentication method
        """
        # Clear existing credential fields
        await self.query_one(f"#{self.SETTINGS_CONTAINER_ID}").remove_children(
            f"#{self.CREDENTIALS_FIELDS_CONTAINER_ID}"
        )

        # Process based on the control that triggered the event
        if event.control.name == self.PROVIDERS_NAME:
            await self._process_selected_provider(str(event.value))
        elif event.control.name == self.AUTH_METHODS_NAME:
            provider = self.query_one(f"#{self.PROVIDER_SELECTOR_ID}").selection  # type: ignore
            await self._process_selected_provider_auth_method(
                provider, str(event.value)
            )

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
            self.dismiss()
        elif event.action == ControlsEnum.CREATE.name:
            if not self.auth_method:
                self.notify("Please select provider and auth method", severity="error")
                return

            auth_fields = self._get_auth_fields()
            if not auth_fields:
                self.notify("Please select provider and auth method", severity="error")
                return

            try:
                self.auth_method.validate_auth_fields_values(auth_fields.fields)
            except MissingAuthFieldsError as e:
                self.notify(str(e), severity="error")
                return

            self.dismiss(auth_fields)

    def _get_auth_fields(self) -> ProviderCredentialsEntry | None:
        """
        Collects authentication fields from the UI and returns a ProviderCredentialsEntry.

        Returns:
            ProviderCredentialsEntry: An object containing the authentication name, method, and fields.
        """
        if not self.auth_method:
            return

        fields = {
            input_field.get().name: input_field.get().value
            for input_field in self.query_one(
                f"#{self.CREDENTIALS_FIELDS_CONTAINER_ID}"
            ).children
            if isinstance(input_field, LabeledInput) and input_field.get().value
        }

        auth_name = self.query_one("#auth_name").get().value or "default"  # type: ignore

        return ProviderCredentialsEntry(
            name=auth_name,
            cloud_storage_provider_credentials_service=self.auth_method,
            fields=fields,
        )

    async def _process_selected_provider_auth_method(self, provider, method):
        """
        Process the selected authentication method for a given provider.

        This method retrieves the authentication class for the specified provider
        and method, sets it as the current authentication method, and mounts its
        credential fields if available.

        Args:
            provider: The name of the provider.
            method: The authentication method to be processed.

        Returns:
            None

        Flow:
            1. Retrieve the authentication class for the specified provider and method.
            2. Set the authentication class as the current authentication method.
            3. Mount the credential fields for the selected authentication method.
        """
        provider_auth_class = self.provider_credentials_settings.get(provider, {}).get(
            method
        )
        if provider_auth_class:
            self.auth_method = provider_auth_class
            await self._mount_credentials_fields(provider_auth_class.auth_fields())

    async def _mount_credentials_fields(self, fields: list[AuthField]) -> None:
        """
        Mounts a container of labeled input fields for credentials onto the settings container
        and sets focus on the first input field.

        Args:
            fields (list[AuthField]): A list of AuthField objects containing key, label, and required attributes.

        Returns:
            None

        Flow:
            1. Create a container of labeled input fields for the provided credentials.
            2. Mount the container onto the settings container.
            3. Set focus on the first input field in the container.
        """
        container = Container(
            *(
                LabeledInput(field.key, field.label, field.required, field.multiline)
                for field in fields
            ),
            id=self.CREDENTIALS_FIELDS_CONTAINER_ID,
        )
        await self.query_one(f"#{self.SETTINGS_CONTAINER_ID}").mount(container)
        self.query_one(f"#{self.CREDENTIALS_FIELDS_CONTAINER_ID}").query_one(
            ".form_input"
        ).focus()
