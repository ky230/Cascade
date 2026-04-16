from cascade.commands.base import BaseCommand, CommandContext
from cascade.ui.styles import THEMES, get_tcss, hot_swap_css, DEFAULT_THEME


class ThemeCommand(BaseCommand):
    """Switch color theme with live preview.

    Reference: claude-code src/commands/theme/theme.tsx (57 lines)
    Claude Code impl: renders <ThemePicker> JSX component using Ink's
    useTheme() hook. User selects from interactive picker, theme applied
    instantly via setTheme(setting).

    Also ref: Gemini CLI theme-manager.ts (662 lines) — ThemeManager
    singleton with 17 built-in themes (Dracula, Solarized, Tokyo Night,
    GitHub, etc.), custom JSON file loading, terminal background detection.

    Cascade impl: 3 built-in themes (dark, light, cms). Theme switch is
    instant — regenerates TCSS from ThemeColors palette and applies via
    Textual's stylesheet.source + refresh_css(). No ThemePicker JSX,
    no terminal background detection.
    """
    name = "theme"
    description = "Switch color theme"
    category = "UI"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        arg = args.strip().lower()

        if arg and arg in THEMES:
            # Apply theme via hot_swap_css — the only correct way to do
            # runtime CSS replacement in Textual 8.x. See styles.py docstring.
            new_css = get_tcss(arg)
            app = ctx.repl  # The CascadeApp instance
            hot_swap_css(app, new_css)
            app._current_theme = arg

            t = THEMES[arg]
            await ctx.output_rich(
                f"[{t.accent}]■[/{t.accent}] "
                f"[bold]Theme: {t.name}[/bold] — {t.description}"
            )
            return

        if arg and arg not in THEMES:
            await ctx.output_rich(
                f"[red]Unknown theme: {arg}[/red]\n"
                f"[dim]Available: {', '.join(THEMES.keys())}[/dim]"
            )
            return

        # No arg: show interactive theme palette
        ctx.repl.show_theme_palette()
