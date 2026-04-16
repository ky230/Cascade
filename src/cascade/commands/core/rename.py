from cascade.commands.base import BaseCommand, CommandContext


class RenameCommand(BaseCommand):
    """Rename the current conversation.

    Reference: claude-code src/commands/rename/index.ts
    Claude Code impl: immediate=true, lazy-loads rename.js.
    Cascade impl: Stub — no conversation naming system yet.
    """
    name = "rename"
    description = "Rename the current conversation"
    category = "Session"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        await ctx.output_rich(
            "[dim]/rename: Conversation naming coming in Phase 10.[/dim]"
        )
