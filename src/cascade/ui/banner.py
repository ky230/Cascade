"""Cascade CLI welcome banner with gradient coloring."""
from cascade.ui.colors import GRADIENT, BOLD, RESET, DIM, CYAN, BLUE, GREEN, LIGHT_CYAN

VERSION = "0.1.0"

ASCII_ART = [
    r" ⎧ ⊚ ",
    r" ⎪  ↘ ⊚       ██████╗ █████╗ ███████╗ ██████╗ █████╗ ██████╗ ███████╗",
    r" ⎨    ↘ ■     ██╔════╝██╔══██╗██╔════╝██╔════╝██╔══██╗██╔══██╗██╔════╝",
    r" ⎪      ↘     ██║     ███████║███████╗██║     ███████║██║  ██║█████╗  ",
    r" ⎩        ⊚   ██║     ██╔══██║╚════██║██║     ██╔══██║██║  ██║██╔══╝  ",
    r"              ╚██████╗██║  ██║███████║╚██████╗██║  ██║██████╔╝███████╗",
    r"               ╚═════╝╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚═════╝ ╚══════╝",
]


def render_banner() -> str:
    """Render gradient-colored ASCII art banner with physics cascade graph."""
    lines = []
    # Render the particle graph (left) in bright cyan and CASCADE in gradient
    for i, line in enumerate(ASCII_ART):
        if "█" in line or "╚" in line:
            # Find the split point where the massive text starts
            idx = line.find("█") if "█" in line else line.find("╚")
            left_part = line[:idx]
            right_part = line[idx:]
            color = GRADIENT[i % len(GRADIENT)]
            # Left graph: cyan, Right text: bold gradient
            lines.append(f"{CYAN}{left_part}{BOLD}{color}{right_part}{RESET}")
        else:
            lines.append(f"{CYAN}{line}{RESET}")

    return "\n".join(lines)


def render_status_bar(provider: str, model: str) -> str:
    """Render the metadata box UI with dynamic width and hierarchical coloring."""
    # Plain-text segments for width calculation (no ANSI codes)
    left_clean = f" ⚛  HEP Agentic Orchestrator v{VERSION} "
    sep_clean = " │ "
    right_clean = f" {provider}  ──  {model} "

    # Total visible width inside the box (between the outer │ borders)
    inner_width = len(left_clean) + len(sep_clean) + len(right_clean)

    # Colored segments
    left_colored = f" {LIGHT_CYAN}⚛{RESET}  {DIM}HEP Agentic Orchestrator v{VERSION}{RESET} "
    sep_colored = f" {DIM}│{RESET} "
    right_colored = f" {BLUE}{provider}{RESET}  {DIM}──{RESET}  {GREEN}{model}{RESET} "

    top    = f" {DIM}╭{'─' * inner_width}╮{RESET}"
    middle = f" {DIM}│{RESET}{left_colored}{sep_colored}{right_colored}{DIM}│{RESET}"
    bottom = f" {DIM}╰{'─' * inner_width}╯{RESET}"

    return f"{top}\n{middle}\n{bottom}"

# ── Rich-compatible banner for Textual TUI ──────────────────────────
from rich.text import Text as RichText
from rich.panel import Panel
from rich.console import Group


def render_banner_rich(provider: str, model: str) -> Group:
    """Render the ASCII art banner + status as Rich renderables for Textual."""
    # Gradient colors (Deep Sea Blue → Cyan)
    gradient_hex = ["#005fff", "#0087ff", "#00afff", "#00d7d7", "#00d7af", "#5fd7ff"]

    banner_lines = []
    for i, line in enumerate(ASCII_ART):
        color = gradient_hex[i % len(gradient_hex)]
        banner_lines.append(RichText(line, style=f"bold {color}"))

    # Status bar
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
