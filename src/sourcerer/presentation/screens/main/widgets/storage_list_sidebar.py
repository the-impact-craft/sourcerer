"""Storage list sidebar widget for the Sourcerer application.

This module provides widgets for displaying and interacting with the list of
storage providers in the sidebar. It handles storage grouping by provider type
and selection of storage items.
"""

from collections import namedtuple
from itertools import groupby

from textual import events
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Label, Rule

from sourcerer.domain.shared.entities import StorageProvider
from sourcerer.domain.storage_provider.entities import Storage
from sourcerer.presentation.screens.main.messages.select_storage_item import (
    SelectStorageItem,
)
from sourcerer.presentation.screens.main.widgets.gradient import GradientWidget

STORAGE_ICONS = {
    StorageProvider.S3: "🟠",
    StorageProvider.GoogleCloudStorage: "🔵",
    StorageProvider.AzureStorage: "⚪️",
}
"""Mapping of storage provider types to their display icons."""


class StorageItem(Label):
    """Widget for displaying and interacting with a single storage item.

    This widget represents a storage instance in the sidebar list, allowing
    selection and visual feedback on hover.
    """

    DEFAULT_CSS = """
    StorageItem {
        width: 90%;
        padding-left: 1;
        height: auto;
        margin:0;
        text-overflow: ellipsis;
        text-wrap: nowrap;

        & > :hover {
            background: $warning;
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
        self.post_message(
            SelectStorageItem(
                self.storage_name, access_credentials_uuid=self.access_credentials_uuid
            )
        )


class StorageListSidebar(VerticalScroll):
    """Sidebar widget for displaying the list of storage providers.

    This widget manages the display of storage providers grouped by their type,
    showing provider icons and storage names in a scrollable list.

    Attributes:
        storages: Dictionary mapping provider types to lists of storage instances
    """

    storages: reactive[dict[str, list[Storage]]] = reactive({})
    last_update_timestamp: reactive[float] = reactive(0, recompose=True)

    DEFAULT_CSS = """
    StorageListSidebar {
        padding-right:  0;
        margin-right: 0;
        & > .storage-group {
            height: auto;
            margin-bottom: 1;
            #rule-left {
                width: 1;
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
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="header"):
            yield GradientWidget("🧙SOURCERER", id="left-middle")
        StorageData = namedtuple("Storage", ["access_credentials_uuid", "storage"])
        storages = [
            StorageData(access_credentials_uuid, storage)
            for access_credentials_uuid, storages in self.storages.items()
            for storage in storages
        ]
        storages = sorted(storages, key=lambda x: x.storage.storage)

        for letter, storages_group in groupby(
            storages, key=lambda x: x.storage.storage[0]
        ):
            with Container(id=f"group-{letter}", classes="storage-group"):
                yield Horizontal(
                    Rule(id="rule-left"),
                    Label(letter.upper(), classes="storage-letter"),
                    Rule(),
                )

                for item in storages_group:
                    yield StorageItem(
                        renderable=STORAGE_ICONS.get(item.storage.provider, "")
                        + " "
                        + item.storage.storage,
                        storage_name=item.storage.storage,
                        access_credentials_uuid=item.access_credentials_uuid,
                    )
