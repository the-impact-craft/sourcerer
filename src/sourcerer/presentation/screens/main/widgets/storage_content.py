"""Storage content display widgets for the Sourcerer application.

This module provides widgets for displaying and interacting with storage content,
including files and folders. It handles file selection, navigation, and content
display with search functionality.
"""

import contextlib
import os.path
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar, Self

import humanize
from textual import events, on
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import (
    Center,
    Container,
    Horizontal,
    Middle,
    Vertical,
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
from sourcerer.presentation.screens.main.messages.presign_url_request import (
    PresignedUrlRequest,
)
from sourcerer.presentation.screens.main.messages.preview_request import PreviewRequest
from sourcerer.presentation.screens.main.messages.select_storage_item import (
    SelectStorageItem,
)
from sourcerer.presentation.screens.main.messages.uncheck_files_request import (
    UncheckFilesRequest,
)
from sourcerer.presentation.screens.main.messages.upload_request import UploadRequest
from sourcerer.presentation.screens.shared.containers import (
    ScrollVerticalContainerWithNoBindings,
)
from sourcerer.presentation.screens.shared.widgets.button import Button
from sourcerer.presentation.settings import NO_DATA_LOGO, KeyBindings
from sourcerer.settings import (
    DIRECTORY_ICON,
    DOWNLOAD_ICON,
    FILE_ICON,
    PRESIGNED_URL_ICON,
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
    PRESIGNED_URL = auto()

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
            "presigned_url": cls.PRESIGNED_URL,
        }

        if action_str not in action_map:
            raise ValueError(f"Unknown action type: {action_str}")

        return action_map[action_str]


class UnfocusableCheckbox(Checkbox):
    can_focus = False


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

    can_focus = True

    DEFAULT_CSS = """
    PathSelector {
        &:focus {
            background: $secondary-lighten-2;
        }
    }
    """

    def __init__(self, storage, path, access_credentials_uuid, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.storage = storage
        self.path = path
        self.access_credentials_uuid = access_credentials_uuid

    def on_click(self, _: events.Click) -> None:
        """Handle click events to navigate to the selected path."""
        self._select()

    def on_key(self, event: events.Key) -> None:
        """Handle key events to navigate to the selected path."""
        if event.key == KeyBindings.ENTER.value:
            self._select()

    def _select(self):
        """Select the current path."""
        self.post_message(
            SelectStorageItem(
                self.storage,
                self.path,
                self.access_credentials_uuid,
                focus_content=True,
            )
        )


class FileActionButton(Button):
    can_focus = False


class StorageContentItem(Horizontal):
    DEFAULT_CSS = """
        StorageContentItem.active {
            background: $secondary;
            color: $panel;
        }
        StorageContentItem:focus {
            background: $secondary-lighten-2;
            color: $panel;
        }
        """

    can_focus = True

    def __init__(self, focus_first: bool, *args, **kwargs):
        """Initialize the storage content widget."""
        super().__init__(*args, **kwargs)
        self.focus_first = focus_first

    def on_mount(self) -> None:
        """Handle the mounting of the widget."""
        if self.focus_first and self.first_child:
            self.focus()

    @abstractmethod
    def _select(self, widget=None):
        raise NotImplementedError

    def on_click(self, event: events.Click) -> None:
        """Handle click events to navigate into the folder."""
        self._select(event.widget)

    def on_key(self, event: events.Key) -> None:
        """Handle key events to navigate into the folder."""
        if event.key == KeyBindings.ARROW_UP.value:
            if self.first_child:
                self.parent.children[-1].focus()  # type: ignore
                return
            self.screen.focus_previous()
        if event.key == KeyBindings.ARROW_DOWN.value:
            if self.last_child:
                self.parent.children[0].focus()  # type: ignore
                return
            self.screen.focus_next()

    @on(events.Enter)
    @on(events.Leave)
    def on_enter(self, _: events.Enter):
        with contextlib.suppress(Exception):
            self.set_class(self.is_mouse_over, "active")


class FolderItem(StorageContentItem):
    """Widget for displaying and interacting with folder items.

    This widget represents a folder in the storage content view, allowing
    navigation into the folder and visual feedback on hover/selection.
    """

    def __init__(
        self,
        storage,
        access_credentials_uuid,
        parent_path,
        folder,
        focus_first,
        *args,
        **kwargs,
    ):
        """Initialize a folder item widget.

        Args:
            storage: The name of the storage provider
            access_credentials_uuid: UUID of the access credentials being used
            parent_path: The parent path of the folder
            folder: The folder name
        """
        super().__init__(focus_first, *args, **kwargs)
        self.storage = storage
        self.access_credentials_uuid = access_credentials_uuid
        self.parent_path = parent_path
        self.folder = folder

    def compose(self):
        """Compose the folder item layout with folder name and icon."""
        yield Label(f"{DIRECTORY_ICON}{self.folder.key}", markup=False)

    def _select(self, widget=None):
        """Select the folder."""
        self.post_message(
            SelectStorageItem(
                self.storage,
                self.folder.parent_path + self.folder.key,
                self.access_credentials_uuid,
                focus_content=True,
            )
        )

    def on_key(self, event: events.Key) -> None:
        """Handle key events to navigate into the folder."""
        if event.key in (KeyBindings.ARROW_UP.value, KeyBindings.ARROW_DOWN.value):
            event.prevent_default()
        if event.key == KeyBindings.ENTER.value:
            self._select()
            return
        super().on_key(event)


class FileItem(StorageContentItem):
    """Widget for displaying and interacting with file items.

    This widget represents a file in the storage content view, allowing
    selection and visual feedback on hover/selection.
    """

    DEFAULT_CSS = """
    .file_size {
        color: $primary
    }
    UnfocusableCheckbox {
        border: none;
        padding: 0 0;
        display: none;
        &:focus {
            border: none;
            background-tint: $foreground 5%;
        }
    }
    """

    @dataclass
    class Selected(Message):
        """Message sent when a file is selected."""

        name: str

    @dataclass
    class Preview(Message):
        """Message sent when a file preview is selected."""

        name: str
        size: int

    @dataclass
    class PresignedUrl(Message):
        """Message sent when a file preview is selected."""

        name: str

    @dataclass
    class Unselect(Message):
        """Message sent when a file is unselected."""

        name: str

    def __init__(self, storage, parent_path, file, focus_first, *args, **kwargs):
        """Initialize a file item widget.

        Args:
            storage: The name of the storage provider
            parent_path: The parent path of the file
            file: The file name
        """
        super().__init__(focus_first, *args, **kwargs)
        self.storage = storage
        self.parent_path = parent_path
        self.file = file

    def compose(self):
        yield UnfocusableCheckbox()
        yield FileMetaLabel(
            f"{FILE_ICON} {self.file.key}", classes="file_name", markup=False
        )
        yield FileMetaLabel(
            f"{humanize.naturalsize(self.file.size)}", classes="file_size", markup=False
        )
        yield FileMetaLabel(
            str(self.file.date_modified), classes="file_date", markup=False
        )
        yield FileActionButton(
            f"{PRESIGNED_URL_ICON}", name="presigned_url", classes="presigned_url"
        )
        if self.file.is_text:
            yield FileActionButton(f"{PREVIEW_ICON}", name="preview", classes="preview")

    def on_key(self, event: events.Key) -> None:
        """Handle key events to toggle file selection."""
        if event.key in (KeyBindings.ARROW_UP.value, KeyBindings.ARROW_DOWN.value):
            event.prevent_default()
        if event.key == KeyBindings.ENTER.value:
            checkbox = self.query_one(UnfocusableCheckbox)
            checkbox.value = not checkbox.value
            if checkbox.value:
                self.post_message(self.Selected(self.file.key))
            else:
                self.post_message(self.Unselect(self.file.key))
            return
        super().on_key(event)

    def _select(self, widget=None):
        preview_button = None
        presign_url_button = None
        with contextlib.suppress(NoMatches):
            preview_button = self.query_one(".preview")
        with contextlib.suppress(NoMatches):
            presign_url_button = self.query_one(".presigned_url")

        if widget is preview_button:
            self.post_message(self.Preview(self.file.key, self.file.size))
            return
        if widget is presign_url_button:
            self.post_message(self.PresignedUrl(self.file.key))
            return

        checkbox = self.query_one(UnfocusableCheckbox)
        if widget is not checkbox:
            checkbox.value = not checkbox.value
        if checkbox.value:
            self.post_message(self.Selected(self.file.key))
        else:
            self.post_message(self.Unselect(self.file.key))

    def uncheck(self):
        """Uncheck the file's checkbox."""
        checkbox = self.query_one(UnfocusableCheckbox)
        checkbox.value = False

    def check(self):
        """Check the file's checkbox."""
        checkbox = self.query_one(UnfocusableCheckbox)
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

    storage: reactive[str | None] = reactive(  # ty: ignore[invalid-assignment]
        None, recompose=True
    )
    path: reactive[str | None] = reactive(  # ty: ignore[invalid-assignment]
        None, recompose=False
    )
    search_prefix: reactive[str | None] = reactive(  # ty: ignore[invalid-assignment]
        None, recompose=False
    )
    access_credentials_uuid: reactive[  # ty: ignore[invalid-assignment]
        str | None
    ] = reactive("", recompose=False)
    storage_content: reactive[  # ty: ignore[invalid-assignment]
        StorageContent | None
    ] = reactive(None, recompose=True)
    selected_files: reactive[set] = reactive(set(), recompose=False)
    selected_files_n: reactive[int] = reactive(0, recompose=False)
    focus_content: reactive[bool] = reactive(False, recompose=False)

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding(
            f"{KeyBindings.CTRL.value}+{KeyBindings.BACKSPACE.value}",
            "back_to_prev_path",
            "Navigate back to the previous path",
            show=True,
        ),
    ]

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
        margin: 1 0 0 0;

        PathSelector {
            &.primary_color {
                color: $primary;
            }
            &.secondary_color {
                color: $secondary;
            }
        }
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

    search_input_id: ClassVar[str] = "search_input"

    def compose(self) -> ComposeResult:
        if not self.storage:
            return
        breadcrumbs = self.path.split("/") if self.path else []
        breadcrumbs.insert(0, self.storage)

        with Container(id="storage_path"):
            with Horizontal():
                yield Label("Current Path: ", classes="storage_path_item")
                for index, breadcrumb in enumerate(breadcrumbs):
                    color_classes = "primary" if index == 0 else "secondary"
                    yield PathSelector(
                        renderable=breadcrumb,
                        storage=self.storage,
                        path="/".join(breadcrumbs[1 : index + 1]),
                        access_credentials_uuid=self.access_credentials_uuid,
                        classes=f"storage_path_item {color_classes}_color",
                        markup=False,
                    )
                    yield Label("/", classes="storage_path_item")
            with Horizontal():
                yield Label("Search:")
                yield Input(
                    id=self.search_input_id,
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
            yield FileMetaLabel("Actions", classes="preview")
        with ScrollVerticalContainerWithNoBindings(id="content", can_focus=False):
            for folder in self.storage_content.folders:
                yield FolderItem(
                    self.storage,
                    self.access_credentials_uuid,
                    self.path,
                    folder,
                    self.focus_content,
                )
            for file in self.storage_content.files:
                yield FileItem(
                    self.storage, self.path, file, self.focus_content, id=file.uuid
                )

    def focus(self, scroll_visible: bool = True) -> Self:
        try:
            content = self.query_one(ScrollVerticalContainerWithNoBindings)
        except NoMatches:
            return self
        if len(content.children) > 0:
            content.children[0].focus()
        return self

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
                event.size,
            )
        )

    @on(FileItem.PresignedUrl)
    def on_file_item_presigned_url(self, event: FileItem.PresignedUrl):
        if not self.storage or not self.access_credentials_uuid:
            return
        self.post_message(
            PresignedUrlRequest(
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
            self.post_message(DeleteRequest(**params))  # ty: ignore[missing-argument]
        elif action_type == ActionType.DOWNLOAD:
            self.post_message(DownloadRequest(**params))  # ty: ignore[missing-argument]
        elif action_type == ActionType.UNCHECK_ALL:
            self.post_message(
                UncheckFilesRequest(
                    keys=[
                        item.uuid
                        for item in getattr(self.storage_content, "files", [])
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
            counter = self.query_one("#selected_n", Label)
        except NoMatches:
            return

        if self.selected_files_n > 0:
            if not selected_actions.has_class("-visible"):
                selected_actions.add_class("-visible")
            counter.update(f"❌Selected: {self.selected_files_n}")
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
                self.storage,
                self.path,
                self.access_credentials_uuid,
                value,
                focus_content=True,
            )
        )

    def action_back_to_prev_path(self):
        """
        Navigate back to the previous path in the storage content.

        This method updates the path to the parent directory and triggers a
        SelectStorageItem message to refresh the storage content with the new path.
        """
        if not self.storage:
            return
        if not self.path:
            return
        path_parents = [i for i in self.path.split("/")[:-1] if i]
        prev_path = "/".join(path_parents)
        self.post_message(
            SelectStorageItem(
                self.storage,
                prev_path,
                self.access_credentials_uuid,
                focus_content=True,
            )
        )
