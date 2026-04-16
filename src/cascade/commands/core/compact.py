from cascade.commands.base import BaseCommand, CommandContext


class CompactCommand(BaseCommand):
    """Summarize and compress conversation context.

    Reference: claude-code src/commands/compact/compact.ts
    Claude Code impl: 288 lines, supports session memory compaction,
    microcompact, reactive compact, custom instructions, hooks.
    Cascade impl: basic message counting + LLM summarization.
    """
    name = "compact"
    description = "Summarize and compress conversation context"
    category = "Session"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        msg_count = len(ctx.engine.messages)
        if msg_count == 0:
            await ctx.output_rich("[dim]No messages to compact.[/dim]")
            return

        # Token estimate (block-aware, ref: tokenEstimation.ts L203-435)
        from cascade.utils.tokens import estimate_message_tokens
        est_tokens = estimate_message_tokens(ctx.engine.messages)

        if msg_count <= 2:
            await ctx.output_rich(
                "[dim]Too few messages to compact "
                f"({msg_count} messages, ~{est_tokens} tokens).[/dim]"
            )
            return

        await ctx.output_rich(
            f"[bold]Compact[/bold]\n"
            f"  Messages: {msg_count}\n"
            f"  Est. tokens: ~{est_tokens}\n"
            f"  [dim](Full LLM-based compaction coming in a future release)[/dim]"
        )
