from cascade.commands.base import BaseCommand, CommandContext


class ResumeCommand(BaseCommand):
    """Resume a previous conversation.

    Reference: claude-code src/commands/resume/index.ts
    Claude Code impl: aliases=['continue'], lazy-loads resume.js
    with session picker UI. Requires SessionStorage.
    Cascade impl: Stub — session persistence not yet available.
    """
    name = "resume"
    description = "Resume a previous conversation"
    aliases = ["/continue"]
    category = "Session"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        await ctx.output_rich(
            "[dim]/resume: Session persistence coming in Phase 10. "
            "Currently, conversations are not saved between sessions.[/dim]"
        )
