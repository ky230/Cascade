"""Cascade CLI welcome banner — Rich-only rendering."""
from rich.text import Text as RichText
from rich.panel import Panel
from rich.console import Group

VERSION = "0.2.0"

_LOGO = [
    r"██████╗ █████╗ ███████╗ ██████╗ █████╗ ██████╗ ███████╗",
    r"██╔════╝██╔══██╗██╔════╝██╔════╝██╔══██╗██╔══██╗██╔════╝",
    r"██║     ███████║███████╗██║     ███████║██║  ██║█████╗  ",
    r"██║     ██╔══██║╚════██║██║     ██╔══██║██║  ██║██╔══╝  ",
    r"╚██████╗██║  ██║███████║╚██████╗██║  ██║██████╔╝███████╗",
    r" ╚═════╝╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚═════╝ ╚══════╝",
]

_L = [
    "●·  ·  ·    ",  # 12  gen-0 beam ● + halo dots
    " ╲ · ╲  ·   ",  # 12  two beam tracks + radiation ·
    "  ╲·  ╲✦    ",  # 12  tracks converge → vertex ✦
    "   ╱╲  ╲·   ",  # 12  primary split: 3 branches
    "  ╱  ╲· ╲   ",  # 12  secondary spread
    " ·  ·  ·  · ",  # 12  3rd-gen endpoints
]

_R = [
    "   · ·  ·●  ",  # 12  halo dots + beam ●
    "   · ╱ ·╱   ",  # 12  tracks + radiation
    "   ✦╱  ·╱   ",  # 12  vertex ✦ + track
    "  ·╱  ╱╲    ",  # 12  primary split
    "  ╱ ·╱  ╲   ",  # 12  secondary
    " ·  ·  ·  · ",  # 12  endpoints
]

_max_len = max(len(l) for l in _LOGO)
ASCII_ART = [f" {_L[i]} {_LOGO[i].ljust(_max_len)} {_R[i]}" for i in range(6)]


def render_status_bar(provider: str, model: str) -> Panel:
    """Render just the status bar panel (provider + model)."""
    status = RichText.from_markup(
        f" [#5fd7ff]⚛[/#5fd7ff]  [dim]HEP Agentic Orchestrator[/dim] [#ff00ff]v{VERSION}[/#ff00ff]"
        f"  [dim]│[/dim]  [#0087ff]{provider}[/#0087ff]"
        f"  [dim]──[/dim]  [green]{model}[/green] "
    )
    return Panel(status, border_style="dim", expand=False)


def render_banner_rich(provider: str, model: str) -> Group:
    """Render the ASCII art banner + status as Rich renderables."""
    import os

    gradient_hex = ["#005fff", "#0087ff", "#00afff", "#00d7d7", "#00d7af", "#5fd7ff"]

    banner_lines = []
    for i, line in enumerate(ASCII_ART):
        color = gradient_hex[i % len(gradient_hex)]
        banner_lines.append(RichText(line, style=f"bold {color}"))

    # Top banner: version + working directory (model info lives in bottom toolbar)
    cwd = os.getcwd()
    home = os.path.expanduser("~")
    if cwd.startswith(home):
        cwd_display = "~" + cwd[len(home):]
    else:
        cwd_display = cwd

    status = RichText.from_markup(
        f" [#5fd7ff]⚛[/#5fd7ff]  [dim]HEP Agentic Orchestrator[/dim] [#00d7af]v{VERSION}[/#00d7af]"
        f"  [dim]│[/dim]  [#0087ff]📂 {cwd_display}[/#0087ff] "
    )
    status_panel = Panel(status, border_style="dim", expand=False)

    return Group(*banner_lines, "", status_panel)

