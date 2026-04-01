from __future__ import annotations
from typing import Callable, List
from cascade.state.app_state import AppState

class Store:
    """Minimal reactive state store."""

    def __init__(self):
        self._state = AppState()
        self._listeners: List[Callable[[AppState], None]] = []

    def get_state(self) -> AppState:
        return self._state

    def set_state(self, updater: Callable[[AppState], AppState]) -> None:
        self._state = updater(self._state)
        for listener in self._listeners:
            listener(self._state)

    def subscribe(self, listener: Callable[[AppState], None]) -> Callable[[], None]:
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)
