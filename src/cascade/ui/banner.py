"""Cascade CLI welcome banner — Rich-only rendering."""
from rich.text import Text as RichText
from rich.panel import Panel
from rich.console import Group

VERSION = "0.2.0"

ASCII_ART = [
    r" ⎧ ⊚ ",
    r" ⎪  ↘ ⊚       ██████╗ █████╗ ███████╗ ██████╗ █████╗ ██████╗ ███████╗",
    r" ⎨    ↘ ■     ██╔════╝██╔══██╗██╔════╝██╔════╝██╔══██╗██╔══██╗██╔════╝",
    r" ⎪      ↘     ██║     ███████║███████╗██║     ███████║██║  ██║█████╗  ",
    r" ⎩        ⊚   ██║     ██╔══██║╚════██║██║     ██╔══██║██║  ██║██╔══╝  ",
    r"              ╚██████╗██║  ██║███████║╚██████╗██║  ██║██████╔╝███████╗",
    r"               ╚═════╝╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚═════╝ ╚══════╝",
]


def render_banner_rich(provider: str, model: str) -> Group:
    """Render the ASCII art banner + status as Rich renderables."""
    gradient_hex = ["#005fff", "#0087ff", "#00afff", "#00d7d7", "#00d7af", "#5fd7ff"]

    banner_lines = []
    for i, line in enumerate(ASCII_ART):
        color = gradient_hex[i % len(gradient_hex)]
        banner_lines.append(RichText(line, style=f"bold {color}"))

    status = RichText.from_markup(
        f" [#5fd7ff]⚛[/#5fd7ff]  [dim]HEP Agentic Orchestrator v{VERSION}[/dim]"
        f"  [dim]│[/dim]  [#0087ff]{provider}[/#0087ff]"
        f"  [dim]──[/dim]  [green]{model}[/green] "
    )
    status_panel = Panel(
        status,
        border_style="dim",
        expand=False,
    )

    return Group(*banner_lines, "", status_panel)
