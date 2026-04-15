from cascade.commands.base import BaseCommand, CommandContext


class RewindCommand(BaseCommand):
    """Restore conversation to a previous point.

    Reference: claude-code src/commands/rewind/index.ts
    Claude Code impl: aliases=['checkpoint'], type='local'.
    Cascade impl: Stub — no checkpoint/snapshot system yet.
    """
    name = "rewind"
    description = "Restore conversation to a previous point"
    aliases = ["/checkpoint"]
    category = "Session"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        await ctx.output_rich(
            "[dim]/rewind: Conversation checkpoints coming in Phase 10.[/dim]"
        )
