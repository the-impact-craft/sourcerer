"""Storage content display widgets for the Sourcerer application.

This module provides widgets for displaying and interacting with storage content,
including files and folders. It handles file selection, navigation, and content
display with search functionality.
"""

import contextlib
import os.path
from dataclasses import dataclass
from enum import Enum, auto

from textual import events, on
from textual.app import ComposeResult
from textual.containers import (
    Center,
    Container,
    Horizontal,
    Middle,
    Vertical,
    VerticalScroll,
)
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Checkbox, Input, Label, Static

from sourcerer.domain.storage_provider.entities import StorageContent
from sourcerer.presentation.screens.main.messages.delete_request import DeleteRequest
from sourcerer.presentation.screens.main.messages.download_request import (
    DownloadRequest,
)
from sourcerer.presentation.screens.main.messages.preview_request import PreviewRequest
from sourcerer.presentation.screens.main.messages.select_storage_item import (
    SelectStorageItem,
)
from sourcerer.presentation.screens.main.messages.uncheck_files_request import (
    UncheckFilesRequest,
)
from sourcerer.presentation.screens.main.messages.upload_request import UploadRequest
from sourcerer.presentation.screens.shared.widgets.button import Button
from sourcerer.presentation.settings import NO_DATA_LOGO
from sourcerer.settings import (
    DIRECTORY_ICON,
    DOWNLOAD_ICON,
    FILE_ICON,
    PREVIEW_ICON,
    UPLOAD_ICON,
)


class ActionType(Enum):
    """
    Enum representing the different types of actions that can be performed on storage items.

    This enum is used to replace string literals for action types, providing better type safety,
    code completion, and making the code more maintainable.
    """

    UPLOAD = auto()
    DELETE = auto()
    DOWNLOAD = auto()
    UNCHECK_ALL = auto()
    PREVIEW = auto()

    @classmethod
    def from_string(cls, action_str: str) -> "ActionType":
        """
        Convert a string action name to the corresponding enum value.

        Args:
            action_str (str): The string representation of the action

        Returns:
            ActionType: The corresponding enum value

        Raises:
            ValueError: If the string doesn't match any known action type
        """
        action_map = {
            "upload": cls.UPLOAD,
            "delete": cls.DELETE,
            "download": cls.DOWNLOAD,
            "uncheck_all": cls.UNCHECK_ALL,
            "preview": cls.PREVIEW,
        }

        if action_str not in action_map:
            raise ValueError(f"Unknown action type: {action_str}")

        return action_map[action_str]


class FileMetaLabel(Static):
    """Widget for displaying file metadata information.

    This widget is used to show file metadata such as size, modification date,
    or other file properties in a transparent background.
    """

    DEFAULT_CSS = """
    FileMetaLabel {
        margin: 0 0;
        padding: 0 0;
        background: transparent;
    }
    """
    can_focus = False


class PathSelector(Label):
    """Widget for displaying and selecting storage paths.

    This widget shows the current path in the storage and allows navigation
    by clicking on path segments.

    Args:
        storage: The name of the storage provider
        path: The current path in the storage
        access_credentials_uuid: UUID of the access credentials being used
    """

    def __init__(self, storage, path, access_credentials_uuid, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.storage = storage
        self.path = path
        self.access_credentials_uuid = access_credentials_uuid

    def on_click(self, _: events.Click) -> None:
        """Handle click events to navigate to the selected path."""
        self.post_message(
            SelectStorageItem(self.storage, self.path, self.access_credentials_uuid)
        )


class FolderItem(Horizontal):
    """Widget for displaying and interacting with folder items.

    This widget represents a folder in the storage content view, allowing
    navigation into the folder and visual feedback on hover/selection.
    """

    DEFAULT_CSS = """
    FolderItem {
        margin-bottom: 1;
    }
    FolderItem.active {
        background: $secondary;
        color: $panel;
    }
    """
    can_focus = False

    def __init__(
        self, storage, access_credentials_uuid, parent_path, folder, *args, **kwargs
    ):
        """Initialize a folder item widget.

        Args:
            storage: The name of the storage provider
            access_credentials_uuid: UUID of the access credentials being used
            parent_path: The parent path of the folder
            folder: The folder name
        """
        super().__init__(*args, **kwargs)
        self.storage = storage
        self.access_credentials_uuid = access_credentials_uuid
        self.parent_path = parent_path
        self.folder = folder

    def compose(self):
        """Compose the folder item layout with folder name and icon."""
        yield Label(f"{DIRECTORY_ICON}{self.folder.key}")

    def on_click(self, _: events.Click) -> None:
        """Handle click events to navigate into the folder."""
        path = self.folder.key
        if self.parent_path:
            path = self.parent_path.strip("/") + "/" + path

        self.post_message(
            SelectStorageItem(self.storage, path, self.access_credentials_uuid)
        )

    def on_mouse_move(self, _) -> None:
        """Handle mouse move events to highlight the folder."""
        self.add_class("active")

    def on_leave(self, _) -> None:
        """Handle mouse leave events to remove highlight."""
        self.remove_class("active")


class FileItem(Horizontal):
    """Widget for displaying and interacting with file items.

    This widget represents a file in the storage content view, allowing
    selection and visual feedback on hover/selection.
    """

    DEFAULT_CSS = """
    FileItem {
        margin-bottom: 1;
    }
    FileItem.active {
        background: $secondary;
        color: $panel;
    }
    Checkbox {
        border: none;
        padding: 0 0;
        display: none;
        &:focus {
            border: none;
            background-tint: $foreground 5%;
        }
    }
    """
    can_focus = False

    @dataclass
    class Selected(Message):
        """Message sent when a file is selected."""

        name: str

    @dataclass
    class Preview(Message):
        """Message sent when a file preview is selected."""

        name: str

    @dataclass
    class Unselect(Message):
        """Message sent when a file is unselected."""

        name: str

    def on_mount(self):
        """Initialize the file item on mount."""
        self.add_class("file-item")

    def __init__(self, storage, parent_path, file, *args, **kwargs):
        """Initialize a file item widget.

        Args:
            storage: The name of the storage provider
            parent_path: The parent path of the file
            file: The file name
        """
        super().__init__(*args, **kwargs)
        self.storage = storage
        self.parent_path = parent_path
        self.file = file

    def compose(self):
        yield Checkbox()
        yield FileMetaLabel(f"{FILE_ICON} {self.file.key}", classes="file_name")
        yield FileMetaLabel(
            f"[$primary]{self.file.size}[/$primary]", classes="file_size"
        )
        yield FileMetaLabel(str(self.file.date_modified), classes="file_date")
        if self.file.is_text:
            yield Button(f"{PREVIEW_ICON}", name="preview", classes="download")

    def on_mouse_move(self, _) -> None:
        """Handle mouse move events to highlight the file."""
        self.add_class("active")

    def on_leave(self, _) -> None:
        """Handle mouse leave events to remove highlight."""
        self.remove_class("active")

    def on_click(self, event: events.Click) -> None:
        """Handle click events to toggle file selection."""
        preview_button = None
        with contextlib.suppress(NoMatches):
            preview_button = self.query_one(Button)

        if event.widget is preview_button:
            self.post_message(self.Preview(self.file.key))
            return

        checkbox = self.query_one(Checkbox)
        if event.widget is not checkbox:
            checkbox.value = not checkbox.value
        if checkbox.value:
            self.post_message(self.Selected(self.file.key))
        else:
            self.post_message(self.Unselect(self.file.key))
        event.prevent_default()
        event.stop()

    def uncheck(self):
        """Uncheck the file's checkbox."""
        checkbox = self.query_one(Checkbox)
        checkbox.value = False

    def check(self):
        """Check the file's checkbox."""
        checkbox = self.query_one(Checkbox)
        checkbox.value = True


class StorageContentContainer(Vertical):
    """Main widget for displaying storage content.

    This widget manages the display of storage content including files and folders,
    handles file selection, search functionality, and bulk operations.

    Attributes:
        storage: The name of the current storage provider
        path: The current path in the storage
        search_prefix: The current search filter
        access_credentials_uuid: UUID of the access credentials being used
        storage_content: The current storage content to display
        selected_files: Set of selected file names
        selected_files_n: Number of selected files
    """

    storage: reactive[str | None] = reactive(None, recompose=True)
    path: reactive[str | None] = reactive(None, recompose=False)
    search_prefix: reactive[str | None] = reactive(None, recompose=False)
    access_credentials_uuid: reactive[str | None] = reactive("", recompose=False)
    storage_content: reactive[StorageContent | None] = reactive(None, recompose=True)
    selected_files: reactive[set] = reactive(set(), recompose=False)
    selected_files_n: reactive[int] = reactive(0, recompose=False)

    DEFAULT_CSS = """

    StorageContent {
        padding: 1 2 1 1;
        height: 100%
    }

    Horizontal {
        height:auto
    }
    VerticalScroll {
        height: 100%
    }

    .file_name {
        width: 55%;
    }

    .file_size {
        width: 10;
    }

    .file_date {
        width: 25%;
    }

    .preview {
        width: 5%;
    }

    #storage_path {
        width: 100%;
        height: auto;
        border-bottom: solid $secondary;
        margin: 1 0;
    }
    .storage_path_item {
        padding: 0 0;
    }

    #search_input {
        height: 1;
        border: none;
        background: transparent
    }

    Center {

        & > Static {
            width: auto;
        }
    }

    .file_list_header {
        border-bottom: solid $background-lighten-3;
    }

    #content {
        height: 80%;
        & > FileItem {
            & > Checkbox {
                display: none;
            }
        }

        &.-visible {
             & > FileItem {
                & > Checkbox {
                    display: block;
                }
            }

        }
    }
    #totals_section {
        height:1;
        padding-right: 1;
    }

    #default_actions {
        width: 100%;
        display: none;
        align-horizontal: right;
        height: auto;
        padding-right: 2;
        margin: 0 0;

        &.-visible {
            display: block;
        }
        Static {
            width: auto;
            height: auto;
        }
    }

    #selected_actions {
        width: 100%;
        display: none;
        layout: grid;
        grid-size: 2 1;
        height: auto;

        &.-visible {
            display: block;
        }
        Static {
            width: auto;
            height: auto;
        }

        #action_buttons {

            align-horizontal: right;
            height: auto;

            & > Label {
                width: auto;
                padding-right: 2;


            }
        }
    }
    """

    def compose(self) -> ComposeResult:
        if not self.storage:
            return
        breadcrumbs = self.path.split("/") if self.path else []
        breadcrumbs.insert(0, self.storage)

        with Container(id="storage_path"):
            with Horizontal():
                yield Label("Current Path: ", classes="storage_path_item")
                for index, breadcrumb in enumerate(breadcrumbs):
                    color = "$primary" if index == 0 else "$secondary"
                    yield PathSelector(
                        renderable=f"[{color}]{breadcrumb}[/]",
                        storage=self.storage,
                        path="/".join(breadcrumbs[1 : index + 1]),
                        access_credentials_uuid=self.access_credentials_uuid,
                        classes="storage_path_item",
                    )
                    yield Label("/", classes="storage_path_item")
            with Horizontal():
                yield Label("Search:")
                yield Input(
                    id="search_input",
                    placeholder="input path prefix here...",
                    value=self.search_prefix,
                )
        if not self.storage_content:
            return
        with Horizontal(id="totals_section"):
            with Horizontal(id="selected_actions"):
                yield Button("❌Selected: ", id="selected_n", name="uncheck_all")
                with Horizontal(id="action_buttons"):
                    yield Button(f"{DOWNLOAD_ICON} Download", name="download")
                    yield Button("🗑️ Delete", name="delete")
            with Horizontal(id="default_actions", classes="-visible"):
                yield Button(f"{UPLOAD_ICON} Upload", name="upload")
        if not self.storage_content or (
            not self.storage_content.files and not self.storage_content.folders
        ):
            with Middle(), Center():
                yield Static(NO_DATA_LOGO)
            return
        with Horizontal(classes="file_list_header"):
            yield FileMetaLabel("Name", classes="file_name")
            yield FileMetaLabel("Size", classes="file_size")
            yield FileMetaLabel("Date modified", classes="file_date")
            yield FileMetaLabel("Preview", classes="preview")
        with VerticalScroll(id="content"):
            for folder in self.storage_content.folders:
                yield FolderItem(
                    self.storage, self.access_credentials_uuid, self.path, folder
                )
            for file in self.storage_content.files:
                yield FileItem(self.storage, self.path, file, id=file.uuid)

    @on(Input.Submitted)
    def on_input_submitted(self, event: Input.Submitted):
        """
        Handle input submission events to apply the search prefix.

        This method is triggered when the user presses Enter in the input field
        and applies the search prefix to the current storage content.

        Args:
            event (Input.Submitted): The submit event containing the input value
        """
        self.apply_search_prefix(event.value)

    @on(Input.Blurred)
    def on_input_blurred(self, event: Input.Blurred):
        """
        Handle input blur events to apply the search prefix.

        This method is triggered when the input field loses focus and applies
        the search prefix to the current storage content.

        Args:
            event (Input.Blurred): The blur event containing the input value
        """
        self.apply_search_prefix(event.value)

    @on(FileItem.Preview)
    def on_file_item_preview(self, event: FileItem.Preview):
        """
        Handle file preview events to request a preview of the selected file.
        This method sends a PreviewRequest message with the storage name,
        access credentials UUID, and file path to the backend for processing.

        Args:
            event (FileItem.Preview): The preview event containing the file name

        """
        if not self.storage or not self.access_credentials_uuid:
            return
        self.post_message(
            PreviewRequest(
                self.storage,
                self.access_credentials_uuid,
                os.path.join(self.path, event.name) if self.path else event.name,
            )
        )

    @on(FileItem.Selected)
    def on_file_item_select(self, event: FileItem.Selected):
        """
        Handle file selection events to update the selected files list.

        This method adds the selected file to the selected_files set and updates
        the selected_files_n attribute accordingly. It also manages the visibility of
        the selected actions and default actions sections based on the number of selected files.

        Args:
            event (FileItem.Selected): The select event containing the file name
        """
        self.selected_files.add(event.name)
        self.selected_files_n = len(self.selected_files)

        selected_actions = self.query_one("#selected_actions")
        content = self.query_one("#content")

        if not content.has_class("-visible"):
            content.add_class("-visible")
        if not selected_actions.has_class("-visible"):
            selected_actions.add_class("-visible")

        self.query_one("#default_actions").remove_class("-visible")

    @on(FileItem.Unselect)
    def on_file_item_unselect(self, event: FileItem.Unselect):
        """
        Handle file unselection events to update the selected files list.

        This method removes the unselected file from the selected_files set and updates
        the selected_files_n attribute accordingly. It also manages the visibility of
        the selected actions and default actions sections based on the number of selected files.
        Args:
            event (FileItem.Unselect): The unselect event containing the file name
        """
        if event.name not in self.selected_files:
            return
        self.selected_files.remove(event.name)
        self.selected_files_n = len(self.selected_files)
        if self.selected_files_n == 0:
            self.query_one("#content").remove_class("-visible")
            self.query_one("#selected_actions").remove_class("-visible")
            self.query_one("#default_actions").add_class("-visible")

    @on(Button.Click)
    def on_button_click(self, event: Button.Click):
        """
        Handle button click events to perform actions on selected files.
        This method processes the click events for buttons in the storage content
        section, such as upload, delete, download, and uncheck all actions.

        Args:
            event (Button.Click): The button click event
        """
        if not self.storage or not self.access_credentials_uuid:
            return
        params = {
            "storage_name": self.storage,
            "path": self.path,
            "access_credentials_uuid": self.access_credentials_uuid,
            "keys": self.selected_files,
        }

        # Convert string action to enum
        action_type = ActionType.from_string(event.action)

        if action_type == ActionType.UPLOAD:
            self.post_message(
                UploadRequest(
                    access_credentials_uuid=self.access_credentials_uuid,
                    storage=self.storage,
                    path=self.path,
                )
            )
        elif action_type == ActionType.DELETE:
            self.post_message(DeleteRequest(**params))
        elif action_type == ActionType.DOWNLOAD:
            self.post_message(DownloadRequest(**params))
        elif action_type == ActionType.UNCHECK_ALL:
            self.post_message(
                UncheckFilesRequest(
                    keys=[
                        item.uuid
                        for item in self.storage_content.files  # type: ignore
                        if item.key in self.selected_files
                    ]
                )
            )
            self.query_one("#default_actions").add_class("-visible")

    def watch_selected_files_n(self):
        """
        Watch for changes in the number of selected files and update the UI accordingly.

        This method updates the visibility and content of the selected actions section
        based on the number of selected files.
        """
        try:
            selected_actions = self.query_one("#selected_actions")
            counter = self.query_one("#selected_n")
        except NoMatches:
            return

        if self.selected_files_n > 0:
            if not selected_actions.has_class("-visible"):
                selected_actions.add_class("-visible")
            counter.update(f"❌Selected: {self.selected_files_n}")  # type: ignore
        else:
            selected_actions.remove_class("-visible")
            self.query_one("#content").remove_class("-visible")
            self.query_one("#selected_actions").remove_class("-visible")

    def apply_search_prefix(self, value):
        """
        Apply a search prefix filter to the current storage content.

        This method updates the search prefix and triggers a SelectStorageItem
        message to refresh the storage content with the new filter.

        Args:
            value (str): The search prefix to apply
        """
        if not self.storage:
            return
        self.search_prefix = value
        self.post_message(
            SelectStorageItem(
                self.storage,  # type: ignore
                self.path,
                self.access_credentials_uuid,
                value,
            )
        )
