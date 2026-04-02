from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from cascade.engine.query import QueryEngine


@dataclass
class CommandContext:
    """Runtime context passed to every command handler."""
    engine: QueryEngine
    repl: object                     # CascadeApp instance

    async def output(self, text: str) -> None:
        """Output plain text via CascadeApp."""
        if hasattr(self.repl, 'append_system_message'):
            await self.repl.append_system_message(text)

    async def output_rich(self, markup: str) -> None:
        """Output Rich markup via CascadeApp."""
        if hasattr(self.repl, 'append_rich_message'):
            await self.repl.append_rich_message(markup)
        else:
            await self.output(markup)


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
