# Input History (⬆️⬇️ Arrow Key Recall + JSONL Persistence)

**Goal:** Add terminal-style ⬆️⬇️ input history to `PromptInput` with cross-session persistence via JSONL file.

**Architecture:** A standalone `InputHistory` class (new file) manages both the in-memory buffer and disk I/O. `PromptInput` owns an `InputHistory` instance. `CascadeApp.on_input_submitted` calls `prompt_input.add_to_history(text)`.

**Tech Stack:** Python 3.14, Textual 3.x, stdlib `json` / `pathlib` / `time`

**Design Decisions (from competitive analysis):**
- **Storage:** Claude-style JSONL (`~/.cascade/history.jsonl`), each line a JSON object with metadata
- **Capacity:** Gemini-style hard cap (MAX=200), file rewritten on overflow to prevent growth
- **Loading:** Full read on startup (200 entries ≈ 30KB, <1ms) — no need for Claude's chunked lazy loading
- **`/clear`:** Does NOT clear history (shell semantics — `/clear` only affects screen)
- **Dedup:** Consecutive identical entries are skipped (Codex/Gemini pattern)
- **Multiline conflict:** ⬆️ only triggers history when cursor is on first line; ⬇️ only when on last line
- **Palette conflict:** History navigation disabled while CommandPalette or ModelPalette is visible

---

## Task 1: Create `InputHistory` module

> **New file:** `src/cascade/ui/input_history.py`

This isolates all history logic (buffer + disk I/O) from the widget, keeping `widgets.py` clean.

```python
"""Session + persistent input history for Cascade TUI."""
from __future__ import annotations

import json
import time
from pathlib import Path


class InputHistory:
    """Manages an in-memory history buffer backed by a JSONL file.

    Storage format (one JSON object per line):
        {"display": "hello world", "type": "prompt", "ts": 1712100000.0}
        {"display": "/model gpt-4", "type": "command", "ts": 1712100060.0}

    Fields:
        display  — the raw text the user typed
        type     — "command" if starts with "/", else "prompt"
        ts       — Unix timestamp (float)
    """

    MAX_HISTORY = 200
    _HISTORY_DIR = Path.home() / ".cascade"
    _HISTORY_FILE = _HISTORY_DIR / "history.jsonl"

    def __init__(self) -> None:
        self._entries: list[str] = []       # newest at end
        self._index: int = -1               # -1 = not browsing
        self._stashed_input: str = ""       # saves current draft

        # Load persistent history from disk
        self._load()

    # ── Public API ──

    def add(self, text: str) -> None:
        """Record a submitted prompt. Deduplicates consecutive identical entries."""
        stripped = text.strip()
        if not stripped:
            return
        if self._entries and self._entries[-1] == stripped:
            return
        self._entries.append(stripped)
        if len(self._entries) > self.MAX_HISTORY:
            self._entries = self._entries[-self.MAX_HISTORY:]
        self._index = -1
        self._stashed_input = ""
        self._save(stripped)

    def navigate_up(self) -> str | None:
        """Move to an older entry. Returns the text, or None if at boundary."""
        if not self._entries:
            return None
        if self._index == -1:
            # Entering history mode — stash whatever is in the input
            self._index = len(self._entries) - 1
            return self._entries[self._index]
        if self._index > 0:
            self._index -= 1
            return self._entries[self._index]
        return None  # already at oldest

    def navigate_down(self) -> str | None:
        """Move to a newer entry, or restore the stashed draft.

        Returns the text to display, or None if not in history mode.
        Special: returns empty string "" to signal "restore stashed draft".
        """
        if self._index < 0:
            return None  # not browsing
        if self._index < len(self._entries) - 1:
            self._index += 1
            return self._entries[self._index]
        # Past the newest: exit history mode
        self._index = -1
        return ""  # signal: restore stash

    def stash(self, text: str) -> None:
        """Save the current input draft before entering history mode."""
        self._stashed_input = text

    @property
    def stashed_input(self) -> str:
        """Return the stashed draft text."""
        return self._stashed_input

    @property
    def is_browsing(self) -> bool:
        """True if the user is currently navigating history."""
        return self._index >= 0

    def reset_navigation(self) -> None:
        """Exit history browsing mode without restoring."""
        self._index = -1
        self._stashed_input = ""

    # ── Disk I/O ──

    def _load(self) -> None:
        """Read history.jsonl into memory on startup."""
        if not self._HISTORY_FILE.exists():
            return
        try:
            lines = self._HISTORY_FILE.read_text(encoding="utf-8").splitlines()
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    display = entry.get("display", "").strip()
                    if display:
                        self._entries.append(display)
                except json.JSONDecodeError:
                    continue
            # Enforce cap
            if len(self._entries) > self.MAX_HISTORY:
                self._entries = self._entries[-self.MAX_HISTORY:]
                self._rewrite()
        except OSError:
            pass

    def _save(self, text: str) -> None:
        """Append one entry to disk. Rewrites if over MAX_HISTORY."""
        try:
            self._HISTORY_DIR.mkdir(parents=True, exist_ok=True)
            entry = {
                "display": text,
                "type": "command" if text.startswith("/") else "prompt",
                "ts": time.time(),
            }
            with open(self._HISTORY_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

            # If disk file has grown too large, rewrite with only current entries
            line_count = sum(1 for _ in open(self._HISTORY_FILE, encoding="utf-8"))
            if line_count > self.MAX_HISTORY * 2:
                self._rewrite()
        except OSError:
            pass

    def _rewrite(self) -> None:
        """Rewrite the entire history file with current in-memory entries."""
        try:
            self._HISTORY_DIR.mkdir(parents=True, exist_ok=True)
            with open(self._HISTORY_FILE, "w", encoding="utf-8") as f:
                for entry_text in self._entries:
                    entry = {
                        "display": entry_text,
                        "type": "command" if entry_text.startswith("/") else "prompt",
                        "ts": 0.0,  # original timestamp lost on rewrite
                    }
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass
```

---

## Task 2: Wire `InputHistory` into `PromptInput`

> **Modify:** `src/cascade/ui/widgets.py` (lines 151-170)

**Step 1:** Add `__init__` to `PromptInput` and create an `InputHistory` instance + `add_to_history` method.

Current code (lines 151-170):
```python
class PromptInput(TextArea):
    """Multiline input for prompt.

    Enter  → submit (fires Submitted message)
    Ctrl+N → insert newline

    We must override ``_on_key`` because TextArea hard-codes
    ``{"enter": "\\n"}`` inside its own ``_on_key``, which runs
    *before* any BINDINGS, making a Binding("enter", ...) useless.
    """

    class Submitted(Message):
        """Fired when the user presses Enter to submit their prompt."""
        def __init__(self, prompt_input: 'PromptInput', value: str) -> None:
            self.input = prompt_input
            self.value = value
            super().__init__()

    def on_mount(self) -> None:
        self.show_line_numbers = False
```

New code:
```python
class PromptInput(TextArea):
    """Multiline input for prompt.

    Enter  → submit (fires Submitted message)
    Ctrl+N → insert newline
    ⬆️/⬇️   → recall input history (when no palette is visible)

    We must override ``_on_key`` because TextArea hard-codes
    ``{"enter": "\\n"}`` inside its own ``_on_key``, which runs
    *before* any BINDINGS, making a Binding("enter", ...) useless.
    """

    class Submitted(Message):
        """Fired when the user presses Enter to submit their prompt."""
        def __init__(self, prompt_input: 'PromptInput', value: str) -> None:
            self.input = prompt_input
            self.value = value
            super().__init__()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from cascade.ui.input_history import InputHistory
        self._history = InputHistory()

    def on_mount(self) -> None:
        self.show_line_numbers = False

    def add_to_history(self, text: str) -> None:
        """Record a submitted prompt to the history buffer + disk."""
        self._history.add(text)
```

---

## Task 3: Intercept ⬆️⬇️ in `_on_key`

> **Modify:** `src/cascade/ui/widgets.py` (lines 172-237)

Replace the entire `_on_key` method. Key changes marked with `# NEW:` comments.

Current code starts at line 172. New code:

```python
    async def _on_key(self, event) -> None:
        """Intercept Enter, Ctrl+N, ⬆️/⬇️ before TextArea's default handler.

        PromptInput is the SINGLE AUTHORITY for Enter handling.
        Palette navigation keys (up/down/tab/escape) bubble to App.on_key.
        ⬆️/⬇️ navigate input history when no palette is visible and cursor
        is on the first/last line respectively.
        """
        # Check command palette visibility
        palette_visible = False
        palette = None
        try:
            from cascade.ui.command_palette import CommandPalette
            palette = self.app.query_one("#cmd-palette", CommandPalette)
            palette_visible = palette.display
        except Exception:
            pass

        # Check model palette visibility
        model_palette_visible = False
        try:
            from cascade.ui.model_palette import ModelPalette
            mp = self.app.query_one("#model-palette", ModelPalette)
            model_palette_visible = mp.display
        except Exception:
            pass

        # Command palette visible: let UP/DOWN/TAB/ESCAPE bubble to App.on_key
        if palette_visible and event.key in ("up", "down", "tab", "escape"):
            return

        # Model palette visible: let UP/DOWN/ESCAPE bubble to App.on_key
        if model_palette_visible and event.key in ("up", "down", "escape"):
            return

        # NEW: ── History navigation (no palette visible) ──
        if event.key == "up":
            cursor_row, _ = self.cursor_location
            if cursor_row == 0:
                # Stash current draft on first entry into history mode
                if not self._history.is_browsing:
                    self._history.stash(self.text)
                result = self._history.navigate_up()
                if result is not None:
                    event.stop()
                    event.prevent_default()
                    self.text = result
                    self.move_cursor((0, 0))
                    return

        if event.key == "down":
            if self._history.is_browsing:
                cursor_row, _ = self.cursor_location
                last_row = self.document.line_count - 1
                if cursor_row >= last_row:
                    result = self._history.navigate_down()
                    if result is not None:
                        event.stop()
                        event.prevent_default()
                        if result == "":
                            # Restore stashed draft
                            self.text = self._history.stashed_input
                        else:
                            self.text = result
                        self.move_cursor(self.document.end)
                        return

        if event.key == "enter":
            # Enter is ALWAYS handled here — never let it bubble
            event.stop()
            event.prevent_default()

            # NEW: Reset history navigation on submit
            self._history.reset_navigation()

            # Case 0: Model palette visible → select model directly
            if model_palette_visible:
                mp.select_current()
                return

            # Case 1: Command palette visible → select command and submit
            if palette_visible and palette is not None and palette._matches:
                trigger = palette._matches[palette._highlight]["trigger"]
                palette.display = False
                self.text = trigger
                self.post_message(self.Submitted(self, trigger))
                return

            # Case 2: Normal submit
            if self.text.strip():
                self.post_message(self.Submitted(self, self.text))
            return

        if event.key == "ctrl+n":
            # Ctrl+N = insert a real newline character
            event.stop()
            event.prevent_default()
            start, end = self.selection
            self._replace_via_keyboard("\n", start, end)
            return

        # Everything else: delegate to parent TextArea._on_key
        await super()._on_key(event)
```

---

## Task 4: Record history on submission in `CascadeApp`

> **Modify:** `src/cascade/ui/textual_app.py` (lines 269-270)

Current code:
```python
        input_widget = self.query_one("#prompt-input", PromptInput)
        input_widget.text = ""
```

New code:
```python
        input_widget = self.query_one("#prompt-input", PromptInput)
        input_widget.add_to_history(user_text)
        input_widget.text = ""
```

---

## JSONL Storage Example

File: `~/.cascade/history.jsonl`
```jsonl
{"display": "帮我分析一下这段代码的性能", "type": "prompt", "ts": 1712100000.0}
{"display": "/model deepseek deepseek-chat", "type": "command", "ts": 1712100060.5}
{"display": "/help", "type": "command", "ts": 1712100120.3}
{"display": "把这个函数重构成 async", "type": "prompt", "ts": 1712100180.1}
{"display": "/clear", "type": "command", "ts": 1712100240.7}
```

---

## Verification Plan

### Manual Tests (user runs the app)
1. Type "hello" → Enter → "world" → Enter → ⬆️ → shows "world" → ⬆️ → shows "hello" ✓
2. ⬆️ at oldest → stays on "hello" (no crash, no wrap) ✓
3. ⬇️ → shows "world" → ⬇️ → restores empty draft ✓
4. Type "draft text", press ⬆️ → history replaces → ⬇️⬇️ → "draft text" restored ✓
5. Type "/help" → Enter → ⬆️ → shows "/help" (slash commands recorded) ✓
6. Type "/clear" → Enter → ⬆️ → shows "/clear" and earlier entries (NOT cleared) ✓
7. Multiline: Ctrl+N to add newline, cursor on line 2, press ⬆️ → cursor moves up (NOT history) ✓
8. Open command palette `/` → ⬆️⬇️ → palette navigates (NOT history) ✓
9. Quit and relaunch → ⬆️ → previous session's entries are available ✓
10. Verify `~/.cascade/history.jsonl` exists and contains valid JSONL ✓
