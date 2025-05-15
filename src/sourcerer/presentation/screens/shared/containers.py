from textual.containers import HorizontalScroll, ScrollableContainer, VerticalScroll


class ScrollableContainerWithNoBindings(ScrollableContainer, inherit_bindings=False):
    pass


class ScrollHorizontalContainerWithNoBindings(HorizontalScroll, inherit_bindings=False):
    pass


class ScrollVerticalContainerWithNoBindings(VerticalScroll, inherit_bindings=False):
    pass
