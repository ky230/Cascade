# Cascade Phase 2c: CLI Polish Refinement (Dynamic Box & Prompt)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refine the Cascade CLI visual polish based on user feedback. Specifically: replace the generic `You>` prompt with a clean, colored `>` prompt; dynamically resize the metadata status box based on string length to prevent overflow; replace the `❖` icon with `⚛`; and apply hierarchical coloring (cyan/blue/green/dim) to the status bar text.

**Architecture:** Modifies existing UI and CLI modules (`src/cascade/ui/banner.py` and `src/cascade/cli.py`). Uses the identical `cascade.ui.colors` constants. Zero further dependencies required. 

---

### Task 1: Update Banner Status Bar

**Files:**
- Modify: `src/cascade/ui/banner.py`

**Step 1: Write implementation**

**Instruction:** Replace the `render_status_bar` function to dynamically calculate width and apply colors. Ensure `colors` imports are updated at the top of the file to include `BLUE`, `GREEN`, and `LIGHT_CYAN`.

```python
# src/cascade/ui/banner.py (Partial replacement)
from cascade.ui.colors import GRADIENT, BOLD, RESET, DIM, CYAN, BLUE, GREEN, LIGHT_CYAN

# ... (Keep VERSION and ASCII_ART and render_banner as is) ...

def render_status_bar(provider: str, model: str) -> str:
    """Render the metadata box UI with dynamic width and hierarchical coloring."""
    
    # Text components with color styling
    left_text_clean = f" ⚛  HEP Agentic Orchestrator v{VERSION}    "
    right_text_clean = f"    {provider}  ──  {model} "
    
    left_text_colored = f" {LIGHT_CYAN}⚛{RESET}  {DIM}HEP Agentic Orchestrator v{VERSION}{RESET}    "
    right_text_colored = f"    {BLUE}{provider}{RESET}  {DIM}──{RESET}  {GREEN}{model}{RESET} "
    
    # Dynamic Box Calculation
    visible_width = len(left_text_clean) + 1 + len(right_text_clean) 
    
    top    = f" {DIM}╭{'─' * visible_width}╮{RESET}"
    middle = f" {DIM}│{RESET}{left_text_colored}{DIM}│{RESET}{right_text_colored}{DIM}│{RESET}"
    bottom = f" {DIM}╰{'─' * visible_width}╯{RESET}"
    
    return f"{top}\n{middle}\n{bottom}"
```

**Step 2: Run verification**
Run: `python -c "from cascade.ui.banner import render_status_bar; print(render_status_bar('gemini', 'gemini/gemini-3.1-flash-lite-preview'))"`
Expected output: A visually perfect, enclosed box without right border overflow, with colored internal elements.

**Step 3: Commit**
```bash
git add src/cascade/ui/banner.py
git commit -m "style(ui): dynamic status bar resizing with hierarchical coloring and atom icon"
```

---

### Task 2: Refine CLI Prompt Aesthetics

**Files:**
- Modify: `src/cascade/cli.py`

**Step 1: Write implementation**

**Instruction:** Modify `interactive_chat` loop inside `src/cascade/cli.py`. Change `You>` to a clean `> ` using `CYAN` color. Keep Cascade's response clean.

```python
# target lines to update inside async def interactive_chat(provider: str, model: str):
            user_input = input(f"\n{CYAN}{BOLD}>{RESET} ")
```

**Step 2: Commit**
```bash
git add src/cascade/cli.py
git commit -m "style(cli): refine prompt style to minimalist angle bracket"
```

---

## Execution Options

- **Option 1: Execute in this session** → 调用 /sp-subagent-driven-dev 或 /sp-executing-plans
- **Option 2: Open a new session** → 在新会话中加载此计划
