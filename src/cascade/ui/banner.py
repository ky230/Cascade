"""Cascade CLI welcome banner with gradient coloring."""
from cascade.ui.colors import GRADIENT, BOLD, RESET, DIM, CYAN

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
    """Render the metadata box UI."""
    top    = " ╭───────────────────────────────────────────────────────────────────────╮"
    middle = f" │  ❖  HEP Agentic Orchestrator v{VERSION}    │    {provider}  ──  {model}"

    # Calculate padding to ensure the right border aligns exactly
    visible_len = len(f" │  ❖  HEP Agentic Orchestrator v{VERSION}    │    {provider}  ──  {model}")
    pad_len = 73 - visible_len
    pad_len = max(pad_len, 1)  # Prevent negative

    middle_padded = middle + (" " * pad_len) + "│"
    bottom = " ╰───────────────────────────────────────────────────────────────────────╯"

    return f"{DIM}{top}\n{middle_padded}\n{bottom}{RESET}"
