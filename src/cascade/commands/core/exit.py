from cascade.commands.base import BaseCommand, CommandContext


class ExitCommand(BaseCommand):
    name = "exit"
    description = "Exit Cascade"
    aliases = ["/quit"]
    category = "Session"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        if hasattr(ctx.repl, 'exit'):
            # Textual mode — graceful exit
            ctx.repl.exit()
        else:
            raise SystemExit(0)
