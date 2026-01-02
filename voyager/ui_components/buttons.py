from importlib.resources import files

from textual.widgets import Button


class SmallButton(Button):
    """Compact button with Voyager styling."""

    DEFAULT_CSS = files("voyager.ui_components").joinpath("styles/buttons.tcss").read_text()

    def __init__(self, label: str, *, variant: str = "default", **kwargs) -> None:
        super().__init__(label, **kwargs)
        self.set_variant(variant)

    def set_variant(self, variant: str) -> None:
        self.remove_class("btn-primary", "btn-ghost")
        if variant == "primary":
            self.add_class("btn-primary")
        elif variant == "ghost":
            self.add_class("btn-ghost")
