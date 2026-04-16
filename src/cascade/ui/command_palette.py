"""Textual-native slash command completion dropdown.

Replicates the prompt_toolkit completion menu from feat/phase8-slash-commands:
- Compact single-line items: command name (green) + description (cyan)
- Blue highlight bar on current selection
- Dark background (#1a1a2e)
- Appears when typing '/', filters as you type, ↑↓ navigate, Enter select
- Keyboard handled externally (Input forwards ↑↓/Enter/Esc)
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static
from textual.message import Message


class CommandPalette(Vertical):
    """Compact floating completion dropdown for slash commands.

    This widget does NOT use ListView (which requires focus).
    Instead it manages its own highlight index and re-renders
    Static items, so the Input can keep focus while ↑↓ work.
    """

    DEFAULT_CSS = """
    CommandPalette {
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
        """Emitted when user selects a command from the palette."""
        def __init__(self, trigger: str) -> None:
            super().__init__()
            self.trigger = trigger

    def __init__(self, router, **kwargs):
        super().__init__(**kwargs)
        self._router = router
        self._matches: list[dict] = []  # {trigger, description, aliases}
        self._highlight: int = 0

    def _build_items(self) -> list[dict]:
        """Build the master command list from the router."""
        seen = set()
        items = []
        for trigger, cmd in self._router._commands.items():
            if id(cmd) in seen or cmd.hidden:
                continue
            seen.add(id(cmd))
            aliases = [a if a.startswith("/") else f"/{a}" for a in (cmd.aliases or [])]
            alias_str = f"  ({', '.join(aliases)})" if aliases else ""
            items.append({
                "trigger": trigger,
                "display": f"{trigger}{alias_str}",
                "description": cmd.description,
            })
        return items

    def filter(self, query: str) -> None:
        """Filter commands matching query and render. '/' shows all."""
        all_items = self._build_items()
        q = query.lower()
        self._matches = [
            item for item in all_items
            if q == "/" or item["trigger"].lower().startswith(q)
        ]
        if self._matches:
            self._highlight = 0
            self._update_items()
            self.display = True
        else:
            self.display = False

    def _update_items(self) -> None:
        """Re-render all items as Static widgets with highlight."""
        # Remove old children
        for child in list(self.children):
            child.remove()

        for i, item in enumerate(self._matches):
            display_name = item['display'].ljust(15)
            desc = item['description']
            
            if i == self._highlight:
                # Active: background #5fd7ff applied via CSS class. Force dark text.
                markup = f"[bold #0d1117] {display_name}[/bold #0d1117] [#0d1117]{desc}[/#0d1117]"
                classes = "palette-item active"
            else:
                # Normal: transparent background. White command, gray description.
                markup = f" [bold white]{display_name}[/bold white] [#8b949e]{desc}[/#8b949e]"
                classes = "palette-item"
                
            line = Static(markup, classes=classes)
            self.mount(line)

        # Scroll highlighted row into view (matches ModelPalette._render_items)
        if self._matches:
            try:
                children = list(self.children)
                if self._highlight < len(children):
                    children[self._highlight].scroll_visible()
            except Exception:
                pass

    def move_up(self) -> None:
        """Move highlight up, wrapping around."""
        if not self._matches:
            return
        self._highlight = (self._highlight - 1) % len(self._matches)
        self._update_items()

    def move_down(self) -> None:
        """Move highlight down, wrapping around."""
        if not self._matches:
            return
        self._highlight = (self._highlight + 1) % len(self._matches)
        self._update_items()

    def select_current(self) -> bool:
        """Select the currently highlighted item. Returns True if there was one."""
        if not self._matches:
            return False
        trigger = self._matches[self._highlight]["trigger"]
        self.post_message(self.Selected(trigger))
        self.display = False
        return True

    @property
    def is_visible(self) -> bool:
        return self.display and bool(self._matches)
