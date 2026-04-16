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
            "Rules": ("📜", "#ffd700"),
        }

        lines = ["[bold #5fd7ff]═══ Cascade Commands ═══[/bold #5fd7ff]", ""]
        for cat_name, cmds in groups.items():
            emoji, color = cat_style.get(cat_name, ("▪", "dim"))
            lines.append(f"  {emoji} [bold {color}]{cat_name}[/bold {color}]")
            lines.append(f"  [dim]{'─' * (len(cat_name) + 4)}[/dim]")
            for cmd in sorted(cmds, key=lambda c: c.name):
                aliases = ""
                if cmd.aliases:
                    aliases = f" [dim]({', '.join(cmd.aliases)})[/dim]"
                lines.append(
                    f"    [bold #00d7af]/{cmd.name}[/bold #00d7af]{aliases}"
                    f"  [dim]{cmd.description}[/dim]"
                )
            lines.append("")
        lines.append("[dim]Tip: Type / for command autocomplete dropdown[/dim]")
        await ctx.output_rich("\n".join(lines))
