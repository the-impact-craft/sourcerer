"""Storage list sidebar widget for the Sourcerer application.

This module provides widgets for displaying and interacting with the list of
storage providers in the sidebar. It handles storage grouping by provider type
and selection of storage items.
"""

from collections import namedtuple
from dataclasses import dataclass
from itertools import groupby
from typing import Self

from textual import events, on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Label, Rule

from sourcerer.domain.shared.entities import StorageProvider
from sourcerer.domain.storage_provider.entities import Storage
from sourcerer.presentation.screens.main.messages.refresh_storages_list_request import (
    RefreshStoragesListRequest,
)
from sourcerer.presentation.screens.main.messages.select_storage_item import (
    SelectStorageItem,
)
from sourcerer.presentation.screens.main.widgets.gradient import GradientWidget
from sourcerer.presentation.screens.shared.containers import (
    ScrollVerticalContainerWithNoBindings,
)
from sourcerer.presentation.screens.shared.widgets.button import Button
from sourcerer.presentation.screens.shared.widgets.spinner import Spinner
from sourcerer.presentation.settings import KeyBindings

"""Mapping of storage provider types to their display icons."""
STORAGE_ICONS = {
    StorageProvider.S3: "🟠",
    StorageProvider.GoogleCloudStorage: "🔵",
    StorageProvider.AzureStorage: "⚪️",
}

StorageData = namedtuple("Storage", ["access_credentials_uuid", "storage"])


class StorageItem(Label):
    """Widget for displaying and interacting with a single storage item.

    This widget represents a storage instance in the sidebar list, allowing
    selection and visual feedback on hover.
    """

    can_focus = True
    selected = reactive(False, recompose=True, toggle_class="selected")

    DEFAULT_CSS = """
    StorageItem {
        width: 90%;
        padding-left: 1;
        height: auto;
        margin:0;
        text-overflow: ellipsis;
        text-wrap: nowrap;

        & > :hover {
            background: $primary-lighten-2;
            color: $panel;
        }

        & > :focus {
            background: $primary-lighten-2;
            color: $panel;
        }

        &.selected {
            background: $primary;
            color: $panel;
        }
    }
    """

    def __init__(self, storage_name, access_credentials_uuid, *args, **kwargs):
        """Initialize a storage item widget.

        Args:
            storage_name: The name of the storage instance
            access_credentials_uuid: UUID of the access credentials being used
        """
        self.storage_name = storage_name
        self.access_credentials_uuid = access_credentials_uuid

        super().__init__(*args, **kwargs)

    def on_click(self, _: events.Click) -> None:
        """Handle click events to select the storage item."""
        self._select_storage()

    def on_key(self, event: events.Key) -> None:
        """Handle key events to select the storage item."""
        if event.key == KeyBindings.ENTER.value:
            self._select_storage()
            return
        storages = [
            component
            for component in self.screen.focus_chain
            if isinstance(component, StorageItem)
        ]
        if not storages:
            return
        if event.key == KeyBindings.ARROW_DOWN.value:
            if self.screen.focused == storages[-1]:
                storages[0].focus()
                return
            self.screen.focus_next(StorageItem)
        elif event.key == KeyBindings.ARROW_UP.value:
            if self.screen.focused == storages[0]:
                storages[-1].focus()
                return
            self.screen.focus_previous(StorageItem)

    def _select_storage(self):
        """
        Select the storage item and notify the application.
        This method posts a message to select the storage item based on its
        name and access credentials UUID.

        """
        self.post_message(
            SelectStorageItem(
                self.storage_name, access_credentials_uuid=self.access_credentials_uuid
            )
        )


class StorageCredentialsDivider(Horizontal):
    @dataclass
    class Click(Message):
        credentials_uuid: str

    collapsed: reactive[bool] = reactive(False, recompose=True)

    def __init__(self, credential_name, credentials_uuid, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.credential_name = credential_name
        self.credentials_uuid = credentials_uuid

    def compose(self) -> ComposeResult:
        yield Rule(classes="storage-credentials-rule-left")
        yield Label(
            renderable=("> " if self.collapsed else "⌄ ")
            + self.credential_name.upper(),
            classes="storage-credentials-name",
        )
        yield Rule(classes="storage-credentials-rule-right")

    def on_click(self):
        self.post_message(self.Click(self.credentials_uuid))


class StorageListSidebar(Vertical):
    """Sidebar widget for displaying the list of storage providers.

    This widget manages the display of storage providers grouped by their type,
    showing provider icons and storage names in a scrollable list.

    Attributes:
        storages: Dictionary mapping provider types to lists of storage instances
    """

    is_loading: reactive[bool] = reactive(False, recompose=True)
    groupby_access_credentials: reactive[bool] = reactive(False, recompose=True)
    storages: reactive[dict[tuple[str, str], list[Storage]]] = reactive({})
    last_update_timestamp: reactive[float] = reactive(  # ty: ignore[invalid-assignment]
        0.0, recompose=True
    )

    DEFAULT_CSS = """
    StorageListSidebar {
        padding-right:  0;
        margin-right: 0;
        height: 100%;
        margin-bottom: 1;
        .rule-left {
            width: 1;
            color: $background-lighten-3;
        }

        .storage-credentials-container-name {
            margin-top: 1;

            & > :first-of-type {
                margin-top: 0;
            }
        }

        .storage-credentials-container {
            display: none;
            height: auto;
            &.-visible {
                display: block;
            }
        }

        ScrollVerticalContainerWithNoBindings{
            height: 95%;

            & > Horizontal {
              height: auto;

              & > .storage-credentials-name {
                    color: $secondary;
                    padding: 0 1;
                }

              & > Rule {
                    color: $background-lighten-3;
              }

              & > Rule.storage-credentials-rule-left {
                    width: 1;
                    color: $secondary;
                }
              & > Rule.storage-credentials-rule-right {
                    color: $secondary;
                }

            }
        }

        Horizontal {
            height: auto;
        }
        Rule.-horizontal {
            height: 1;
            margin: 0 0;

        }
        .storage-letter {
            color: $secondary;
            padding: 0 1;
        }

    }
    #header {
        width: 100%;

        GradientWidget {
            width: auto;
        }

        Spinner {
            width: 5%;
        }
    }
    """

    def __init__(self, groupby_access_credentials, *args, **kwargs):
        """Initialize the StorageListSidebar widget."""
        super().__init__(*args, **kwargs)
        self.groupby_access_credentials = groupby_access_credentials

    def render_ungrouped_storages(self) -> ComposeResult:
        storages = [
            StorageData(access_credentials_uuid, storage)
            for (
                access_credentials_uuid,
                access_credentials_name,
            ), storages in self.storages.items()
            for storage in storages
        ]
        storages = sorted(storages, key=lambda x: x.storage.storage)
        with ScrollVerticalContainerWithNoBindings():
            for letter, storages_group in groupby(
                storages, key=lambda x: x.storage.storage[0]
            ):
                yield Horizontal(
                    Rule(classes="rule-left"),
                    Label(letter.upper(), classes="storage-letter"),
                    Rule(),
                    classes="storage-letter-container",
                )
                for item in storages_group:
                    yield StorageItem(
                        renderable=f"{STORAGE_ICONS.get(item.storage.provider, '')} {item.storage.storage}",
                        storage_name=item.storage.storage,
                        access_credentials_uuid=item.access_credentials_uuid,
                    )

    def render_grouped_by_access_credentials_storages(self) -> ComposeResult:
        """Render storages grouped by access credentials."""
        with ScrollVerticalContainerWithNoBindings():
            for (
                access_credentials_uuid,
                access_credentials_name,
            ), storages in self.storages.items():
                storages = sorted(
                    [
                        StorageData(access_credentials_uuid, storage)
                        for storage in storages
                    ],
                    key=lambda x: x.storage.storage,
                )
                yield StorageCredentialsDivider(
                    credential_name=access_credentials_name,
                    credentials_uuid=access_credentials_uuid,
                    classes="storage-credentials-container-name -visible",
                    id=f"{access_credentials_uuid}_container_title",
                )
                with Container(
                    classes="storage-credentials-container -visible",
                    id=f"{access_credentials_uuid}_container",
                ):
                    for letter, storages_group in groupby(
                        storages, key=lambda x: x.storage.storage[0]
                    ):
                        yield Horizontal(
                            Rule(classes="rule-left"),
                            Label(letter.upper(), classes="storage-letter"),
                            Rule(),
                            classes="storage-letter-container",
                        )
                        for item in storages_group:
                            yield StorageItem(
                                renderable=f"{STORAGE_ICONS.get(item.storage.provider, '')} {item.storage.storage}",
                                storage_name=item.storage.storage,
                                access_credentials_uuid=item.access_credentials_uuid,
                            )

    @on(StorageCredentialsDivider.Click)
    def on_credentials_divider_click(self, event: StorageCredentialsDivider.Click):
        uuid = event.credentials_uuid
        divider = self.query_one(f"#{uuid}_container_title", StorageCredentialsDivider)
        container = self.query_one(f"#{uuid}_container")
        divider.collapsed = not divider.collapsed
        container.toggle_class("-visible")

    def compose(self) -> ComposeResult:
        with Horizontal(id="header"):
            if self.is_loading:
                yield Spinner()
            yield GradientWidget(
                " SOURCERER" if self.is_loading else "🧙SOURCERER",
                id="left-middle",
                name="header_click",
            )
        if self.groupby_access_credentials:
            yield from self.render_grouped_by_access_credentials_storages()
        else:
            yield from self.render_ungrouped_storages()

    def focus(self, scroll_visible: bool = True) -> Self:
        try:
            content = self.query_one(StorageItem)
        except NoMatches:
            return self
        content.focus()
        return self

    @on(Button.Click)
    def on_button_click(self, event: Button.Click) -> None:
        """Handle button click events to refresh the storage list."""
        if event.action == "header_click":
            self.post_message(RefreshStoragesListRequest())

    @on(SelectStorageItem)
    def on_select_storage_item(self, event: SelectStorageItem) -> None:
        """Handle selection of a storage item."""
        for child in self.query(StorageItem):
            child.selected = (
                child.storage_name == event.name
                and child.access_credentials_uuid == event.access_credentials_uuid
            )
