from cascade.commands.base import BaseCommand, CommandContext


class ConfigCommand(BaseCommand):
    """View Cascade configuration.

    Reference: claude-code src/commands/config/config.tsx (7 lines)
    Claude Code impl: opens <Settings> JSX panel with defaultTab="Config".
    aliases: ['settings']. The Settings component has multi-tab UI
    (Config / Status / Stats tabs).
    Cascade impl: text-based config display (no JSX panel).
    """
    name = "config"
    description = "View Cascade configuration"
    aliases = ["/settings"]
    category = "Setup"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        lines = [
            "[bold]Cascade Config[/bold]\n",
            f"  Provider: [#0087ff]{ctx.engine.client.provider}[/#0087ff]",
            f"  Model:    [bold]{ctx.engine.client.model_name}[/bold]",
        ]
        if ctx.engine.registry:
            tool_count = len(ctx.engine.registry.list_tools())
            lines.append(f"  Tools:    {tool_count} registered")
        if ctx.engine.permissions:
            lines.append(f"  Perms:    {ctx.engine.permissions.mode.value}")
        await ctx.output_rich("\n".join(lines))
