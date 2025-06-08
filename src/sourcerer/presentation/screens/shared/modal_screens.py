from typing import ClassVar

from textual.binding import Binding, BindingType
from textual.screen import ModalScreen


class ExitBoundModalScreen(ModalScreen):
    """
    A base class for modal screens that can be exited.
    It provides a method to exit the screen and a flag to indicate if the screen should be exited.
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "cancel_screen", "Pop screen"),
    ]

    def action_cancel_screen(self):
        """
        Action to exit the screen.
        """
        self.dismiss()


class RefreshTriggerableModalScreen(ExitBoundModalScreen):
    """
    A base class for modal screens that can be refreshed.
    It provides a method to refresh the screen and a flag to indicate if the screen should be refreshed.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._requires_storage_refresh = False

    def action_cancel_screen(self):
        requires_storage_refresh = self._requires_storage_refresh
        self._requires_storage_refresh = False
        self.dismiss(requires_storage_refresh)
