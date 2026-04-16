"""Persistent queue preview widget for Cascade TUI.

Displays queued commands above the input area as dim gray text lines.
Mirrors Claude Code's PromptInputQueuedCommands.tsx — the preview is
persistent (not a toast), auto-updates via subscription, and hides
when the queue is empty.
"""
from __future__ import annotations

from textual.widgets import Static


class QueuePreview(Static):
    """Persistent preview of queued commands above the input.

    Subscribes to the MessageQueueManager and refreshes automatically
    when commands are enqueued/dequeued.

    Mount this widget inside the input-section, above the prompt-container.
    """

    DEFAULT_CSS = """
    QueuePreview {
        height: auto;
        padding: 0 2;
        margin: 0 0;
        display: none;
        background: transparent;
    }
    """

    MAX_VISIBLE = 5

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._unsubscribe = None

    def on_mount(self) -> None:
        """Subscribe to queue changes when mounted."""
        try:
            self._unsubscribe = self.app._input_queue.subscribe(self._refresh)
        except AttributeError:
            pass

    def on_unmount(self) -> None:
        """Unsubscribe when removed."""
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None

    def _refresh(self) -> None:
        """Re-render the preview from the current queue state."""
        try:
            commands = self.app._input_queue.get_snapshot()
        except AttributeError:
            self.display = False
            return

        visible = [cmd for cmd in commands if self.app._input_queue.is_visible(cmd)]
        if not visible:
            self.display = False
            return

        self.display = True
        lines: list[str] = []
        for cmd in visible[:self.MAX_VISIBLE]:
            text = cmd.value
            if len(text) > 80:
                text = text[:77] + "..."
            lines.append(f"[dim]⏳ {text}[/dim]")

        if len(visible) > self.MAX_VISIBLE:
            remaining = len(visible) - self.MAX_VISIBLE
            lines.append(f"[dim]  +{remaining} more queued[/dim]")

        self.update("\n".join(lines))

    def force_refresh(self) -> None:
        """Explicitly trigger a refresh (called by _update_queue_preview)."""
        self._refresh()
