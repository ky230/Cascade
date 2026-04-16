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

        # Token count — prefer real API usage, fallback to LiteLLM estimate
        api_input = getattr(ctx.engine, "session_input_tokens", 0)
        api_output = getattr(ctx.engine, "session_output_tokens", 0)
        if (api_input + api_output) > 0:
            token_str = f"{api_input + api_output:,}"
        else:
            from cascade.utils.tokens import precise_token_count
            from cascade.services.api_config import get_litellm_kwargs
            kwargs = get_litellm_kwargs(ctx.engine.client.provider, ctx.engine.client.model_name)
            est_tokens = precise_token_count(ctx.engine.messages, kwargs["model"])
            token_str = f"~{est_tokens:,}"

        if msg_count <= 2:
            await ctx.output_rich(
                "[dim]Too few messages to compact "
                f"({msg_count} messages, {token_str} tokens).[/dim]"
            )
            return

        await ctx.output_rich(
            f"[bold]Compact[/bold]\n"
            f"  Messages: {msg_count}\n"
            f"  Tokens: {token_str}\n"
            f"  [dim](Full LLM-based compaction coming in a future release)[/dim]"
        )
