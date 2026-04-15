from cascade.commands.base import BaseCommand, CommandContext


class VersionCommand(BaseCommand):
    """Show Cascade version.

    Reference: claude-code src/commands/version.ts (23 lines)
    Claude Code impl: reads MACRO.VERSION + MACRO.BUILD_TIME,
    only visible to Anthropic internal users (USER_TYPE === 'ant').
    Cascade impl: reads VERSION from banner.py, always visible.
    """
    name = "version"
    description = "Show Cascade version"
    category = "Setup"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        from cascade.ui.banner import VERSION
        await ctx.output_rich(f"[bold #5fd7ff]Cascade[/bold #5fd7ff] v{VERSION}")
