from cascade.commands.base import BaseCommand, CommandContext


class ExitCommand(BaseCommand):
    name = "exit"
    description = "Exit Cascade"
    aliases = ["/quit"]
    category = "Session"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        ctx.console.print("[dim]Goodbye![/dim]")
        raise SystemExit(0)
