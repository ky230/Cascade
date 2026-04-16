"""Slash command: /tools — list all registered tools.

Reference: NO direct Claude Code equivalent.
Claude Code distributes tool info across /status (Settings Status Tab),
/permissions (PermissionRuleList), and getTools() runtime API.
Cascade impl: ORIGINAL command inspired by Gemini CLI. Consolidates
all tool information into a single command: name, description, and
enabled/disabled status. This is a Cascade differentiator.
"""
from cascade.commands.base import BaseCommand, CommandContext


class ToolsCommand(BaseCommand):
    """List all registered tools and their status.

    Reference: NO direct Claude Code equivalent.
    Claude Code distributes tool info across /status (Settings Status Tab),
    /permissions (PermissionRuleList), and getTools() runtime API.
    Cascade impl: ORIGINAL command inspired by Gemini CLI. Consolidates
    all tool information into a single command: name, description, and
    enabled/disabled status. This is a Cascade differentiator.
    """
    name = "tools"
    description = "List all registered tools"
    category = "Tools"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        # Access the tool registry from the engine
        registry = getattr(ctx.engine, "registry", None)
        if not registry:
            await ctx.output_rich("[dim]No tool registry available.[/dim]")
            return

        tools = registry.list_tools()
        if not tools:
            await ctx.output_rich("[dim]No tools registered.[/dim]")
            return

        # Build formatted output sorted by tool name
        lines = [f"[bold]Tools ({len(tools)} registered)[/bold]\n"]
        for tool in sorted(tools, key=lambda t: t.name):
            desc = getattr(tool, "description", "")[:60]
            lines.append(
                f"  [green]●[/green] [bold]{tool.name}[/bold]"
                f"  [dim]{desc}[/dim]"
            )
        await ctx.output_rich("\n".join(lines))
