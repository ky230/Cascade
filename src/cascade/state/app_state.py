from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class AppState:
    """Immutable application state."""
    is_loading: bool = False
    messages: tuple = ()
    provider: str = ""
    model: str = ""
    permission_mode: str = "default"
    verbose: bool = False
    conversation_id: str = ""
    input_tokens: int = 0
    output_tokens: int = 0

    def with_update(self, **kwargs) -> AppState:
        current = asdict(self)
        current.update(kwargs)
        return AppState(**current)
