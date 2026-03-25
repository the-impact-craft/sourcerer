import contextlib
import time
import traceback
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import ClassVar

from dependency_injector.wiring import Provide
from textual import on, work
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding, BindingType
from textual.containers import Horizontal
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Footer

from sourcerer.domain.package_meta.services import BasePackageMetaService
from sourcerer.domain.settings.entities import SettingsFields
from sourcerer.domain.storage_provider.entities import Storage
from sourcerer.infrastructure.access_credentials.services import CredentialsService
from sourcerer.infrastructure.settings.services import SettingsService
from sourcerer.infrastructure.storage_provider.exceptions import (
    ListStorageItemsError,
    PresignedUrlError,
)
from sourcerer.infrastructure.utils import generate_uuid
from sourcerer.presentation.di_container import DiContainer
from sourcerer.presentation.screens.about.main import AboutScreen
from sourcerer.presentation.screens.critical_error.main import CriticalErrorScreen
from sourcerer.presentation.screens.file_system_finder.main import (
    FileSystemNavigationModal,
)
from sourcerer.presentation.screens.main.messages.delete_request import DeleteRequest
from sourcerer.presentation.screens.main.messages.download_request import (
    DownloadRequest,
)
from sourcerer.presentation.screens.main.messages.presign_url_request import (
    PresignedUrlRequest,
)
from sourcerer.presentation.screens.main.messages.preview_request import PreviewRequest
from sourcerer.presentation.screens.main.messages.refresh_storages_list_request import (
    RefreshStoragesListRequest,
)
from sourcerer.presentation.screens.main.messages.select_storage_item import (
    SelectStorageItem,
)
from sourcerer.presentation.screens.main.messages.uncheck_files_request import (
    UncheckFilesRequest,
)
from sourcerer.presentation.screens.main.messages.upload_request import UploadRequest
from sourcerer.presentation.screens.main.mixins.resize_containers_watcher_mixin import (
    ResizeContainersWatcherMixin,
)
from sourcerer.presentation.screens.main.widgets.resizing_rule import ResizingRule
from sourcerer.presentation.screens.main.widgets.storage_content import (
    FileItem,
    StorageContentContainer,
)
from sourcerer.presentation.screens.main.widgets.storage_list_sidebar import (
    StorageListSidebar,
)
from sourcerer.presentation.screens.preview_content.main import PreviewContentScreen
from sourcerer.presentation.screens.provider_creds_list.main import (
    ProviderCredsListScreen,
)
from sourcerer.presentation.screens.question.main import QuestionScreen
from sourcerer.presentation.screens.settings.main import SettingsScreen
from sourcerer.presentation.screens.storage_action_progress.main import (
    DeleteKey,
    DownloadKey,
    StorageActionProgressScreen,
    UploadKey,
)
from sourcerer.presentation.screens.storages_list.main import StoragesListScreen
from sourcerer.presentation.settings import KeyBindings
from sourcerer.presentation.themes.github_dark import github_dark_theme
from sourcerer.presentation.utils import (
    get_provider_service_by_access_credentials,
    get_provider_service_by_access_uuid,
)
from sourcerer.settings import MAX_PARALLEL_STORAGE_LIST_OPERATIONS


class Sourcerer(App, ResizeContainersWatcherMixin):
    """
    A Textual application for managing cloud storage credentials and content.

    This application provides a user interface to list and manage cloud storage
    credentials, view storage content, and handle storage item selection. It
    integrates with various cloud storage providers and supports asynchronous
    operations for fetching and displaying storage data.

    Attributes:
        CSS_PATH (str): Path to the CSS file for styling the application.
        BINDINGS (list): Key bindings for application actions.
        is_storage_list_loading (reactive): Reactive attribute indicating if the
            storage list is currently loading.

    Methods:
        compose() -> ComposeResult: Composes the UI layout with storage list and
            content areas.
        on_mount(): Initializes the application theme and storage list on mount.
        action_credentials_list(): Opens the credentials list screen and refreshes
            storages.
        refresh_storages(*args, **kwargs): Refreshes the storage list by clearing
            and reinitializing it.
        init_storages_list() -> None: Asynchronously initializes the storage list
            by fetching and displaying storages.
        on_select_storage_item(event: SelectStorageItem): Handles storage item
            selection and updates storage content.
    """

    CSS_PATH = "styles.tcss"
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("ctrl+r", "registrations", "Registrations list"),
        Binding("ctrl+l", "storages", "Storages list"),
        Binding("ctrl+f", "find", show=False),
        Binding("ctrl+s", "settings", "Settings"),
        Binding("ctrl+a", "about", "About"),
        Binding(
            KeyBindings.ARROW_LEFT.value, "focus_sidebar", "Focus sidebar", show=False
        ),
        Binding(
            KeyBindings.ARROW_RIGHT.value, "focus_content", "Focus content", show=False
        ),
    ]
    is_storage_list_loading = reactive(False, recompose=True)

    def __init__(
        self,
        settings_service: SettingsService = Provide[DiContainer.settings_service],
        credentials_service: CredentialsService = Provide[
            DiContainer.credentials_service
        ],
        package_meta_service: BasePackageMetaService = Provide[
            DiContainer.package_meta_service
        ],
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.settings_service = settings_service
        self.credentials_service = credentials_service
        self.package_meta_service = package_meta_service
        self.settings = self.settings_service.load_settings()
        self.storage_list_sidebar = StorageListSidebar(
            self.settings.group_by_access_credentials, id="storage_list_sidebar"
        )
        self.storage_content = StorageContentContainer(id="storage_content_container")
        self.load_percentage = 0
        self.active_resizing_rule: ResizingRule | None = None

    def compose(self) -> ComposeResult:
        with Horizontal(id="main"):
            yield self.storage_list_sidebar
            yield ResizingRule(
                id="storage_list_sidebar_container",
                orientation="vertical",
                classes="resize-handle",
                prev_component_id=self.storage_list_sidebar.id,
                next_component_id=self.storage_content.id,
            )
            yield self.storage_content
        yield Footer()

    def _handle_exception(self, error: Exception) -> None:
        self.push_screen(CriticalErrorScreen(str(error), traceback.format_exc()))

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        yield SystemCommand(
            "Quit the application",
            "Quit the application as soon as possible",
            self.action_quit,
        )

        if screen.query("HelpPanel"):
            yield SystemCommand(
                "Hide keys and help panel",
                "Hide the keys and widget help panel",
                self.action_hide_help_panel,
            )
        else:
            yield SystemCommand(
                "Show keys and help panel",
                "Show help for the focused widget and a summary of available keys",
                self.action_show_help_panel,
            )
        yield SystemCommand(
            "Save screenshot",
            "Save an SVG 'screenshot' of the current screen",
            self.deliver_screenshot,
        )
        yield SystemCommand("About", "About sourcerer", self.action_about)
        yield SystemCommand("Settings", "Sourcerer settings", self.action_settings)

    def on_mount(self):
        """
        Initializes the application theme and storage list on mount.
        """

        self.register_theme(github_dark_theme)  # pyright: ignore [reportArgumentType]
        if self.settings.theme in self._registered_themes:
            self.theme = self.settings.theme

        package_meta = self.package_meta_service.get_package_meta()
        if package_meta.has_available_update:
            self.notify(
                f"Sourcerer {package_meta.version} "
                f"is running while {package_meta.latest_version} is available",
                severity="warning",
            )
        self.init_storages_list()

    def action_find(self):
        """
        Focus search input.
        """
        with contextlib.suppress(NoMatches):
            self.query_one(f"#{self.storage_content.search_input_id}").focus()

    def action_focus_content(self):
        """
        Focuses the storage content container.
        """
        self.storage_content.focus()

    def action_focus_sidebar(self):
        """
        Focuses the storage list sidebar.
        """
        self.storage_list_sidebar.focus()

    def action_registrations(self):
        """
        Opens the provider credentials list screen and refreshes the storage list.
        This method is triggered by the key binding "ctrl+r" and allows the user
        to manage their cloud storage credentials. It pushes the
        ProviderCredsListScreen to the application stack and sets a callback
        to refresh the storage list after the screen is closed.
        This method is typically used to allow users to add their
        cloud storage credentials, which will then be reflected in the storage
        """
        self.app.push_screen(
            ProviderCredsListScreen(), callback=self.modal_screen_callback
        )

    def action_settings(self):
        """
        Opens the settings screen.
        This method is triggered by the key binding "ctrl+s" and allows the user
        to modify application settings such as theme and grouping of storage items.
        It retrieves the current settings from the settings service and pushes
        the SettingsScreen to the application stack. A callback is set to handle
        the settings changes when the screen is closed.
        """
        settings = self.settings_service.load_settings()
        self.app.push_screen(SettingsScreen(settings), callback=self.settings_callback)

    def action_storages(self):
        self.app.push_screen(StoragesListScreen(), callback=self.modal_screen_callback)

    def action_about(self):
        self.push_screen(AboutScreen())

    def settings_callback(self, settings: dict | None):
        default_settings = self.settings_service.load_settings()
        if settings is None:
            self.app.theme = default_settings.theme
            return
        self.app.theme = settings[SettingsFields.theme]
        if (theme := settings.get(SettingsFields.theme)) != default_settings.theme:
            self.settings_service.set_setting(SettingsFields.theme, theme)  # type: ignore

        if (
            group_by := settings.get(SettingsFields.group_by_access_credentials)
        ) != default_settings.group_by_access_credentials:
            self.settings_service.set_setting(SettingsFields.group_by_access_credentials, group_by)  # type: ignore
            self.storage_list_sidebar.groupby_access_credentials = group_by  # type: ignore

        if upload_chunk_size := settings.get(SettingsFields.upload_chunk_size):
            self.settings_service.set_setting(
                SettingsFields.upload_chunk_size, upload_chunk_size
            )

        if download_chunk_size := settings.get(SettingsFields.download_chunk_size):
            self.settings_service.set_setting(
                SettingsFields.download_chunk_size, download_chunk_size
            )

        if presigned_url_ttl := settings.get(SettingsFields.presigned_url_ttl_seconds):
            self.settings_service.set_setting(
                SettingsFields.presigned_url_ttl_seconds, presigned_url_ttl
            )

        self.settings = self.settings_service.load_settings()

    def modal_screen_callback(self, requires_storage_refresh: bool | None = True):
        """
        Callback for modal screens to refresh the storage list if required.

        This method is called when a modal screen is closed. If the
        `requires_storage_refresh` flag is set to True, it refreshes the
        storage list by calling the `refresh_storages` method.
        """
        if requires_storage_refresh:
            self.refresh_storages()

    def refresh_storages(self, *args, **kwargs):
        """
        Refreshes the storage list by clearing the current storages and
        reinitializing the storages list. This method is typically used
        to update the storage list after changes in credentials or storage
        configurations.
        """
        self.storage_list_sidebar.storages = {}
        self.storage_list_sidebar.last_update_timestamp = time.time()
        self.init_storages_list()

    @work(thread=True)
    async def init_storages_list(self) -> None:
        """
        Initializes the list of storages by fetching active access credentials
        and retrieving storages for each credential. Updates the storage list
        sidebar with the retrieved storages. Notifies the user in case of errors.

        This method is asynchronous and should be awaited.

        Flow:
            1. Fetch active access credentials using self.credentials_service.list.
            2. If no credentials are found, exit the method.
            3. For each credential, retrieve the corresponding provider service.
            4. Attempt to list storages using the provider service.
            5. Update the storage_list_sidebar with the retrieved storages.
            6. Handle exceptions by printing an error message and notifying the user.
        """
        self.reset_storage_content()
        access_credentials = self.credentials_service.list(active_only=True)

        if not access_credentials:
            return

        self.storage_list_sidebar.is_loading = True

        with ThreadPoolExecutor(
            max_workers=MAX_PARALLEL_STORAGE_LIST_OPERATIONS
        ) as executor:
            futures = [
                executor.submit(self._load_storages, credentials)
                for credentials in access_credentials
            ]

            for future in futures:
                future.result()
        self.storage_list_sidebar.is_loading = False

    @on(SelectStorageItem)
    def on_select_storage_item(self, event: SelectStorageItem):
        """
        Handles the selection of a storage item by updating the storage content
        with the selected item's details and retrieving its contents.

        Args:
            event (SelectStorageItem): The event containing details of the selected storage item.

        Flow:
            1. Update storage_content with the path, storage name, and access credentials UUID from the event.
            2. Retrieve the provider service using the access credentials UUID.
            3. If the provider service is available, attempt to list storage items.
            4. Update storage_content with the retrieved storage items.
            5. Notify the user if an error occurs during the retrieval process.
        """
        self.refresh_storage_content(
            event.access_credentials_uuid,
            event.name,
            event.path,
            event.prefix,
            event.focus_content,
        )

    @on(UploadRequest)
    def on_upload_request(self, event: UploadRequest):
        """
        Handles file upload requests by opening a file system navigation modal.

        This method is triggered when an UploadRequest event is received. It opens
        a file system navigation modal to allow the user to select a file or directory
        to upload, then calls the _upload_file method with the selected source path.

        Args:
            event (UploadRequest): The upload request event containing storage details
        """
        self.push_screen(
            FileSystemNavigationModal(),
            callback=lambda src: self._upload_file(
                event.access_credentials_uuid, event.storage, event.path, src  # type: ignore
            ),
        )

    @on(DownloadRequest)
    def on_download_request(self, event: DownloadRequest):
        """
        Handles file download requests by opening a storage action progress screen.

        This method is triggered when a DownloadRequest event is received. It creates
        a StorageActionProgressScreen to track and display the progress of the download
        operation for the selected files.

        Args:
            event (DownloadRequest): The download request event containing file details
        """
        self.push_screen(
            StorageActionProgressScreen(
                storage_name=event.storage_name,
                provider_service=get_provider_service_by_access_uuid(
                    event.access_credentials_uuid,
                    self.credentials_service,
                    self.settings,
                ),
                path=event.path,
                keys=[
                    DownloadKey(display_name=key, uuid=generate_uuid(), path=key)
                    for key in event.keys
                ],
                action="download",
            ),
            callback=lambda x: self.after_bulk_operation_callback(
                event.access_credentials_uuid, event.storage_name, event.path
            ),
        )

    @on(DeleteRequest)
    def on_delete_request(self, event: DeleteRequest):
        """
        Handles file deletion requests by opening a storage action progress screen.

        This method is triggered when a DeleteRequest event is received. It creates
        a StorageActionProgressScreen to track and display the progress of the delete
        operation for the selected files.

        Args:
            event (DeleteRequest): The delete request event containing file details
        """

        def trigger_delete_action(process_delete_request):
            if not process_delete_request:
                return
            self.push_screen(
                StorageActionProgressScreen(
                    storage_name=event.storage_name,
                    provider_service=get_provider_service_by_access_uuid(
                        event.access_credentials_uuid,
                        self.credentials_service,
                        self.settings,
                    ),
                    path=event.path,
                    keys=[
                        DeleteKey(display_name=key, uuid=generate_uuid(), path=key)
                        for key in event.keys
                    ],
                    action="delete",
                ),
                callback=lambda x: self.after_bulk_operation_callback(
                    event.access_credentials_uuid, event.storage_name, event.path
                ),
            )

        self.app.push_screen(
            QuestionScreen(f"Are you sure you want to delete {len(event.keys)} keys?"),
            callback=trigger_delete_action,
        )

    def after_bulk_operation_callback(
        self, access_credentials_uuid, storage_name, path
    ):
        """
        Callback method executed after bulk operations (download, upload, delete) complete.

        This method resets the storage content display and refreshes it with the latest
        content from the specified storage path after a bulk operation completes.

        Args:
            access_credentials_uuid (str): UUID of the access credentials to use
            storage_name (str): Name of the storage to display
            path (str): Path within the storage to display
        """
        self.reset_storage_content()
        self.refresh_storage_content(access_credentials_uuid, storage_name, path)

    @on(UncheckFilesRequest)
    def uncheck_files_request(self, event: UncheckFilesRequest):
        """
        Handles requests to uncheck selected files in the storage content view.

        This method is triggered when an UncheckFilesRequest event is received.
        It unchecks all files specified in the event and clears the selected files
        tracking in the storage content widget.

        Args:
            event (UncheckFilesRequest): The uncheck request event containing file keys
        """
        for key_uuid in event.keys:
            file_item = self.query_one(f"#{key_uuid}", FileItem)
            file_item.uncheck()
        self.storage_content.selected_files = set()
        self.storage_content.selected_files_n = 0

    @on(PreviewRequest)
    def on_preview_request(self, event: PreviewRequest):
        """
        Handles requests to preview file content.

        This method is triggered when a PreviewRequest event is received. It attempts
        to read the content of the specified file using the provider service and
        displays it in a PreviewContentScreen if successful.

        Args:
            event (PreviewRequest): The preview request event containing file details

        Note:
            If an error occurs while reading the file content, a notification is shown
            to the user and the preview is not displayed.
        """
        self.push_screen(
            PreviewContentScreen(
                storage_name=event.storage_name,
                key=event.path,
                file_size=event.size,
                access_credentials_uuid=event.access_credentials_uuid,
                settings=self.settings,
            )
        )

    @on(PresignedUrlRequest)
    def on_presigned_url_request(self, event: PresignedUrlRequest):
        provider_service = get_provider_service_by_access_uuid(
            event.access_credentials_uuid,
            self.credentials_service,
            self.settings,
        )
        if provider_service is None:
            self.notify(f"Could not create presigned url for {event.path}")
            return
        try:
            url = provider_service.get_download_presigned_url(
                event.storage_name, event.path
            )
        except PresignedUrlError:
            self.notify(f"Could not create presigned url for {event.path}")
            return

        self.copy_to_clipboard(url)
        self.notify("🔗Presigned url has been copied to clipboard")

    @on(RefreshStoragesListRequest)
    def on_refresh_storages_list_request(self, _: RefreshStoragesListRequest):
        """
        Handles requests to refresh the storage list.

        This method is triggered when a RefreshStoragesListRequest event is received.
        It refreshes the storage list if the storage list sidebar is not currently
        loading.

        Args:
            _ (RefreshStoragesListRequest): The refresh request event
        """
        if self.storage_list_sidebar.is_loading:
            return
        self.refresh_storages()

    def reset_storage_content(self):
        """
        Resets the storage content attributes to their default state.

        This method clears the current storage path, storage name, search prefix,
        storage content, and access credentials UUID, effectively resetting the
        storage content to an uninitialized state.
        """
        self.storage_content.path = None
        self.storage_content.storage = None
        self.storage_content.search_prefix = None
        self.storage_content.storage_content = None
        self.storage_content.access_credentials_uuid = ""
        self.storage_content.selected_files = set()
        self.storage_content.selected_files_n = 0
        self.uncheck_files_request(UncheckFilesRequest(keys=[]))

    def refresh_storage_content(
        self,
        access_credentials_uuid,
        storage_name,
        path,
        prefix=None,
        focus_content=False,
    ):
        """
        Refreshes the storage content display with items from the specified storage path.

        This method updates the storage content widget with items from the specified
        storage path and provider. It handles retrieving the storage items using the
        provider service and updating the UI accordingly.

        Args:
            access_credentials_uuid (str): UUID of the access credentials to use
            storage_name (str): Name of the storage to display
            path (str): Path within the storage to display
            prefix (str, optional): Filter prefix for storage items. Defaults to None.

        Note:
            If an error occurs while retrieving storage items, a notification is shown
            to the user and the storage content remains unchanged.
        """
        self.storage_content.path = path.strip("/") if path else path
        self.storage_content.storage = storage_name
        self.storage_content.access_credentials_uuid = access_credentials_uuid
        self.storage_content.search_prefix = prefix or ""
        self.storage_content.storage_content = None
        self.storage_content.selected_files = set()
        self.storage_content.selected_files_n = 0
        self.storage_content.focus_content = focus_content

        provider_service = get_provider_service_by_access_uuid(
            access_credentials_uuid,
            self.credentials_service,
            self.settings,
        )

        if not provider_service:
            self.notify_error("Could not extract storage content")
            return
        params = {"storage": storage_name, "path": path or "", "prefix": prefix or ""}
        try:
            self.storage_content.storage_content = provider_service.list_storage_items(
                **params
            )
        except ListStorageItemsError as e:
            self.notify_error(f"""Could not extract storage content \n{e}""")

    def _upload_file(
        self,
        access_credentials_uuid: str,
        storage_name: str,
        path: str,
        source_path: Path,
    ) -> None:
        """
        Uploads a file to the specified storage.

        This method handles the upload of a file to a cloud storage provider.
        It creates an upload key, gets the provider service, and pushes a
        progress screen to handle the upload operation.

        Args:
            access_credentials_uuid (str): The UUID of the access credentials used for authentication.
            storage_name (str): The name of the storage where the file will be uploaded.
            path (str): The destination path within the storage.
            source_path (Path): The local path of the file to be uploaded.
            file_system_service (FileSystemService, optional): Service for file system operations.
                Defaults to Provide[DiContainer.file_system_service].

        Returns:
            None

        Note:
            If the source_path is None or the provider service is not available,
            the method will return early without performing any upload.
        """
        # Validate input parameters
        if not source_path:
            self.notify_error("No file selected for upload")
            return

        # Get the provider service
        provider_service = get_provider_service_by_access_uuid(
            access_credentials_uuid,
            self.credentials_service,
            self.settings,
        )
        if not provider_service:
            self.notify_error("Could not get provider service for upload")
            return

        # Create upload key
        upload_key = UploadKey(
            display_name=source_path.name,
            uuid=generate_uuid(),
            path=source_path,
            dest_path=str(source_path.name),
        )

        # Push the upload progress screen
        self.push_screen(
            StorageActionProgressScreen(
                storage_name=storage_name,
                provider_service=provider_service,
                path=path,
                keys=[upload_key],
                action="upload",
            ),
            callback=lambda x: self.after_bulk_operation_callback(
                access_credentials_uuid, storage_name, path
            ),
        )

    def _load_storages(self, credentials):
        """
        Loads the list of storages for the given access credentials.

        This method retrieves the list of storages from the provider service
        associated with the provided access credentials and updates the
        storage list sidebar with the retrieved storages.

        Args:
            credentials (Credentials): The access credentials for which to load storages.

        Note:
            If an error occurs while retrieving the storages, a notification is shown
            to the user.
        """
        provider_service = get_provider_service_by_access_credentials(
            credentials, self.settings
        )
        if not provider_service:
            self.notify_error(f"Could not get storages list for {credentials.name}!")
            return

        try:
            storages = provider_service.list_storages()
            storage_names = [storage.storage for storage in storages]
            registered_storages = [
                Storage(credentials.provider, storage.name, storage.created_at)
                for storage in credentials.storages
                if storage.name not in storage_names
            ]
            self.storage_list_sidebar.storages[(credentials.uuid, credentials.name)] = (
                storages + registered_storages
            )
            self.storage_list_sidebar.last_update_timestamp = time.time()
        except Exception:
            self.notify_error(f"Could not get storages list for {credentials.name}!")

    def notify_error(self, message):
        """
        Displays an error notification to the user.

        Args:
            message (str): The error message to display.
        """
        self.notify(message, severity="error")
