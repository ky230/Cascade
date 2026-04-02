from cascade.commands.base import BaseCommand, CommandContext


class HelpCommand(BaseCommand):
    name = "help"
    description = "Show available commands"
    aliases = ["/?"]
    category = "Session"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        groups = ctx.repl.router.get_commands_by_category()

        cat_style = {
            "Session": ("🟢", "#00d7af"),
            "Model": ("🔵", "#0087ff"),
            "Tools": ("🟠", "#ff8700"),
            "Git": ("🔴", "#ff5f5f"),
            "Setup": ("⚪", "#a0a0a0"),
            "UI": ("🟤", "#d7875f"),
            "Workflow": ("🔷", "#5f87ff"),
            "Plugins": ("🔶", "#ffaf00"),
            "Memory": ("🧩", "#af87ff"),
        }

        lines = ["# ═══ Cascade Commands ═══", ""]
        for cat_name, cmds in groups.items():
            emoji, _ = cat_style.get(cat_name, ("▪", ""))
            lines.append(f"### {emoji} {cat_name}")
            for cmd in sorted(cmds, key=lambda c: c.name):
                aliases = ""
                if cmd.aliases:
                    aliases = f" *({', '.join(cmd.aliases)})*"
                lines.append(f"- `/{cmd.name}`{aliases} : {cmd.description}")
            lines.append("")
        lines.append("> Tip: Type `/` for command autocomplete dropdown")
        await ctx.output("\n".join(lines))
