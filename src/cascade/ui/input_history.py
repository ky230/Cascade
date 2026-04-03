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

    MAX_HISTORY = 2000
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
            # Entering history mode
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
