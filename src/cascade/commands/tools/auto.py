"""Slash command: /auto — toggle automatic tool approval mode.

Reference: NO direct Claude Code slash command equivalent.
Claude Code implements similar functionality via:
1. CLI flag: --dangerously-skip-permissions (skips all permission checks)
2. /sandbox auto-allow mode (SandboxManager.isAutoAllowBashIfSandboxedEnabled())
3. /permissions allow rules (e.g., Bash(*):* wildcard rules)
Cascade impl: ORIGINAL design. Toggles PermissionEngine.mode between
AUTO (destructive tools require confirmation) and BYPASS (all tools
auto-approved). Designed for HEP batch workflows where manual
confirmation of every cmsRun/hadd call is impractical.
"""
from cascade.commands.base import BaseCommand, CommandContext
from cascade.permissions.engine import PermissionMode


class AutoCommand(BaseCommand):
    """Toggle automatic tool approval mode.

    Reference: NO direct Claude Code slash command equivalent.
    Claude Code implements similar functionality via:
    1. CLI flag: --dangerously-skip-permissions (skips all permission checks)
    2. /sandbox auto-allow mode (SandboxManager.isAutoAllowBashIfSandboxedEnabled())
    3. /permissions allow rules (e.g., Bash(*):* wildcard rules)
    Cascade impl: ORIGINAL design. Toggles PermissionEngine.mode between
    AUTO (destructive tools require confirmation) and BYPASS (all tools
    auto-approved). Designed for HEP batch workflows where manual
    confirmation of every cmsRun/hadd call is impractical.
    """
    name = "auto"
    description = "Toggle automatic tool approval"
    category = "Tools"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        # Access the permission engine from the query engine
        perms = ctx.engine.permissions
        if perms is None:
            await ctx.output_rich("[dim]No permission system configured.[/dim]")
            return

        if perms.mode == PermissionMode.BYPASS:
            # Currently in BYPASS → switch back to AUTO (safe mode)
            perms.mode = PermissionMode.AUTO
            await ctx.output_rich(
                "[#00d7af]Auto-approve: OFF[/#00d7af]\n"
                "[dim]Tool calls will require manual confirmation.[/dim]"
            )
        else:
            # Currently in AUTO or DEFAULT → switch to BYPASS
            perms.mode = PermissionMode.BYPASS
            await ctx.output_rich(
                "[bold yellow]⚠ Auto-approve: ON[/bold yellow]\n"
                "[dim]All tool calls will be approved automatically.\n"
                "Use /auto again to disable.[/dim]"
            )
