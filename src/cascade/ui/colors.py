"""ANSI 256-color constants for the Cascade CLI. Zero dependencies."""

# Deep Sea Blue → Cyan palette
BLUE = "\033[38;5;33m"       # DodgerBlue — primary brand
CYAN = "\033[38;5;44m"       # DarkCyan — accent
LIGHT_CYAN = "\033[38;5;87m" # SkyBlue — highlights
DIM = "\033[38;5;245m"       # Gray — secondary text
RED = "\033[38;5;196m"       # Bright red — errors
GREEN = "\033[38;5;40m"      # Green — success
YELLOW = "\033[38;5;220m"    # Gold — warnings
BOLD = "\033[1m"
RESET = "\033[0m"

# Gradient stops for the ASCII banner (top → bottom)
GRADIENT = [
    "\033[38;5;27m",   # Deep blue
    "\033[38;5;33m",   # Blue
    "\033[38;5;39m",   # Lighter blue
    "\033[38;5;44m",   # Cyan
    "\033[38;5;50m",   # Bright cyan
    "\033[38;5;87m",   # Light cyan
]
