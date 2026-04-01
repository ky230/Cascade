from __future__ import annotations
from typing import Optional, Iterable
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from cascade.commands.base import BaseCommand, CommandContext


class SlashCompleter(Completer):
    """Custom completer that activates only when input starts with '/'.

    Shows all commands when just '/' is typed, then fuzzy-filters as the
    user continues typing. Dropdown appears as-you-type (no Tab needed)
    when paired with complete_while_typing=True on the PromptSession.
    """

    def __init__(self, router: CommandRouter):
        self._router = router

    def get_completions(
        self, document: Document, complete_event
    ) -> Iterable[Completion]:
        text = document.text_before_cursor.lstrip()

        # Only activate when input starts with '/'
        if not text.startswith("/"):
            return

        # Don't show completions after the command (when there's a space)
        if " " in text:
            return

        query = text.lower()  # e.g., "/he" or "/"
        word_before_cursor = text  # The full slash command fragment

        # Collect and score all matching commands
        seen_ids: set[int] = set()
        for trigger, cmd in self._router._commands.items():
            if id(cmd) in seen_ids:
                continue

            trigger_lower = trigger.lower()

            # Match: exact prefix, or fuzzy substring
            if query == "/" or trigger_lower.startswith(query):
                seen_ids.add(id(cmd))
                # Calculate display + metadata
                display_text = trigger
                description = cmd.description
                # Show aliases inline
                aliases = [a if a.startswith("/") else f"/{a}" for a in (cmd.aliases or [])]
                alias_str = f"  ({', '.join(aliases)})" if aliases else ""

                yield Completion(
                    text=trigger,
                    start_position=-len(word_before_cursor),
                    display=f"{display_text}{alias_str}",
                    display_meta=description,
                )


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

    def get_completer(self) -> SlashCompleter:
        """Build a slash-activated completer for prompt_toolkit."""
        return SlashCompleter(self)

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
