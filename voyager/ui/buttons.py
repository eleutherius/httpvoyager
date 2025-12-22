from textual.widgets import Button


class SmallButton(Button):
    """Compact button with Voyager styling."""

    DEFAULT_CSS = """
    SmallButton {
        height: 3;
        min-height: 3;
        padding: 0 3;
        border: tall #3b4f7a;
        background: #1c2943;
        color: #ffffff;
        text-style: bold;
        content-align: center middle;
        min-width: 12;
    }

    SmallButton:hover {
        background: #213355;
        border: tall #6fa6ff;
    }

    SmallButton:focus {
        border: tall #6fa6ff;
    }

    SmallButton.btn-primary {
        background: #4f8dff;
        border: tall #4f8dff;
        color: #0b1221;
    }

    SmallButton.btn-primary:hover {
        background: #6aa1ff;
        border: tall #6aa1ff;
    }

    SmallButton.btn-ghost {
        background: #233555;
        border: tall #3b4f7a;
        color: #f1f5ff;
    }

    SmallButton.btn-ghost:hover {
        border: tall #6fa6ff;
        color: #ffffff;
        background: #2d4470;
    }
    """

    def __init__(self, label: str, *, variant: str = "default", **kwargs) -> None:
        super().__init__(label, **kwargs)
        self.set_variant(variant)

    def set_variant(self, variant: str) -> None:
        self.remove_class("btn-primary", "btn-ghost")
        if variant == "primary":
            self.add_class("btn-primary")
        elif variant == "ghost":
            self.add_class("btn-ghost")
