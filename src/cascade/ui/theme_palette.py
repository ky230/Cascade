"""Inline theme selection dropdown — same UX as ModelPalette.

Shows color swatch + name + description for each theme.
Appears below the input prompt. ↑↓ navigate with live preview,
Enter select, Esc cancel (rolls back to original theme).
Focus stays on PromptInput at all times.
"""
from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import Static
from textual.message import Message

from cascade.ui.styles import THEMES, ThemeColors, get_tcss, hot_swap_css


class ThemePalette(Vertical):
    """Inline theme picker dropdown, appears below input like ModelPalette."""

    DEFAULT_CSS = """
    ThemePalette {
        height: auto;
        max-height: 10;
        background: #1a1a2e;
        padding: 0 0;
        margin: 0 1;
        display: none;
        overflow-y: auto;
    }
    """

    class Selected(Message):
        """Emitted when user selects a theme."""
        def __init__(self, theme_name: str) -> None:
            super().__init__()
            self.theme_name = theme_name

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._items: list[dict] = []
        self._highlight: int = 0
        self._original_theme: str = "dark"  # Stashed for Esc rollback

    def populate(self, current_theme: str) -> None:
        """Build items from THEMES and show the palette."""
        self._original_theme = current_theme
        self._items = []
        for name, colors in THEMES.items():
            self._items.append({
                "name": name,
                "description": colors.description,
                "accent": colors.accent,
                "is_current": name == current_theme,
            })

        # Pre-select current theme
        self._highlight = 0
        for i, item in enumerate(self._items):
            if item["is_current"]:
                self._highlight = i
                break

        self._render_items()
        self.display = True

    def _render_items(self) -> None:
        """Re-render all rows with highlight."""
        for child in list(self.children):
            child.remove()

        for i, item in enumerate(self._items):
            accent = item["accent"]
            marker = "●" if item["is_current"] else "○"
            name_padded = item["name"].ljust(8)
            current_tag = " ← current" if item["is_current"] else ""

            if i == self._highlight:
                # Active row: blue background, dark text
                markup = (
                    f"[bold #0d1117] [{accent}]■[/{accent}] "
                    f"{marker} {name_padded} — {item['description']}"
                    f"{current_tag} [/bold #0d1117]"
                )
                classes = "palette-item active"
            else:
                markup = (
                    f" [{accent}]■[/{accent}] "
                    f"[dim]{marker}[/dim] "
                    f"[bold white]{name_padded}[/bold white] — "
                    f"[dim]{item['description']}{current_tag}[/dim]"
                )
                classes = "palette-item"

            self.mount(Static(markup, classes=classes))

        # Scroll highlighted row into view
        if self._items:
            try:
                children = list(self.children)
                if self._highlight < len(children):
                    children[self._highlight].scroll_visible()
            except Exception:
                pass

    def _apply_preview(self) -> None:
        """Live-preview the highlighted theme without committing."""
        if not self._items:
            return
        theme_name = self._items[self._highlight]["name"]
        try:
            new_css = get_tcss(theme_name)
            hot_swap_css(self.app, new_css)
        except Exception:
            pass

    def move_up(self) -> None:
        if not self._items:
            return
        self._highlight = (self._highlight - 1) % len(self._items)
        self._render_items()
        self._apply_preview()

    def move_down(self) -> None:
        if not self._items:
            return
        self._highlight = (self._highlight + 1) % len(self._items)
        self._render_items()
        self._apply_preview()

    def select_current(self) -> bool:
        if not self._items:
            return False
        item = self._items[self._highlight]
        self.post_message(self.Selected(theme_name=item["name"]))
        self.display = False
        return True

    def cancel(self) -> None:
        """Cancel and roll back to the original theme."""
        # Roll back CSS to original theme
        try:
            original_css = get_tcss(self._original_theme)
            hot_swap_css(self.app, original_css)
            self.app._current_theme = self._original_theme
        except Exception:
            pass
        self.display = False

    @property
    def is_visible(self) -> bool:
        return self.display and bool(self._items)
