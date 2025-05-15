import contextlib
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.color import Gradient
from textual.containers import Center, Container, Horizontal, VerticalScroll
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Label, ProgressBar, Rule

from sourcerer.domain.storage_provider.services import BaseStorageProviderService
from sourcerer.infrastructure.storage_provider.exceptions import (
    UploadStorageItemsError,
)
from sourcerer.presentation.screens.question.main import QuestionScreen
from sourcerer.presentation.screens.shared.widgets.button import Button
from sourcerer.settings import MAX_PARALLEL_DOWNLOADS

gradient = Gradient.from_colors(
    "#881177",
    "#aa3355",
    "#cc6666",
    "#ee9944",
    "#eedd00",
    "#99dd55",
    "#44dd88",
    "#22ccbb",
    "#00bbcc",
    "#0099cc",
    "#3366bb",
    "#663399",
)

gradient2 = Gradient.from_colors(
    "#aa3355",
    "#663399",
    "#0099cc",
)


@dataclass
class Key:
    """
    Base class for representing a key in storage operations.

    Attributes:
        display_name (str): Name to display in the UI
        uuid (str): Unique identifier for the key
        path (str): Path to the file or directory
    """

    display_name: str
    uuid: str
    path: Path


class DownloadKey(Key):
    """
    Represents a key for download operations.

    Inherits all attributes from the base Key class.
    """


class DeleteKey(Key):
    """
    Represents a key for delete operations.

    Inherits all attributes from the base Key class.
    """


@dataclass
class UploadKey(Key):
    """
    Represents a key for upload operations.

    Inherits all attributes from the base Key class and adds destination path.

    Attributes:
        dest_path (str): Destination path for the uploaded file
    """

    dest_path: str


class StorageActionProgressScreen(ModalScreen):
    """
    A modal screen that displays progress for storage operations (download, upload, delete).

    This screen shows progress bars for the overall operation and for individual files,
    allowing users to monitor and cancel operations in progress.
    """

    CSS_PATH = "styles.tcss"

    files_has_been_processed = reactive(False)

    def __init__(
        self,
        storage_name: str,
        path: str,
        provider_service: BaseStorageProviderService | None,
        keys: list[UploadKey | DownloadKey | DeleteKey],
        action: str,
        *args,
        **kwargs,
    ):
        """
        Initialize the storage action progress screen.

        Args:
            storage_name (str): Name of the storage being operated on
            path (str): Path within the storage
            provider_service (BaseStorageProviderService | None): Service for interacting with the storage provider
            keys (list[Key]): List of keys representing files/folders to process
            action (str): Type of action being performed ('download', 'upload', or 'delete')
            *args: Additional positional arguments to pass to parent class
            **kwargs: Additional keyword arguments to pass to parent class
        """
        super().__init__(*args, **kwargs)
        self.storage_name = storage_name
        self.provider_service = provider_service
        self.action = action
        self.path = path
        self.keys = keys
        self.active_worker = None
        self.active_executor = None

    def compose(self) -> ComposeResult:
        """
        Compose the UI elements of the screen.

        Creates a container with a main progress bar, individual progress bars for each file,
        and a cancel button.

        Returns:
            ComposeResult: The composed UI elements
        """
        with Container(id="StorageActionProgress"):
            with Center():
                yield ProgressBar(
                    show_eta=False,
                    total=len(self.keys),
                    id="progress_bar",
                    gradient=gradient2,
                )

            yield Rule()

            with VerticalScroll(id="progress_files"):
                for key in self.keys:
                    with Horizontal(
                        classes="progress_file", id=f"progress_files_{key.uuid}"
                    ):
                        yield Label(
                            Text(key.display_name, overflow="ellipsis"),
                            id=f"progress_file_{key.uuid}",
                            classes="label",
                        ).with_tooltip(key.display_name)
                        yield ProgressBar(
                            total=1,
                            show_percentage=False,
                            id=f"progress_bar_{key.uuid}",
                            gradient=gradient2,
                        )
                    if Path(key.path).is_dir():
                        with Horizontal(classes="progress_file_details"):
                            yield Label(
                                "",
                                id=f"progress_file_details_{key.uuid}",
                                classes="label",
                            )
            with Horizontal(id="controls"):
                yield Button("Cancel", name="cancel")

    def on_mount(self) -> None:
        """
        Handle the mount event when the screen is first displayed.

        Sets the border title and starts the appropriate worker thread based on the action type
        (download, delete, or upload).
        """
        self.query_one("#StorageActionProgress").border_title = (
            f"{self.action.capitalize()} {len(self.keys)} files from {self.storage_name}"
        )

        if self.action == "download":
            self.active_worker = self.run_worker(self.download_files, thread=True)
        elif self.action == "delete":
            self.action_worker = self.run_worker(self.delete_files, thread=True)
        elif self.action == "upload":
            self.action_worker = self.run_worker(self.upload_files, thread=True)

    @on(Button.Click)
    def on_button_click(self, event: Button.Click) -> None:
        """
        Handle button click events.

        Processes the cancel button click by either dismissing the screen if processing is complete
        or showing a confirmation dialog if processing is still in progress.

        Args:
            event (Button.Click): The button click event
        """
        if event.action != "cancel":
            return

        if self.files_has_been_processed:
            self.dismiss()
            return

        self.app.push_screen(
            QuestionScreen("Are you sure you want to cancel process?"),
            callback=self.exit_callback,
        )

    def exit_callback(self, result):
        """
        Callback function to handle the result of the confirmation dialog.
        If the user confirms, it cancels the ongoing operation and dismisses the screen.
        Args:
            result (bool): The result of the confirmation dialog

        """
        if not result:
            return
        if self.active_executor:
            self.active_executor.shutdown(cancel_futures=True)
            self.active_executor = None
        if self.active_worker:
            self.active_worker.cancel()
            self.active_worker = None
        self.dismiss()

    async def download_files(self):
        """
        Download files from storage and update progress bars.
        This method handles the download of multiple files, updating progress bars
        and handling various error conditions that might occur during the process.
        """
        main_progress_bar = self.query_one("#progress_bar")
        failed_downloads = []

        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_DOWNLOADS) as executor:
            self.active_executor = executor
            futures = [
                executor.submit(
                    self.download_file,
                    os.path.join(self.path, key.path) if self.path else key.path,
                    key.uuid,
                    main_progress_bar,
                )
                for key in self.keys
            ]

            for future in as_completed(futures):
                if future.exception():
                    failed_downloads.append(future)
            self.files_has_been_processed = True

        self.active_executor = None
        if failed_downloads:
            self.notify(
                f"Failed to download {len(failed_downloads)} files", severity="error"
            )

    def download_file(self, key, uuid, main_progress_bar):
        """
        Download a file from storage and update progress bars.

        This method handles the download of a single file, updating progress bars
        and handling various error conditions that might occur during the process.

        Args:
            key (str): The key/path of the file to download
            uuid (str): Unique identifier for the file
            main_progress_bar (ProgressBar): The main progress bar to update
        """

        if not self.provider_service:
            self.notify(f"Failed to download {key}", severity="error")
            return

        def progress_callback(progress_bar, chunk):
            progress_bar.advance(chunk)

        progress_bar = self.query_one(f"#progress_bar_{uuid}")

        try:
            # Step 1: Get file size
            try:
                file_size = self.provider_service.get_file_size(self.storage_name, key)
                progress_bar.total = file_size  # type: ignore
            except Exception as ex:
                self.notify(
                    f"Failed to get file size for {key}: {str(ex)}", severity="error"
                )
                self.log.error(f"Error getting file size: {ex}")
                return

            # Step 2: Download the file
            try:
                self.provider_service.download_storage_item(
                    self.storage_name,
                    key,
                    lambda chunk: progress_callback(progress_bar, chunk),
                )
            except Exception as ex:
                self.notify(f"Failed to download {key}: {str(ex)}", severity="error")
                self.log.error(f"Error downloading file: {ex}")
                return

            # Step 3: Ensure progress bar is complete
            if progress_bar.progress != progress_bar.total:  # type: ignore
                try:
                    progress_bar.progress = file_size  # type: ignore
                except Exception as ex:
                    self.log.error(f"Error updating progress bar: {ex}")
                    # Non-critical error, continue execution
        except Exception as ex:
            # Catch any unexpected exceptions
            self.notify(
                f"Unexpected error downloading {key}: {str(ex)}", severity="error"
            )
            self.log.error(f"Unexpected error: {ex}")
        finally:
            main_progress_bar.advance(1)

    async def delete_files(self):
        """
        Delete files from storage and update progress bars.

        This method handles the deletion of multiple files, updating progress bars
        and handling various error conditions that might occur during the process.
        """
        main_progress_bar = self.query_one("#progress_bar")
        failed_downloads = []

        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_DOWNLOADS) as executor:
            self.active_executor = executor
            futures = [
                executor.submit(
                    self.delete_file,
                    os.path.join(self.path, key.path) if self.path else key.path,
                    key.uuid,
                    main_progress_bar,
                )
                for key in self.keys
            ]

            for future in as_completed(futures):
                if future.exception():
                    failed_downloads.append(future)
            self.files_has_been_processed = True

        self.active_executor = None

    def delete_file(self, key, uuid, main_progress_bar):
        """
        Delete a file from storage and update progress bars.

        This method handles the deletion of a single file, updating progress bars
        and handling various error conditions that might occur during the process.

        Args:
            key (str): The key/path of the file to delete
            uuid (str): Unique identifier for the file
            main_progress_bar (ProgressBar): The main progress bar to update
        """ ""
        if not self.provider_service:
            self.notify(f"Failed to delete {key}", severity="error")
            main_progress_bar.advance(1)
            return

        progress_bar = self.query_one(f"#progress_bar_{uuid}")
        try:
            progress_bar.total = 1  # type: ignore
            self.provider_service.delete_storage_item(self.storage_name, key)
            progress_bar.advance(1)  # type: ignore
        except Exception:
            self.notify(f"Failed to delete {key}", severity="error")
            raise
        finally:
            main_progress_bar.advance(1)

    async def upload_files(self):
        """
        Upload files to storage and update progress bars.

        This method handles the upload of files, updating progress bars and
        handling various error conditions that might occur during the process.
        """
        main_progress_bar = self.query_one("#progress_bar")
        failed_downloads = []
        if not self.provider_service:
            self.notify("Failed to upload files", severity="error")
            return

        for key in self.keys:
            source_path = Path(key.path)
            if source_path.is_file():
                try:
                    self.provider_service.upload_storage_item(
                        storage=self.storage_name,
                        storage_path=self.path,
                        source_path=key.path,
                        dest_path=key.dest_path,  # type: ignore
                    )
                    progress_bar = self.query_one(f"#progress_bar_{key.uuid}")
                    progress_bar.advance(1)  # type: ignore
                except UploadStorageItemsError as e:
                    self.notify(f"Failed to upload {key.path}: {e}", severity="error")
                finally:
                    self.files_has_been_processed = True
            elif source_path.is_dir():

                files_n = len([i for i in source_path.rglob("*") if i.is_file()])
                progress_bar = self.query_one(f"#progress_bar_{key.uuid}")
                progress_bar.total = files_n  # type: ignore
                with ThreadPoolExecutor(max_workers=MAX_PARALLEL_DOWNLOADS) as executor:
                    self.active_executor = executor
                    futures = [
                        executor.submit(
                            self.upload_file,
                            obj,
                            Path(obj).relative_to(source_path),
                            os.path.join(
                                source_path.name,
                                str(Path(obj).relative_to(source_path)),
                            ),
                            key.uuid,
                        )
                        for obj in source_path.rglob("*")
                        if obj.is_file()
                    ]

                    for future in as_completed(futures):
                        if future.exception():
                            failed_downloads.append(future)
                    self.files_has_been_processed = True
                self.active_executor = None
                try:
                    self.query_one(f"#progress_file_details_{key.uuid}").remove()
                except Exception:
                    self.log(f"Failed to remove progress details for {key.uuid}")
            main_progress_bar.advance(1)  # type: ignore

    def upload_file(self, source, rel_source, destination, uuid):
        """
        Upload a file to storage and update progress bars.

        This method handles the upload of a single file, updating progress bars
        and handling various error conditions that might occur during the process.
        Args:
            source (str): The source path of the file to upload
            rel_source (str): The relative path of the file in the source directory
            destination (str): The destination path in the storage
            uuid (str): Unique identifier for the file
        """
        if not self.provider_service:
            self.notify(f"Failed to upload {source}", severity="error")
            return
        progress_bar = self.query_one(f"#progress_bar_{uuid}")
        details_container = None
        with contextlib.suppress(NoMatches):
            details_container = self.query_one(f"#progress_file_details_{uuid}")
        if details_container:
            details_container.update(Text(f"({rel_source})", overflow="ellipsis"))  # type: ignore
        try:
            self.provider_service.upload_storage_item(
                storage=self.storage_name,
                storage_path=self.path,
                source_path=source,
                dest_path=destination,
            )
            progress_bar.advance(1)  # type: ignore
        except UploadStorageItemsError as e:
            self.notify(f"Failed to upload {source}: {e}", severity="error")

    def watch_files_has_been_processed(self):
        if self.files_has_been_processed:
            self.notify(f"{self.action.capitalize()} operation is completed")
            self.query_one("#StorageActionProgress").add_class("success")
