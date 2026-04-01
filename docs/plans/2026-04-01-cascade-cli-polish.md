# Cascade Phase 2b: CLI Polish — Banner, Spinner, Color System

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the bare-bones `cascade chat` into a visually premium terminal experience with an ASCII art banner, animated loading spinner, colored output, and informational status bar — inspired by Gemini CLI and Claude Code, zero external dependencies beyond Python stdlib.

**Architecture:** Create a new `src/cascade/ui/` module containing: `banner.py` (ASCII art + gradient renderer), `spinner.py` (async animated spinner), `colors.py` (ANSI color constants). The existing `cli.py` will import and compose them.

**Tech Stack:** Python 3, `asyncio`, `shutil.get_terminal_size()`, ANSI escape codes (256-color), `time.perf_counter()`.

**Color Scheme:** Deep Sea Blue → Cyan gradient (scheme A). Primary: `\033[38;5;33m` (DodgerBlue), Accent: `\033[38;5;44m` (DarkCyan), Dim: `\033[38;5;245m` (Gray).

---

### Task 1: Color Constants Module

**Files:**
- Create: `src/cascade/ui/__init__.py`
- Create: `src/cascade/ui/colors.py`

**Step 1: Write implementation**

```python
# src/cascade/ui/__init__.py
```

```python
# src/cascade/ui/colors.py
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
```

**Step 2: Commit**
```bash
git add src/cascade/ui/
git commit -m "feat(ui): add ANSI color constants and gradient palette"
```

---

### Task 2: ASCII Art Banner

**Files:**
- Create: `src/cascade/ui/banner.py`

**Step 1: Write implementation**

```python
# src/cascade/ui/banner.py
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
    pad_len = max(pad_len, 1) # Prevent negative
        
    middle_padded = middle + (" " * pad_len) + "│"
    bottom = " ╰───────────────────────────────────────────────────────────────────────╯"
    
    return f"{DIM}{top}\n{middle_padded}\n{bottom}{RESET}"
```

**Step 2: Commit**
```bash
git add src/cascade/ui/banner.py
git commit -m "feat(ui): implement fused ASCII art banner with physics graph and box UI"
```

---

### Task 3: Async Loading Spinner

**Files:**
- Create: `src/cascade/ui/spinner.py`
- Create: `tests/ui/test_spinner.py`

**Step 1: Write the failing test**

```python
# tests/ui/test_spinner.py
import pytest
import asyncio
from cascade.ui.spinner import Spinner

@pytest.mark.asyncio
async def test_spinner_lifecycle():
    spinner = Spinner(message="Thinking")
    
    # Start spinner
    spinner.start()
    assert spinner._task is not None
    
    # Let it run briefly
    await asyncio.sleep(0.15)
    
    # Stop and get elapsed time
    elapsed = spinner.stop()
    assert elapsed > 0.1
    assert spinner._task is None or spinner._task.done()
```

**Step 2: Run test to verify it fails**
Run: `python3 -m pytest tests/ui/test_spinner.py -v`
Expected: FAIL (ModuleNotFoundError)

**Step 3: Write minimal implementation**

```python
# src/cascade/ui/spinner.py
"""Async animated spinner for API wait states. Zero dependencies."""
import sys
import asyncio
import time
from cascade.ui.colors import CYAN, DIM, RESET

SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

class Spinner:
    """Async spinner that shows animated feedback during API calls."""

    def __init__(self, message: str = "Thinking"):
        self.message = message
        self._task: asyncio.Task | None = None
        self._start_time: float = 0

    def start(self):
        """Start the spinner animation."""
        self._start_time = time.perf_counter()
        self._task = asyncio.get_event_loop().create_task(self._animate())

    def stop(self) -> float:
        """Stop the spinner, clear the line, return elapsed seconds."""
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
        # Clear the spinner line
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
        return time.perf_counter() - self._start_time

    async def _animate(self):
        """Render spinner frames at ~80ms interval."""
        i = 0
        try:
            while True:
                frame = SPINNER_FRAMES[i % len(SPINNER_FRAMES)]
                elapsed = time.perf_counter() - self._start_time
                text = f"\r{CYAN}{frame}{RESET} {DIM}{self.message}... ({elapsed:.1f}s){RESET}"
                sys.stdout.write(text)
                sys.stdout.flush()
                i += 1
                await asyncio.sleep(0.08)
        except asyncio.CancelledError:
            pass
```

**Step 4: Run test to verify it passes**
Run: `python3 -m pytest tests/ui/ -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/cascade/ui/spinner.py tests/ui/
git commit -m "feat(ui): implement async loading spinner with elapsed timer"
```

---

### Task 4: Rewrite CLI with Full Polish

**Files:**
- Modify: `src/cascade/cli.py`

**Step 1: Write the polished implementation**

```python
# src/cascade/cli.py
import argparse
import asyncio
import os
import time
from dotenv import load_dotenv
from cascade.core.agent import Agent
from cascade.ui.banner import render_banner, render_status_bar
from cascade.ui.spinner import Spinner
from cascade.ui.colors import BLUE, CYAN, DIM, RED, RESET, BOLD

def main():
    load_dotenv()
    default_provider = os.getenv("CASCADE_DEFAULT_PROVIDER", "openai")
    default_model = os.getenv("CASCADE_DEFAULT_MODEL", "gpt-4o")

    parser = argparse.ArgumentParser(description="Cascade: CLI Agentic Orchestrator for HEP")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    chat_parser = subparsers.add_parser("chat", help="Start an interactive chat session.")
    chat_parser.add_argument("--provider", type=str, default=default_provider)
    chat_parser.add_argument("--model", type=str, default=default_model)

    args = parser.parse_args()

    if args.command == "chat":
        asyncio.run(interactive_chat(args.provider, args.model))

async def interactive_chat(provider: str, model: str):
    # Welcome banner
    print(render_banner())
    print(render_status_bar(provider, model))
    print(f"\n  {DIM}Type {BOLD}exit{RESET}{DIM} or {BOLD}quit{RESET}{DIM} to end. {BOLD}Ctrl+C{RESET}{DIM} to interrupt.{RESET}\n")
    
    agent = Agent(provider=provider, model_name=model)
    
    while True:
        try:
            user_input = input(f"{DIM}You>{RESET} ")
            if user_input.lower() in ["exit", "quit"]:
                print(f"\n{DIM}Exiting Cascade. Goodbye! 👋{RESET}")
                break
            if not user_input.strip():
                continue
            
            # Spinner during API call
            spinner = Spinner(message="Thinking")
            spinner.start()
            
            response = await agent.chat(user_input)
            
            elapsed = spinner.stop()
            
            # Colored response
            print(f"\n{BLUE}{BOLD}Cascade>{RESET} {response}")
            print(f"{DIM}({elapsed:.1f}s){RESET}\n")
            
        except KeyboardInterrupt:
            print(f"\n\n{DIM}Exiting Cascade. Goodbye! 👋{RESET}")
            break
        except Exception as e:
            print(f"\n{RED}[Error]{RESET} {str(e)}\n")

if __name__ == "__main__":
    main()
```

**Step 2: Run full test suite**
Run: `python3 -m pytest tests/ -v`
Expected: All PASS (existing tests unaffected)

**Step 3: Run manual visual verification**
Run: `cascade chat --provider gemini --model "gemini/gemini-3.1-flash-lite-preview"`
Expected: See gradient banner, status bar, spinner animation, colored responses, error in red.

**Step 4: Commit**
```bash
git add src/cascade/cli.py
git commit -m "feat(cli): full visual polish — banner, spinner, colors, status bar"
```

---

### Task 5: Update Walkthrough

**Files:**
- Modify: `docs/walkthrough.md`

**Step 1: Append Phase 2b completion entry**

Append to `docs/walkthrough.md`:
```markdown

## Phase 2b: CLI Visual Polish
- **Completed:** 2026-04-01
- **Achievements:** Added gradient ASCII art banner, async loading spinner with elapsed timer, ANSI 256-color system (Deep Sea Blue/Cyan palette), model status bar, colored prompts and error output. Zero external dependencies — pure Python stdlib ANSI rendering.
```

**Step 2: Commit and merge**
```bash
git add docs/walkthrough.md
git commit -m "docs: record Phase 2b CLI polish in walkthrough"
```

---

## Execution Options

- **Option 1: Execute in this session** → 调用 /sp-executing-plans
- **Option 2: Open a new session** → 在新会话中调用 /sp-executing-plans 并加载此计划
