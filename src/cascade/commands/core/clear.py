from cascade.commands.base import BaseCommand, CommandContext


class ClearCommand(BaseCommand):
    name = "clear"
    description = "Clear conversation history"
    category = "Session"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        # Keep system prompt (index 0), drop everything else
        if ctx.engine.messages and ctx.engine.messages[0].get("role") == "system":
            ctx.engine.messages = ctx.engine.messages[:1]
        else:
            ctx.engine.messages = []

        # Also clear UI if in Textual mode
        if hasattr(ctx.repl, 'action_clear_chat'):
            ctx.repl.action_clear_chat()

        await ctx.output_rich("[#00d7af]✓ Conversation history cleared.[/#00d7af]")
