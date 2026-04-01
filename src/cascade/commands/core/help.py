from cascade.commands.base import BaseCommand, CommandContext


class HelpCommand(BaseCommand):
    name = "help"
    description = "Show available commands"
    aliases = ["/?"]
    category = "Session"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        groups = ctx.repl.router.get_commands_by_category()

        cat_emoji = {
            "Session": "🟢", "Model": "🔵", "Tools": "🟠",
            "Git": "🔴", "Setup": "⚪", "UI": "🟤",
            "Workflow": "🔷", "Plugins": "🔶", "Memory": "🧩",
        }

        lines = ["═══ Cascade Commands ═══", ""]
        for cat_name, cmds in groups.items():
            emoji = cat_emoji.get(cat_name, "▪")
            lines.append(f"  {emoji} {cat_name}")
            lines.append(f"  {'─' * (len(cat_name) + 4)}")
            for cmd in sorted(cmds, key=lambda c: c.name):
                aliases = f" ({', '.join(cmd.aliases)})" if cmd.aliases else ""
                lines.append(f"    /{cmd.name}{aliases:<20s}  {cmd.description}")
            lines.append("")

        lines.append("Tip: Type / for command suggestions")
        await ctx.output("\n".join(lines))
