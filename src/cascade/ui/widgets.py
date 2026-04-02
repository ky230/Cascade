"""Textual widgets for Cascade TUI."""
from __future__ import annotations

import pyperclip
from textual.widgets import TextArea, Static
from textual.binding import Binding
from textual.reactive import reactive


class CopyableTextArea(TextArea):
    """Read-only TextArea with mouse drag-selection + 'c' key copy.

    The mouse selection is TextArea's built-in logic (not terminal-native),
    so it works in alternate screen / full-screen Textual apps.
    Clipboard access via pyperclip (direct OS clipboard), with OSC 52 fallback.

    Usage:
        area = CopyableTextArea("some long text", id="msg-1")
        await container.mount(area)
    """

    BINDINGS = [
        Binding("ctrl+a", "select_all_text", "Select All", show=False),
    ]

    def on_mount(self) -> None:
        self.read_only = True
        self.show_line_numbers = False

    def action_copy_selection(self) -> None:
        """Press 'c' to copy selected text to system clipboard (handled in on_key)."""
        text = self.selected_text
        if not text:
            return
        self._copy_to_clipboard(text)

    from textual.events import Key
    def on_key(self, event: Key) -> None:
        # If 'c' is pressed and text is selected, do copy.
        if event.character == "c" and self.selected_text:
            self.action_copy_selection()
            event.stop()
            return
        
        # Otherwise, if it's a printable character, forward to input!
        if event.is_printable:
            try:
                inp = self.app.query_one("#prompt-input")
                inp.focus()
                inp.value += event.character
                inp.cursor_position = len(inp.value)
                event.stop()
            except Exception:
                pass

    def action_select_all_text(self) -> None:
        """Ctrl+A to select all text in this area."""
        self.select_all()

    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to clipboard: pyperclip first, OSC 52 fallback."""
        try:
            pyperclip.copy(text)
            self.notify(f"✅ 已复制 {len(text)} 字符")
        except Exception:
            try:
                self.app.copy_to_clipboard(text)
                self.notify(f"✅ 已复制 {len(text)} 字符 (OSC52)")
            except Exception as e:
                self.notify(f"❌ {str(e)}")


class SpinnerWidget(Static):
    """Animated spinner that shows during API calls.

    Renders as a single-line braille animation with elapsed time.

    Usage:
        spinner = SpinnerWidget("Generating")
        await container.mount(spinner)
        # ... later ...
        await spinner.remove()
    """

    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    _frame_index: reactive[int] = reactive(0)

    def __init__(self, message: str = "Thinking", **kwargs):
        import time
        super().__init__(**kwargs)
        self._message = message
        self._timer = None
        self._start_time = time.time()

    def on_mount(self) -> None:
        self._timer = self.set_interval(0.08, self._advance_frame)

    def _advance_frame(self) -> None:
        self._frame_index += 1

    def watch__frame_index(self, value: int) -> None:
        import time
        frame = self.SPINNER_FRAMES[value % len(self.SPINNER_FRAMES)]
        elapsed = time.time() - self._start_time
        self.update(f"[#5fd7ff]{frame}[/#5fd7ff] [dim]{self._message}... ({elapsed:.1f}s)[/dim]")

    def stop(self) -> None:
        """Stop the animation timer."""
        if self._timer:
            self._timer.stop()
            self._timer = None
