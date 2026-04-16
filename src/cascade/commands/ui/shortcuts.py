from cascade.commands.base import BaseCommand, CommandContext


class ShortcutsCommand(BaseCommand):
    """Display keyboard shortcuts for the Cascade TUI.

    Reference: claude-code src/commands/keybindings/keybindings.ts (54 lines)
    Claude Code impl: name='keybindings', creates/opens keybindings
    config file for editing (generateKeybindingsTemplate + editFileInEditor).
    NOT a shortcuts display — it's a config editor.
    Cascade impl: ORIGINAL design inspired by Gemini CLI's /shortcuts.
    Displays a formatted list of all available keyboard shortcuts in
    the Textual TUI. This is a Cascade differentiator.
    """
    name = "shortcuts"
    description = "Show keyboard shortcuts"
    aliases = ["/keys", "/keybindings"]
    category = "UI"

    SHORTCUTS = [
        ("Navigation", [
            ("↑ / ↓", "Scroll through conversation history"),
            ("Tab", "Cycle input focus"),
            ("Esc", "Cancel current operation / close modal"),
        ]),
        ("Editing", [
            ("Enter", "Send message"),
            ("Shift+Enter", "New line in input"),
            ("Ctrl+C", "Cancel streaming response"),
        ]),
        ("Commands", [
            ("/help", "Show all available commands"),
            ("/model", "Switch AI model"),
            ("/compact", "Compress conversation context"),
            ("/export", "Export conversation to file"),
        ]),
        ("Clipboard", [
            ("c", "Copy code block (when focused)"),
            ("Ctrl+Y", "Yank last AI response"),
        ]),
    ]

    async def execute(self, ctx: CommandContext, args: str) -> None:
        lines = ["[bold]Keyboard Shortcuts[/bold]\n"]
        for group_name, shortcuts in self.SHORTCUTS:
            lines.append(f"  [bold #5fd7ff]{group_name}[/bold #5fd7ff]")
            for key, desc in shortcuts:
                lines.append(
                    f"    [bold]{key:<16}[/bold] [dim]{desc}[/dim]"
                )
            lines.append("")
        await ctx.output_rich("\n".join(lines))
