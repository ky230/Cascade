from cascade.commands.base import BaseCommand, CommandContext
import time


class StatusCommand(BaseCommand):
    """Show session status, model info, and usage stats.

    Reference: claude-code src/commands/status/status.tsx (8 lines)
    Claude Code impl: renders <Settings onClose={onDone} context={context}
    defaultTab="Status" />. The Status tab in the Settings component shows:
    version, model, account, API connectivity, tool statuses.
    immediate: true (executes without streaming check).
    Also see: src/commands/stats/stats.tsx — renders <Stats onClose={onDone} />
    which shows usage statistics (separate command in Claude Code).
    Cascade impl: merges Claude Code's /status + /stats + original /summary
    into a single comprehensive status dashboard. Outputs Rich text panel
    with session info, model details, token estimates, and tool counts.
    """
    name = "status"
    description = "Show session status and usage stats"
    aliases = ["/summary", "/stats"]
    category = "Workflow"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        from cascade.ui.banner import VERSION

        # Session stats
        msg_count = len(ctx.engine.messages)
        user_msgs = sum(
            1 for m in ctx.engine.messages if m.get("role") == "user"
        )
        assistant_msgs = sum(
            1 for m in ctx.engine.messages if m.get("role") == "assistant"
        )
        system_msgs = sum(
            1 for m in ctx.engine.messages if m.get("role") == "system"
        )

        # Token estimate (block-aware, ref: tokenEstimation.ts L203-435)
        from cascade.utils.tokens import estimate_message_tokens
        est_tokens = estimate_message_tokens(ctx.engine.messages)

        # Session duration
        start_time = getattr(ctx.repl, "_session_start", None)
        if start_time:
            elapsed = int(time.time() - start_time)
            minutes, seconds = divmod(elapsed, 60)
            duration = f"{minutes}m {seconds}s"
        else:
            duration = "unknown"

        # Tool count
        tool_count = 0
        if ctx.engine.registry:
            tool_count = len(ctx.engine.registry.list_tools())

        # Current theme
        theme = getattr(ctx.repl, "_current_theme", "dark")

        lines = [
            "[bold]Cascade Status[/bold]\n",
            f"  [bold]Version:[/bold]   v{VERSION}",
            f"  [bold]Provider:[/bold]  [#0087ff]{ctx.engine.client.provider}[/#0087ff]",
            f"  [bold]Model:[/bold]     [bold]{ctx.engine.client.model_name}[/bold]",
            "",
            f"  [bold]Session:[/bold]   {duration}",
            f"  [bold]Messages:[/bold]  {msg_count} total  "
            f"({user_msgs} user / {assistant_msgs} assistant / {system_msgs} system)",
            f"  [bold]Est. tokens:[/bold] ~{est_tokens:,}",
            f"  [bold]Tools:[/bold]     {tool_count} registered",
            f"  [bold]Theme:[/bold]     {theme}",
        ]

        await ctx.output_rich("\n".join(lines))
