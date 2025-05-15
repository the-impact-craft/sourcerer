from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from time import time
from typing import ClassVar, Literal

from textual import events, on
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, Rule

from sourcerer.infrastructure.file_system.exceptions import ListDirError
from sourcerer.infrastructure.file_system.services import FileSystemService
from sourcerer.infrastructure.utils import generate_uuid
from sourcerer.presentation.screens.shared.containers import (
    ScrollHorizontalContainerWithNoBindings,
    ScrollVerticalContainerWithNoBindings,
)
from sourcerer.settings import DIRECTORY_ICON, DOUBLE_CLICK_THRESHOLD, FILE_ICON


class PathListingContainer(ScrollVerticalContainerWithNoBindings):
    can_focus = False

    def on_mount(self, _: events.Mount) -> None:
        """
        Ensure the scroll is visible when the container is mounted.

        This method is called automatically when the container is mounted, and it makes the scroll bar visible,
        improving the user's ability to navigate through content that may exceed the container's visible area.

        Args:
            _ (events.Mount): The mount event triggered when the container is added to the UI.
        """
        self.scroll_visible()


class FileSystemWidget(Widget):
    DEFAULT_CSS = """
    FileSystemWidget {
        &:hover, &:focus, &:focus-within, &:ansi {
            color: $block-cursor-blurred-foreground;
            background: $block-cursor-blurred-background;
            text-style: $block-cursor-blurred-text-style;
        }
        
        .folder-name {
            text-overflow: ellipsis;
            text-wrap: nowrap;
        }
    }
    """
    can_focus = True

    @dataclass
    class FileClick(Message):
        name: Path

    @dataclass
    class FileDoubleClick(Message):
        name: Path

    @dataclass
    class FolderClick(Message):
        name: Path

    @dataclass
    class FolderDoubleClick(Message):
        name: Path

    @dataclass
    class Focus(Message):
        name: Path

    def __init__(self, entity_name: Path, icon: str, *args, **kwargs):
        """
        Initialize a FileSystemWidget representing a file or directory.

        Parameters:
            entity_name (Path): The path of the file or directory being represented
            icon (str): A visual icon representing the file or directory type
            *args: Variable positional arguments passed to the parent Widget constructor
            **kwargs: Variable keyword arguments passed to the parent Widget constructor

        Attributes:
            entity_name (Path): Stores the path of the current file or directory
            icon (str): Stores the icon for visual representation
            last_file_click (Tuple[float, Path | None]): Tracks the timestamp and path of the last file click
                to enable double-click detection, initialized with a timestamp two seconds in the past
        """
        self.entity_name = entity_name
        self.icon = icon
        self.last_file_click: tuple[float, Path | None] = (
            time() - 2,
            None,
        )
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        """
        Compose the visual representation of a file system entity.

        Returns:
            Label: A label displaying the entity's icon and name with the 'folder-name' CSS class.

        The method yields a Label widget that combines the predefined icon and the name of the entity
        (file or folder) for display in the user interface.
        """
        yield Label(
            f"{self.icon} {self.entity_name.name}", classes="folder-name"
        ).with_tooltip(self.entity_name.name)

    def on_click(self, _: events.Click) -> None:
        """
        Handle click events for file system entities, distinguishing between single and double clicks.

        This method processes user clicks on files and folders, posting appropriate messages based on the entity type:
        - For directories, it posts a FolderClick message
        - For files, it posts a FileClick message
        - For files clicked twice within a short time threshold, it posts a FileDoubleClick message

        Parameters:
            _ (events.Click): The click event (unused parameter)

        Side Effects:
            - Posts FileSystemWidget messages for folder and file interactions
            - Updates the last file click timestamp and entity
        """
        self.on_file_select()

    def on_focus(self, _: events.Focus) -> None:
        """
        Handle focus event for the file system widget.

        When the widget receives focus, it posts a Focus message with the entity's name.

        Parameters:
            _ (events.Focus): The focus event (unused, hence the underscore)

        Emits:
            Focus message containing the name of the focused entity
        """
        self.post_message(self.Focus(self.entity_name))

    def on_key(self, event: events.Key) -> None:
        """
        Handle key press events for the widget, specifically the "enter" key.

        When the "enter" key is pressed, this method triggers the same behavior as a click event,
        simulating a user interaction with the current widget.

        Parameters:
            event (events.Key): The key press event containing details about the key that was pressed.

        Side Effects:
            Calls the `on_click` method if the pressed key is "enter", which may trigger
            folder navigation or file opening depending on the widget's context.
        """
        if event.key == "enter":
            self.on_file_select()

    def on_file_select(self):
        """
        Handle a file selection event by updating the selected file.

        This method is triggered when a file is selected in the file system navigator. It updates the selected file
        based on the event's file path.

        """
        current_click = (time(), self.entity_name)

        self.send_event(
            self.FolderClick if self.entity_name.is_dir() else self.FileClick
        )
        if (
            current_click[0] - self.last_file_click[0] < DOUBLE_CLICK_THRESHOLD
            and current_click[1] == self.last_file_click[1]
        ):
            self.send_event(
                self.FolderDoubleClick
                if self.entity_name.is_dir()
                else self.FileDoubleClick
            )
        self.last_file_click = current_click

    def send_event(self, event_name):
        """
        Send an event with the current file system entity's name.

        Parameters:
            event_name: The event class to be sent, which should be a dataclass with a 'name' field.

        This method is used to post an event related to the current file system entity, such as a click or double-click.
        It dynamically creates an instance of the provided event class with the entity's name and posts it.
        """
        self.post_message(event_name(self.entity_name))


class FileSystemNavigatorClasses(Enum):
    MAIN_CONTAINER = "main_container"
    PATH_LISTING_CONTAINER = "path_listing_container"
    DIRECTORY_LISTING_FOLDER = "dir-listing-folder"
    DIRECTORY_LISTING_FILE = "dir-listing-file"


class FileSystemNavigator(ScrollHorizontalContainerWithNoBindings):
    DEFAULT_CSS = """
    FileSystemNavigator {
        width: 100%;
        height: 11;
        layout: horizontal;
        overflow-y: hidden;
        overflow-x: auto;
        overflow-x: auto;
        & > .dir_listing {
            overflow-y: auto;
            overflow-x: auto;
            width: 40%;
        }

         & > Rule.-vertical {
            margin: 0;
            color: $block-cursor-blurred-background;
        }
    }
    """

    # Consolidate key binding data
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("enter", "select_cursor", "Select", show=False),
        Binding("up", "cursor_up", "Cursor up", show=False),
        Binding("down", "cursor_down", "Cursor down", show=False),
        Binding("left", "cursor_left", "Cursor left", show=False),
        Binding("right", "cursor_right", "Cursor right", show=False),
    ]

    MAIN_CONTAINER_ID: ClassVar[str] = "dirs_content"

    # Direction constants for better readability
    DIRECTION_UP: Literal["up"] = "up"
    DIRECTION_DOWN: Literal["down"] = "down"

    can_focus = True
    active_path = reactive(None)

    @dataclass
    class ActivePathChanged(Message):
        path: Path | None

    @dataclass
    class ActivePathFileDoubleClicked(Message):
        path: Path

    def __init__(
        self, work_dir: Path, file_system_service: FileSystemService, *args, **kwargs
    ):
        """
        Initialize a FileSystemNavigator with a working directory and file system service.

        Parameters:
            work_dir (Path): The initial directory path to start file system navigation
            file_system_service (FileSystemService): Service responsible for file system operations
            *args: Variable positional arguments for parent class initialization
            **kwargs: Variable keyword arguments for parent class initialization

        Attributes:
            work_dir (Path): The current working directory
            file_system_service (object): Service for performing file system operations
            path_listing_containers_uuids (dict): Mapping of path containers to their unique identifiers
            focus_path (Path): The currently focused path, initially set to the working directory
        """
        self.work_dir = work_dir
        self.file_system_service = file_system_service
        self.path_listing_containers_uuids = {}
        self.focus_path = work_dir
        super().__init__(*args, **kwargs)

    async def on_mount(self, _: events.Mount) -> None:
        """
        Mount the initial path listing container for the current working directory.

        This asynchronous method is called when the FileSystemNavigator is mounted. It retrieves the path listing
        container for the current working directory and mounts it without a divider. The container's UUID is stored in
        the path_listing_containers_uuids dictionary for tracking and future reference.

        If no path listing container can be created for the current working directory, the method silently returns.

        Args:
            _ (events.Mount): The mount event (unused in this method)

        Side Effects:
            - Mounts a path listing container for the current working directory
            - Stores the container's UUID in path_listing_containers_uuids
        """
        path_listing_container = self._get_path_listing_container(self.work_dir)
        if not path_listing_container:
            return

        await self._mount_path_listing_container(
            path_listing_container, mount_divider=False
        )
        self._focus_first_child(path_listing_container)

        self.path_listing_containers_uuids[str(self.work_dir)] = (
            path_listing_container.id
        )

    def action_cursor_down(self) -> None:
        """
        Move the cursor down to the next item in the current path listing container.

        This method navigates downward through the children of the currently focused path listing container. If a next
        focusable element is found, it receives focus.

        Behavior:
        - If no path listing container is currently focused, the method returns without action
        - Searches for the next focusable element below the current focused item
        - If no next element is found, the method returns without action
        - Focuses the next available element when found

        Returns:
            None
        """
        path_listing_container = self._get_focused_path_listing_container()
        if not path_listing_container:
            return

        next_focus = self._get_next_element(
            path_listing_container.children, self.DIRECTION_DOWN, self._has_focus
        )
        if not next_focus:
            return
        next_focus.focus()

    def action_cursor_up(self) -> None:
        """
        Navigate to the previous item in the current path listing container.

        This method moves the focus upward within the currently focused path listing container.
        If no container is focused or no previous item exists, the method does nothing.

        Raises:
            No explicit exceptions are raised.

        Side Effects:
            - Changes the focused widget to the previous item in the container
            - Calls the `focus()` method on the selected widget

        Example:
            # When multiple items exist in a path listing container
            # Pressing the up arrow key will move focus to the previous item
        """
        focused_container = self._get_focused_path_listing_container()
        if not focused_container:
            return

        next_focus = self._get_next_element(
            focused_container.children, self.DIRECTION_UP, self._has_focus
        )
        if not next_focus:
            return
        next_focus.focus()

    def action_cursor_left(self) -> None:
        """
        Navigate to the parent directory's container and focus on the first child.

        This method handles left cursor navigation in the file system navigator. If the current focus is at the root
        working directory, no action is taken. Otherwise, it attempts to find and focus on the first child in the
        parent directory's container.

        Parameters:
            None

        Returns:
            None

        Raises:
            NoMatches: If the parent directory's container cannot be found in the query.

        Notes:
            - Skips navigation if the current focus is at the root working directory
            - Retrieves the UUID of the parent directory's container
            - Focuses on the first child of the parent directory's container
        """
        if self.focus_path == self.work_dir:
            return
        active_path_container_uuid = self.path_listing_containers_uuids.get(
            str(self.focus_path.parent)
        )
        if not active_path_container_uuid:
            return

        try:
            active_path_container = self.query_one(f"#{active_path_container_uuid}")
        except NoMatches:
            return

        self._focus_first_child(active_path_container)

    def action_cursor_right(self) -> None:
        """
        Navigate to the next directory column to the right in the file system navigator.

        This method handles cursor movement to the right within the file system navigation interface.
        It performs the following steps:
        - Retrieves the UUID of the currently focused path's container
        - If no container is found for the current path, exits early
        - Finds the next directory column to the right using the `_get_next_element` method
        - If a next column is found, focuses on the first child of that column

        Parameters:
            self (FileSystemNavigator): The current file system navigator instance

        Returns:
            None: Moves the cursor focus without returning a value
        """
        active_path_container_uuid = self.path_listing_containers_uuids.get(
            str(self.focus_path)
        )

        if not active_path_container_uuid:
            return

        next_dir_column = self._get_next_element(
            self.children,
            "down",
            lambda x: x.id == active_path_container_uuid,
            of_type=PathListingContainer,
        )
        if not next_dir_column:
            return
        self._focus_first_child(next_dir_column)

    def _get_focused_path_listing_container(self) -> PathListingContainer | None:
        """
        Retrieve the currently focused path listing container based on the current focus path.

        This method checks if the current focus path has an associated container UUID in the
        path_listing_containers_uuids mapping. If found, it retrieves and returns the corresponding
        PathListingContainer instance.

        Returns:
            PathListingContainer or None: The container associated with the current focus path,
            or None if no matching container is found.
        """
        focus_path = str(self.focus_path)
        if focus_path not in self.path_listing_containers_uuids:
            return
        container_uuid = self.path_listing_containers_uuids[focus_path]
        return self._get_container_by_uuid(container_uuid)

    def _get_container_by_uuid(
        self, container_uuid: str
    ) -> PathListingContainer | None:
        """
        Safely retrieve a PathListingContainer by its unique identifier.

        This method attempts to find a PathListingContainer widget within the current widget tree using its UUID. If
        no matching container is found, it returns None instead of raising an exception.

        Parameters:
            container_uuid (str): The unique identifier of the container to retrieve.

        Returns:
            PathListingContainer | None: The container with the specified UUID, or None if no matching container exists.

        Raises:
            NoMatches: Silently caught internally if no widget matches the UUID.
        """
        try:
            return self.query_one(f"#{container_uuid}")  # type: ignore
        except NoMatches:
            return None

    def _get_path_listing_container(self, path: Path) -> PathListingContainer | None:
        """
        Create a path listing container for a given directory path.

        Attempts to list directory contents using the file system service. If successful and the directory is not empty,
        returns a PathListingContainer with folder and file widgets.

        Parameters:
            path (Path): The directory path to list contents for

        Returns:
            - PathListingContainer | None: A container with folder and file widgets, or None if directory is empty or
            listing fails

        Raises:
            - Notifies user via self.notify() if directory listing encounters an error
        """
        try:
            dir_list = self.file_system_service.list_dir(path, relative_paths=False)
        except ListDirError as e:
            self.notify(str(e), markup=False)
            return

        if not dir_list.files and not dir_list.directories:
            return

        return PathListingContainer(
            *self.create_folder_widgets(dir_list.directories),
            *self.create_file_widgets(dir_list.files),
            id=generate_uuid(),
            classes="dir_listing",
            name=str(path),
        )

    async def _mount_path_listing_container(
        self, path_listing_container, mount_divider=True
    ):
        """
        Mount a new path listing container with an optional vertical divider.

        This asynchronous method mounts a path listing container into the current navigator,
        optionally adding a vertical divider before the container. After mounting, it focuses
        on the first child of the newly mounted container.

        Parameters:
            path_listing_container (PathListingContainer): The container to be mounted.
            mount_divider (bool, optional): Whether to add a vertical divider before the container.
                Defaults to True.

        Notes:
            - Uses asynchronous mounting to integrate with Textual's async UI framework
            - Automatically focuses the first child of the mounted container
            - Generates a unique divider ID based on the container's ID when a divider is mounted
        """
        if mount_divider:
            divider = Rule(
                orientation="vertical", id=f"{path_listing_container.id}-divider"
            )
            await self.mount(divider)

        await self.mount(path_listing_container)

    async def _clean_up_outdated_path_listing_containers(self, path):
        """
        Clean up path listing containers that are no longer part of the current navigation path.

        This asynchronous method removes UI containers and tracking entries for directories
        that are not parent directories of the current path. It helps manage memory and
        UI complexity by removing unnecessary navigation containers.

        Parameters:
            path (Path): The current active path used to determine which containers are outdated.

        Side Effects:
            - Removes child elements from the DOM for outdated containers
            - Removes entries from the path_listing_containers_uuids dictionary
        """
        outdated_containers = [
            (uuid, dir_name)
            for dir_name, uuid in self.path_listing_containers_uuids.items()
            if Path(dir_name) not in path.parents
        ]

        for uuid, dir_name in outdated_containers:
            await self.remove_children(f"#{uuid}")
            await self.remove_children(f"#{uuid}-divider")
            del self.path_listing_containers_uuids[dir_name]

    def _get_main_container(self):
        """
        Returns the main container for the current widget.

        This method is typically used to retrieve the primary container of the widget,
        which in this case is the widget itself. It provides a simple way to access
        the root container for further manipulation or reference.

        Returns:
            Widget: The current widget instance, serving as its own main container.
        """
        return self

    def watch_active_path(self):
        """
        Reactively post an ActivePathChanged message when the active path is updated.

        This method is a reactive watcher that sends a message with the current active path whenever it changes.
        It allows other components to be notified and respond to path navigation events.

        Attributes:
            active_path (Path): The currently selected path in the file system navigator.

        Emits:
            ActivePathChanged: A message containing the updated active path.
        """
        self.post_message(self.ActivePathChanged(self.active_path))

    @on(FileSystemWidget.FolderClick)
    async def on_folder_click(self, event: FileSystemWidget.FolderClick):
        """
        Handle a folder click event in the file system navigator.

        This asynchronous method is triggered when a user clicks on a folder, managing the navigation
        and display of the folder's contents. It performs the following key actions:
        - Retrieves the path listing container for the clicked folder
        - Cleans up any outdated path listing containers
        - Mounts the new path listing container
        - Tracks the UUID of the newly mounted container

        Args:
            event (FileSystemWidget.FolderClick): The folder click event containing the folder path

        Side Effects:
            - Mounts a new path listing container for the clicked folder
            - Removes outdated path listing containers
            - Updates the path_listing_containers_uuids dictionary

        Raises:
            Any exceptions from _clean_up_outdated_path_listing_containers or _mount_path_listing_container
        """
        folder_path = event.name
        path_listing_container = self._get_path_listing_container(folder_path)
        if not path_listing_container:
            return

        await self._clean_up_outdated_path_listing_containers(folder_path)
        await self._mount_path_listing_container(path_listing_container)

        if str(folder_path) not in self.path_listing_containers_uuids:
            self.path_listing_containers_uuids[str(folder_path)] = (
                path_listing_container.id
            )

    @on(FileSystemWidget.Focus)
    def on_folder_focus(self, event: FileSystemWidget.Focus):
        """
        Handle focus event for a folder in the file system navigator.

        This method updates the navigator's focus and active path when a folder widget receives focus.

        Parameters:
            event (FileSystemWidget.Focus): Focus event containing the path of the focused folder widget

        Side Effects:
            - Sets `self.focus_path` to the parent directory of the focused folder
            - Sets `self.active_path` to the path of the focused folder
        """
        self.focus_path = event.name.parent
        self.active_path = event.name

    @on(FileSystemWidget.FileDoubleClick)
    def on_file_doubleclick(self, event: FileSystemWidget.FileDoubleClick):
        """
        Handle a file double-click event by posting an ActivePathFileDoubleClicked message.

        This method is triggered when a user double-clicks on a file in the file system navigator. It forwards the file
        name to the parent component through a custom message.

        Parameters:
            event (FileSystemWidget.FileDoubleClick): The file double-click event containing the name of the clicked
            file.

        Raises:
            No explicit exceptions are raised by this method.
        """
        self.post_message(self.ActivePathFileDoubleClicked(event.name))

    @on(FileSystemWidget.FolderDoubleClick)
    def on_folder_doubleclick(self, event: FileSystemWidget.FolderDoubleClick):
        """
        Handle a folder double-click event by posting an ActivePathChanged message.

        This method is triggered when a user double-clicks on a folder in the file system navigator. It forwards the
        folder name to the parent component through a custom message.

        Parameters:
            event (FileSystemWidget.FolderDoubleClick): The folder double-click event containing the name of the
            clicked folder.

        Raises:
            No explicit exceptions are raised by this method.
        """
        self.post_message(self.ActivePathFileDoubleClicked(event.name))

    @staticmethod
    def _get_next_element(
        elements: Sequence[Widget],
        direction: Literal["up", "down"],
        selector: Callable,
        of_type: type | None = None,
    ) -> Widget | None:
        """
        Determine the next element in a sequence based on navigation direction and selection criteria.

        This method helps with navigating through a sequence of widgets, supporting circular navigation
        and optional type filtering.

        Parameters:
            elements (Sequence[Widget]): A sequence of widgets to navigate through.
            direction (Literal["up", "down"]): The navigation direction, either upward or downward.
            selector (Callable): A function to identify the currently focused element.
            of_type (Type, optional): A specific widget type to filter the elements. Defaults to None.

        Returns:
            Widget | None: The next widget in the sequence, or None if no valid elements exist.
            If no element is currently focused, returns the first element.
            Supports circular navigation, wrapping around to the start/end of the sequence.

        Behavior:
            - If no elements are provided, returns None
            - If type filtering is specified, filters elements by the given type
            - Finds the currently focused element using the provided selector
            - Determines the next element based on the navigation direction
            - Implements circular navigation (wraps around when reaching sequence boundaries)
        """
        if not elements:
            return

        if of_type:
            elements = [i for i in elements if isinstance(i, of_type)]

        if not elements:
            return

        focused_children = [
            index for index, child in enumerate(elements) if selector(child)
        ]
        if not focused_children:
            return elements[0]

        focused_index = focused_children[0]

        if direction == "down":
            focused_index += 1
            if focused_index == len(elements):
                focused_index = 0
        elif direction == "up":
            if focused_index == 0:
                focused_index = len(elements)
            focused_index -= 1
        return elements[focused_index]

    @staticmethod
    def create_folder_widgets(folders: list[Path]) -> list[FileSystemWidget]:
        """
        Create a list of FileSystemWidget instances representing folders.

        Parameters:
            folders (list[Path]): A list of directory paths to convert into widgets.

        Returns:
            list[FileSystemWidget]: A list of FileSystemWidget instances, each representing a folder
            with a predefined directory icon and CSS class for styling.
        """
        return [
            FileSystemWidget(
                folder,
                icon=DIRECTORY_ICON,
                classes=FileSystemNavigatorClasses.DIRECTORY_LISTING_FOLDER.value,
            )
            for folder in folders
        ]

    @staticmethod
    def create_file_widgets(files: list[Path]) -> list[FileSystemWidget]:
        """
        Create a list of FileSystemWidget instances for the given files.

        Parameters:
            files (list[Path]): A list of file paths to convert into FileSystemWidget instances.

        Returns:
            list[FileSystemWidget]: A list of FileSystemWidget objects representing the input files,
            each configured with a file icon and the appropriate CSS class for file listing.
        """
        return [
            FileSystemWidget(
                file,
                icon=FILE_ICON,
                classes=FileSystemNavigatorClasses.DIRECTORY_LISTING_FILE.value,
            )
            for file in files
        ]

    @staticmethod
    def _has_focus(widget: Widget) -> bool:
        """
        Check if a given Textual widget currently has focus.

        Parameters:
            widget (Widget): The Textual widget to check for focus status.

        Returns:
            bool: True if the widget has focus, False otherwise.
        """
        return widget.has_focus

    @staticmethod
    def _focus_first_child(container):
        """
        Focus the first child of a given container.

        If the container has no children, this method does nothing. Otherwise, it sets focus
        to the first child widget in the container.

        Args:
            container (Widget): The container whose first child should receive focus.
        """
        if not container.children:
            return
        container.children[0].focus()
