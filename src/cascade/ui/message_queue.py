"""Message Queue Manager for Cascade TUI.

Mirrors Claude Code's messageQueueManager.ts — a priority-aware FIFO queue
that holds user inputs submitted while the AI is generating. Supports:
  - Three-tier priority (now > next > later)
  - Subscriber notifications for reactive UI updates
  - Pop-all-editable for ↑ arrow queue editing
  - Operation logging for debugging
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Literal, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class QueuedCommand:
    """A queued user input with full context. Mirrors Claude Code's QueuedCommand type."""

    value: str
    mode: str = "prompt"                     # "prompt" | "slash"  (future: "bash")
    priority: Literal["now", "next", "later"] = "next"
    uuid: str = field(default_factory=lambda: str(uuid4()))
    skip_slash_commands: bool = False         # for bridge/remote messages
    is_meta: bool = False                    # system-generated, hidden from transcript
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PopAllEditableResult:
    """Result of pop_all_editable: merged text + cursor position."""

    text: str
    cursor_offset: int


class MessageQueueManager:
    """Module-level message queue, mirrors Claude Code's messageQueueManager.ts.

    Priority ordering:  now(0) > next(1) > later(2)
    Within the same priority, FIFO order is preserved.
    """

    PRIORITY_ORDER = {"now": 0, "next": 1, "later": 2}

    def __init__(self) -> None:
        self._queue: list[QueuedCommand] = []
        self._subscribers: list[Callable[[], None]] = []
        self._session_id: str = str(uuid4())
        self._operations_log: list[dict] = []

    # ── Write operations ──────────────────────────────────────

    def enqueue(self, command: QueuedCommand) -> None:
        """Add a command to the queue in priority order."""
        # Find insertion point: after all existing commands with same or higher priority
        insert_idx = len(self._queue)
        cmd_priority = self.PRIORITY_ORDER.get(command.priority, 1)
        for i, existing in enumerate(self._queue):
            existing_priority = self.PRIORITY_ORDER.get(existing.priority, 1)
            if existing_priority > cmd_priority:
                insert_idx = i
                break

        self._queue.insert(insert_idx, command)
        self._log_operation("enqueue", command.value)
        self._notify_subscribers()

    def dequeue(
        self, filter_fn: Optional[Callable[[QueuedCommand], bool]] = None
    ) -> Optional[QueuedCommand]:
        """Remove and return the first command matching filter_fn (or first overall)."""
        for i, cmd in enumerate(self._queue):
            if filter_fn is None or filter_fn(cmd):
                self._queue.pop(i)
                self._log_operation("dequeue", cmd.value)
                self._notify_subscribers()
                return cmd
        return None

    def dequeue_all_matching(
        self, predicate: Callable[[QueuedCommand], bool]
    ) -> list[QueuedCommand]:
        """Remove and return all commands matching predicate, preserving order."""
        matched: list[QueuedCommand] = []
        remaining: list[QueuedCommand] = []
        for cmd in self._queue:
            if predicate(cmd):
                matched.append(cmd)
            else:
                remaining.append(cmd)
        if matched:
            self._queue[:] = remaining
            self._log_operation("dequeue_all", f"{len(matched)} commands")
            self._notify_subscribers()
        return matched

    def peek(
        self, filter_fn: Optional[Callable[[QueuedCommand], bool]] = None
    ) -> Optional[QueuedCommand]:
        """Return (without removing) the first command matching filter_fn."""
        for cmd in self._queue:
            if filter_fn is None or filter_fn(cmd):
                return cmd
        return None

    def remove_by_uuid(self, uuid: str) -> bool:
        """Remove a specific command by UUID. Returns True if found."""
        for i, cmd in enumerate(self._queue):
            if cmd.uuid == uuid:
                self._queue.pop(i)
                self._log_operation("remove", cmd.value)
                self._notify_subscribers()
                return True
        return False

    def clear(self) -> None:
        """Remove all commands from the queue."""
        if self._queue:
            self._log_operation("clear", f"{len(self._queue)} commands")
            self._queue.clear()
            self._notify_subscribers()

    # ── Editable mode helpers ─────────────────────────────────

    def pop_all_editable(
        self, current_input: str, cursor_offset: int
    ) -> Optional[PopAllEditableResult]:
        """Pop all editable commands from queue, merge into input for editing.

        Mirrors Claude Code's popAllEditable — used when user presses ↑
        while the queue is non-empty.
        """
        editable = [cmd for cmd in self._queue if self.is_editable(cmd)]
        if not editable:
            return None

        queued_texts = [cmd.value for cmd in editable]
        # Keep non-editable items (e.g. system notifications) in queue
        self._queue[:] = [cmd for cmd in self._queue if not self.is_editable(cmd)]

        # Merge: queued commands first, then current input
        parts = queued_texts
        if current_input.strip():
            parts.append(current_input)
        new_input = "\n".join(parts)

        self._log_operation("popAllEditable", f"{len(editable)} commands")
        self._notify_subscribers()

        return PopAllEditableResult(
            text=new_input,
            cursor_offset=len(new_input),
        )

    @staticmethod
    def is_editable(cmd: QueuedCommand) -> bool:
        """A command is editable if it was user-generated (not meta/system)."""
        return not cmd.is_meta

    # ── Read operations ───────────────────────────────────────

    @property
    def length(self) -> int:
        return len(self._queue)

    @property
    def has_commands(self) -> bool:
        return len(self._queue) > 0

    def get_snapshot(self) -> list[QueuedCommand]:
        """Return a shallow copy of the current queue for UI rendering."""
        return list(self._queue)

    # ── Subscription (for reactive UI updates) ────────────────

    def subscribe(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Register a callback for queue changes. Returns an unsubscribe function."""
        self._subscribers.append(callback)

        def unsubscribe() -> None:
            try:
                self._subscribers.remove(callback)
            except ValueError:
                pass

        return unsubscribe

    def _notify_subscribers(self) -> None:
        for cb in self._subscribers:
            try:
                cb()
            except Exception:
                pass

    # ── Logging ───────────────────────────────────────────────

    def _log_operation(self, operation: str, content: Optional[str] = None) -> None:
        """Record a queue operation for debugging. Mirrors Claude Code's sessionStorage logging."""
        record = {
            "type": "queue-operation",
            "operation": operation,
            "timestamp": datetime.now().isoformat(),
            "session_id": self._session_id,
        }
        if content is not None:
            record["content"] = content[:200]  # truncate for safety
        self._operations_log.append(record)
        # Keep log bounded
        if len(self._operations_log) > 500:
            self._operations_log = self._operations_log[-250:]
        logger.debug("Queue: %s — %s", operation, content[:80] if content else "")

    def get_operations_log(self) -> list[dict]:
        """Return the operations log for debugging."""
        return list(self._operations_log)

    # ── Static helpers ────────────────────────────────────────

    @staticmethod
    def is_slash_command(cmd: QueuedCommand) -> bool:
        """Check if a command is a slash command."""
        return (
            isinstance(cmd.value, str)
            and cmd.value.strip().startswith("/")
            and not cmd.skip_slash_commands
        )

    @staticmethod
    def is_visible(cmd: QueuedCommand) -> bool:
        """Check if a command should be visible in the queue preview."""
        return not cmd.is_meta
