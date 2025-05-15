from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from dependency_injector.wiring import Provide
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Static

from sourcerer.infrastructure.file_system.services import FileSystemService
from sourcerer.presentation.di_container import DiContainer
from sourcerer.presentation.screens.file_system_finder.widgets.file_system_navigator import (
    FileSystemNavigator,
)
from sourcerer.presentation.screens.shared.widgets.button import Button


@dataclass
class FileSystemSelectionValidationRule:
    action: Callable[[Path], bool]
    error_message: str


class FileSystemNavigationModal(ModalScreen):
    CONTAINER_ID = "file_system_view_container"
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Pop screen"),
    ]

    active_path: reactive[Path] = reactive(Path())

    def __init__(
        self,
        *args,
        file_system_service: FileSystemService = Provide[
            DiContainer.file_system_service
        ],
        validation_rules: list[FileSystemSelectionValidationRule] | None = None,
        **kwargs,
    ):
        """
        Initialize a FileSystemNavigationModal with file system navigation configuration.

        Arguments:
            file_system_service (FileSystemService, optional): Service for file system operations.
                Defaults to dependency injection from DiContainer.
            work_dir (Path, optional): Working directory for file navigation.
                Defaults to dependency injection from DiContainer configuration.
            validation_rules (List[FileSystemSelectionValidationRule], optional): Rules for validating file selections.
                Defaults to an empty list if not provided.
            *args: Variable positional arguments passed to parent class constructor.
            **kwargs: Variable keyword arguments passed to parent class constructor.

        Raises:
            TypeError: If validation rules are not instances of FileSystemSelectionValidationRule,
                       or if file_system_service is not a FileSystemService or work_dir is not a Path.

        Notes:
            - Validates input types before setting instance attributes
            - Logs an error and raises TypeError for invalid input types
            - Ensures type safety for file system navigation configuration
        """
        super().__init__(*args, **kwargs)

        if not validation_rules:
            validation_rules = []

        if not all(
            isinstance(rule, FileSystemSelectionValidationRule)
            for rule in validation_rules
        ):
            self.log.error("Invalid validation rules provided")
            raise TypeError(
                "Each validation rule must be an instance of FileSystemSelectionValidationRule"
            )

        self.file_system_service = file_system_service
        self.work_dir = file_system_service.work_dir
        self.validation_rules = validation_rules

    def compose(self) -> ComposeResult:
        """
        Compose the user interface for the file system navigation modal.

        This method sets up the modal's layout with three primary components:
        1. A static label to display the current active path
        2. A file system navigator for browsing and selecting files/directories
        3. Control buttons for closing or applying the current selection

        Returns:
            ComposeResult: A generator yielding the modal's UI components, including a path label,
            file system navigator, and control buttons.

        Components:
            - Static label with ID "active-path" for displaying the current path
            - FileSystemNavigator configured with the current working directory and file system service
            - Horizontal layout of "Close" and "Apply" buttons with the ID "controls"
        """
        with Container(id=self.CONTAINER_ID):
            yield Static("", id="active-path")
            yield FileSystemNavigator(
                work_dir=self.work_dir, file_system_service=self.file_system_service
            )
            yield Horizontal(
                Button("Close", name="close", id="close", classes="button"),
                Button("Apply", name="apply", id="apply", classes="button"),
                id="controls",
            )

    @on(Button.Click)
    def on_button_click(self, event: Button.Click):
        """
        Handle button click events for the file system navigation modal.
        This method is triggered when the user clicks either the "Close" or "Apply" button.
        It determines the action to take based on the button clicked.

        Args:
            event (Button.Click): The event containing the button that was clicked.
        """
        if event.action == "close":
            self.on_close()
        else:
            self.on_apply()

    @on(FileSystemNavigator.ActivePathChanged)
    def on_active_path_changed(self, event: FileSystemNavigator.ActivePathChanged):
        """
        Update the active path label when the file system navigator's active path changes.

        This method is triggered by the `ActivePathChanged` event from the file system navigator. It updates
        the displayed path label and sets the `active_path` attribute of the modal.

        Arguments:
            event (FileSystemNavigator.ActivePathChanged): Event containing the newly selected path

        Behavior:
            - Silently returns if the event path is empty
            - Attempts to find the active path label with ID "active-path"
            - If label is not found, silently returns
            - Calculates the relative path from the working directory
            - Appends "/" to the label if the path is a directory
            - Updates the label with the calculated path
            - Sets the `active_path` attribute to the selected path

        Exceptions:
            - Handles `NoMatches` exception if the active path label cannot be found
        """
        if not event.path:
            return
        try:
            active_path_label: Static = self.query_one("#active-path")  # type: ignore
        except NoMatches:
            return
        label = str(event.path.relative_to(self.work_dir))
        if event.path.is_dir():
            label += "/"
        active_path_label.update(label)
        self.active_path = event.path

    @on(FileSystemNavigator.ActivePathFileDoubleClicked)
    def on_path_double_clicked(
        self, event: FileSystemNavigator.ActivePathFileDoubleClicked
    ):
        """
        Handle the event when a file is double-clicked in the file system navigator.

        Validates the selected file path and either dismisses the modal with the selected path or displays an error
        notification.

        Arguments:
            event (FileSystemNavigator.ActivePathFileDoubleClicked): The event containing the double-clicked file path.

        Behavior:
            - If no path is provided, the method returns without action.
            - Validates the path using the `validate_path` method.
            - If the path is invalid, displays an error notification with validation details.
            - If the path is valid, dismisses the modal and returns the selected path.
        """
        if not event.path:
            return
        valid_status, details = self.validate_path(event.path)
        if not valid_status:
            self.notify(details, severity="error")
        else:
            self.dismiss(event.path)

    def validate_path(self, path: Path) -> tuple[bool, str]:
        """
        Validate the given path against a set of predefined validation rules.

        Iterates through the validation rules and checks each rule's action against the provided path.
        If any rule fails or raises an exception, the path is considered invalid.

        Arguments:
            path (Path): The file system path to validate.

        Returns:
            tuple[bool, str]: A tuple containing:
                - A boolean indicating whether the path is valid (True) or invalid (False)
                - A string with error details if validation fails, otherwise an empty string

        Notes:
            - If no validation rules are defined, the path is considered valid by default.
            - Stops validation on the first failed rule and returns its error message.
            - Catches and handles any exceptions raised during rule validation.
        """
        for rule in self.validation_rules or []:
            try:
                if not rule.action(path):
                    return False, rule.error_message
            except Exception:
                return False, rule.error_message
        return True, ""

    def on_close(self):
        """
        Dismiss the file system navigation modal without selecting a path.

        This method is triggered when the user clicks the close button or uses the designated close action.
        It immediately closes the modal screen and returns None, indicating no file was selected.

        """
        self.dismiss(None)

    def on_apply(self):
        """
        Handle the apply action in the file system navigation modal.

        Validates the currently selected path and either dismisses the modal with the selected path
        or displays an error notification if the path is invalid.

        Side Effects:
            - Calls `self.validate_path()` to check path validity
            - Displays an error notification if path is invalid
            - Dismisses the modal with the selected path if valid
        """
        valid_status, details = self.validate_path(self.active_path)
        if not valid_status:
            self.notify(details, severity="error")
        else:
            self.dismiss(self.active_path)
