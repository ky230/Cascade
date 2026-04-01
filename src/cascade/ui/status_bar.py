"""Bottom status bar widget — shows cwd, provider, model."""
from __future__ import annotations

import os
from textual.widgets import Static
from rich.text import Text


class StatusBarWidget(Static):
    """Fixed 1-row footer showing context info."""

    def __init__(self, provider: str, model: str, **kwargs):
        super().__init__(**kwargs)
        self.provider = provider
        self.model = model

    def render(self) -> Text:
        cwd = os.getcwd()
        # Shorten home directory
        home = os.path.expanduser("~")
        if cwd.startswith(home):
            cwd = "~" + cwd[len(home):]

        return Text.from_markup(
            f"[dim]{cwd}[/dim]"
            f"    [#44aacc]{self.provider}[/#44aacc]"
            f"  [dim]·[/dim]  [#44aacc]{self.model}[/#44aacc]"
        )
