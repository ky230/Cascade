from cascade.commands.base import BaseCommand, CommandContext


class BranchCommand(BaseCommand):
    """Create a branch of the current conversation.

    Reference: claude-code src/commands/branch/index.ts
    Claude Code impl: aliases=['fork'] (when FORK_SUBAGENT off).
    Cascade impl: Stub — no conversation branching system yet.
    """
    name = "branch"
    description = "Create a branch of the current conversation"
    aliases = ["/fork"]
    category = "Session"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        await ctx.output_rich(
            "[dim]/branch: Conversation branching coming in Phase 10.[/dim]"
        )
