"""Inline model selection dropdown — same UX as CommandPalette.

Three-column table rows: Provider ✓ | Model (id) | Price
Appears below the input prompt. ↑↓ navigate, Enter select, Esc cancel.
Focus stays on PromptInput at all times.
"""
from __future__ import annotations

import os
from textual.containers import Vertical
from textual.widgets import Static
from textual.message import Message

from cascade.commands.model.model import PROVIDER_CATALOG


class ModelPalette(Vertical):
    """Inline model picker dropdown, appears below input like CommandPalette."""

    DEFAULT_CSS = """
    ModelPalette {
        height: auto;
        max-height: 20;
        background: #1a1a2e;
        padding: 0 0;
        margin: 0 1;
        display: none;
        overflow-y: auto;
    }
    """

    class Selected(Message):
        """Emitted when user selects a model."""
        def __init__(self, provider: str, model_id: str, display_name: str) -> None:
            super().__init__()
            self.provider = provider
            self.model_id = model_id
            self.display_name = display_name

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._items: list[dict] = []
        self._highlight: int = 0

    def populate(self, current_provider: str, current_model: str) -> None:
        """Build items from PROVIDER_CATALOG and show the palette."""
        self._items = []
        for prov_key, prov_info in PROVIDER_CATALOG.items():
            api_key = os.getenv(prov_info["env_key"], "")
            has_key = bool(api_key)
            for m in prov_info["models"]:
                is_current = (prov_key == current_provider and m["id"] == current_model)

                self._items.append({
                    "provider_key": prov_key,
                    "model_id": m["id"],
                    "display_name": f"{prov_info['display']} / {m['label']}",
                    "provider_display": prov_info["display"],
                    "has_key": has_key,
                    "model_label": m["label"],
                    "model_id_str": m["id"],
                    "price": m["price"],
                    "is_current": is_current,
                })

        # Pre-select current model
        self._highlight = 0
        for i, item in enumerate(self._items):
            if item["is_current"]:
                self._highlight = i
                break

        # Compute column widths from plain text
        # Col 1: "Provider ✓" — pad to max provider name + 2
        # Col 2: "Model (id) ← current" — pad to max
        # Col 3: price — no pad needed (last col)
        self._col1_w = max(len(it["provider_display"]) for it in self._items) + 4  # + " ✓ "
        self._col2_w = max(
            len(it["model_label"]) + len(it["model_id_str"]) + 3  # " (id)"
            + (10 if it["is_current"] else 0)  # " ← current"
            for it in self._items
        )

        self._render_items()
        self.display = True

    def _render_items(self) -> None:
        """Re-render all rows with fixed-width column alignment."""
        for child in list(self.children):
            child.remove()

        for i, item in enumerate(self._items):
            # Column 1: Provider + key icon (fixed width)
            key_icon = "[#00d7af]✓[/#00d7af]" if item["has_key"] else "[#ff5f5f]✗[/#ff5f5f]"
            prov_plain = f"{item['provider_display']} ✓"
            prov_padded = prov_plain.ljust(self._col1_w)
            # Replace the plain ✓/✗ with Rich-styled version
            col1 = prov_padded.replace("✓", key_icon, 1)

            # Column 2: Model label (id) + current marker (fixed width)
            marker_plain = " ← current" if item["is_current"] else ""
            model_plain = f"{item['model_label']} ({item['model_id_str']}){marker_plain}"
            model_padded = model_plain.ljust(self._col2_w)
            # Apply Rich markup to the padded string
            if item["is_current"]:
                marker_rich = " [bold #00d7af]← current[/bold #00d7af]"
                col2_base = f"{item['model_label']} [dim]({item['model_id_str']})[/dim]"
                # Padding = total width - plain text length
                pad = self._col2_w - len(model_plain)
                col2 = col2_base + marker_rich + " " * max(0, pad)
            else:
                col2 = f"{item['model_label']} [dim]({item['model_id_str']})[/dim]"
                pad = self._col2_w - len(model_plain)
                col2 += " " * max(0, pad)

            # Column 3: Price (no padding, last column)
            col3 = f"[dim]{item['price']}[/dim]"

            if i == self._highlight:
                markup = f"[bold #0d1117] {col1}  {col2}  {col3} [/bold #0d1117]"
                classes = "palette-item active"
            else:
                markup = f" {col1}  [bold white]{col2}[/bold white]  {col3} "
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

    def move_up(self) -> None:
        if not self._items:
            return
        self._highlight = (self._highlight - 1) % len(self._items)
        self._render_items()

    def move_down(self) -> None:
        if not self._items:
            return
        self._highlight = (self._highlight + 1) % len(self._items)
        self._render_items()

    def select_current(self) -> bool:
        if not self._items:
            return False
        item = self._items[self._highlight]
        self.post_message(self.Selected(
            provider=item["provider_key"],
            model_id=item["model_id"],
            display_name=item["display_name"],
        ))
        self.display = False
        return True

    def cancel(self) -> None:
        self.display = False

    @property
    def is_visible(self) -> bool:
        return self.display and bool(self._items)
