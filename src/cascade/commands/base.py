from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from rich.console import Console
    from cascade.engine.query import QueryEngine


@dataclass
class CommandContext:
    """Runtime context passed to every command handler."""
    console: Optional[Console]       # None when running in Textual
    engine: QueryEngine
    session: Optional[object]        # PromptSession or None
    repl: object                     # CascadeRepl or CascadeApp

    async def output(self, text: str) -> None:
        """Universal output — works in both old REPL and Textual."""
        if hasattr(self.repl, 'append_system_message'):
            # Textual mode
            await self.repl.append_system_message(text)
        elif self.console:
            # Legacy REPL mode
            self.console.print(text)


class BaseCommand(ABC):
    """Abstract base for all slash commands."""
    name: str = ""
    description: str = ""
    aliases: list[str] = []
    category: str = "General"
    hidden: bool = False

    @abstractmethod
    async def execute(self, ctx: CommandContext, args: str) -> None:
        """Execute the command. `args` is everything after `/command `."""
        ...

    @property
    def trigger(self) -> str:
        return f"/{self.name}"
