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
        ctx.console.print("[#00d7af]✓ Conversation history cleared.[/#00d7af]")
