from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console
    from prompt_toolkit import PromptSession
    from cascade.engine.query import QueryEngine


@dataclass
class CommandContext:
    """Runtime context passed to every command handler."""
    console: Console
    engine: QueryEngine
    session: PromptSession
    repl: object  # CascadeRepl (avoid circular import)


class BaseCommand(ABC):
    """Abstract base for all slash commands."""
    name: str = ""
    description: str = ""
    aliases: list[str] = []
    category: str = "General"
    hidden: bool = False  # hidden commands don't show in /help

    @abstractmethod
    async def execute(self, ctx: CommandContext, args: str) -> None:
        """Execute the command. `args` is everything after `/command `."""
        ...

    @property
    def trigger(self) -> str:
        return f"/{self.name}"
