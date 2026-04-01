from cascade.commands.base import BaseCommand, CommandContext
from rich.table import Table


class HelpCommand(BaseCommand):
    name = "help"
    description = "Show available commands"
    aliases = ["/?"]
    category = "Session"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        groups = ctx.repl.router.get_commands_by_category()

        # Category display config: emoji + color
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

        table = Table(
            show_header=True,
            header_style="bold #5fd7ff",
            border_style="dim",
            expand=False,
            title="[bold]Cascade Commands[/bold]",
            title_style="#5fd7ff",
        )
        table.add_column("Command", style="bold #00d7af", min_width=20)
        table.add_column("Description", style="dim")

        for cat_name, cmds in groups.items():
            emoji, color = cat_style.get(cat_name, ("▪", "dim"))
            table.add_row(
                f"\n{emoji} [bold {color}]{cat_name}[/bold {color}]", ""
            )
            for cmd in sorted(cmds, key=lambda c: c.name):
                alias_str = ""
                if cmd.aliases:
                    alias_str = f" [dim]({', '.join(cmd.aliases)})[/dim]"
                table.add_row(f"  /{cmd.name}{alias_str}", cmd.description)

        ctx.console.print(table)
        ctx.console.print(
            "[dim]Tip: Type / and start typing for fuzzy autocomplete[/dim]"
        )
