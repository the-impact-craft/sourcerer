from textual.containers import ScrollableContainer, HorizontalScroll, VerticalScroll


class ScrollableContainerWithNoBindings(ScrollableContainer, inherit_bindings=False):
    pass


class ScrollHorizontalContainerWithNoBindings(HorizontalScroll, inherit_bindings=False):
    pass


class ScrollVerticalContainerWithNoBindings(VerticalScroll, inherit_bindings=False):
    pass
