from __future__ import annotations
from typing import Optional
from cascade.commands.base import BaseCommand, CommandContext


class CommandRouter:
    """Registry and dispatcher for slash commands."""

    def __init__(self):
        self._commands: dict[str, BaseCommand] = {}

    def register(self, cmd: BaseCommand) -> None:
        """Register a command and its aliases."""
        self._commands[f"/{cmd.name}"] = cmd
        for alias in (cmd.aliases or []):
            if not alias.startswith("/"):
                alias = f"/{alias}"
            self._commands[alias] = cmd

    def get(self, name: str) -> Optional[BaseCommand]:
        return self._commands.get(name)

    @property
    def all_commands(self) -> list[BaseCommand]:
        """Unique commands (deduplicated from aliases)."""
        seen = set()
        result = []
        for cmd in self._commands.values():
            if id(cmd) not in seen:
                seen.add(id(cmd))
                result.append(cmd)
        return result

    def get_commands_by_category(self) -> dict[str, list[BaseCommand]]:
        """Group unique commands by category for /help display."""
        groups: dict[str, list[BaseCommand]] = {}
        seen = set()
        for cmd in self._commands.values():
            if id(cmd) in seen:
                continue
            seen.add(id(cmd))
            if not cmd.hidden:
                groups.setdefault(cmd.category, []).append(cmd)
        return groups

    async def dispatch(self, input_str: str, ctx: CommandContext) -> bool:
        """Try to dispatch input as a slash command. Returns True if handled."""
        parts = input_str.strip().split(maxsplit=1)
        cmd_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        cmd = self._commands.get(cmd_name)
        if cmd:
            await cmd.execute(ctx, args)
            return True
        return False
