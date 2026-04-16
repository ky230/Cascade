"""QueryGuard — Three-state machine for query lifecycle.

Mirrors Claude Code's QueryGuard.ts. Prevents race conditions
between dequeue and execution by introducing a 'dispatching' state:

    idle → dispatching → running → idle
              ↓
            idle   (cancelReservation, if nothing to process)

States:
    idle        — No active query. Safe to dequeue.
    dispatching — A command has been dequeued but async execution hasn't started yet.
                  Prevents double-dispatch during the async gap.
    running     — API call / generation in progress.
"""
from __future__ import annotations

import logging
from typing import Callable, Literal, Optional

logger = logging.getLogger(__name__)


class QueryGuard:
    """Three-state machine for query lifecycle."""

    def __init__(self) -> None:
        self._status: Literal["idle", "dispatching", "running"] = "idle"
        self._generation: int = 0
        self._subscribers: list[Callable[[], None]] = []

    # ── State transitions ─────────────────────────────────────

    def reserve(self) -> bool:
        """idle → dispatching. Returns False if not idle.

        Called when a command is about to be dispatched (dequeued or
        directly submitted). Prevents other commands from being
        dispatched concurrently.
        """
        if self._status != "idle":
            return False
        self._status = "dispatching"
        logger.debug("QueryGuard: idle → dispatching")
        self._notify()
        return True

    def cancel_reservation(self) -> None:
        """dispatching → idle. No-op if not dispatching.

        Called when the dispatched command turns out to be a no-op
        or when the async gap resolves without starting a real query.
        """
        if self._status != "dispatching":
            return
        self._status = "idle"
        logger.debug("QueryGuard: dispatching → idle (cancelled)")
        self._notify()

    def try_start(self) -> Optional[int]:
        """idle|dispatching → running. Returns generation number.

        Returns None if already running (another query beat us).
        The returned generation number is used to validate that
        the caller is still the current owner when calling end().
        """
        if self._status == "running":
            return None
        self._status = "running"
        self._generation += 1
        logger.debug("QueryGuard: → running (gen=%d)", self._generation)
        self._notify()
        return self._generation

    def end(self, generation: int) -> bool:
        """running → idle. Returns True if generation matches.

        The caller should only perform cleanup (show prompt, check queue)
        if this returns True. A False return means a newer generation
        has superseded this one.
        """
        if self._generation != generation or self._status != "running":
            return False
        self._status = "idle"
        logger.debug("QueryGuard: running → idle (gen=%d ended)", generation)
        self._notify()
        return True

    def force_end(self) -> None:
        """Force → idle. Used by ESC cancel to abort any state.

        Increments generation so that any in-flight end() calls
        will return False (stale generation).
        """
        if self._status == "idle":
            return
        old_status = self._status
        self._status = "idle"
        self._generation += 1
        logger.debug(
            "QueryGuard: %s → idle (FORCED, new gen=%d)", old_status, self._generation
        )
        self._notify()

    # ── Read-only queries ─────────────────────────────────────

    @property
    def is_active(self) -> bool:
        """True if any query is dispatching or running."""
        return self._status != "idle"

    @property
    def is_running(self) -> bool:
        """True if a query is actively running (not just dispatching)."""
        return self._status == "running"

    @property
    def is_idle(self) -> bool:
        return self._status == "idle"

    @property
    def status(self) -> str:
        return self._status

    @property
    def generation(self) -> int:
        return self._generation

    # ── Subscription (for reactive UI updates) ────────────────

    def subscribe(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Register a callback for state changes. Returns unsubscribe fn."""
        self._subscribers.append(callback)

        def unsubscribe() -> None:
            try:
                self._subscribers.remove(callback)
            except ValueError:
                pass

        return unsubscribe

    def _notify(self) -> None:
        for cb in self._subscribers:
            try:
                cb()
            except Exception:
                pass
