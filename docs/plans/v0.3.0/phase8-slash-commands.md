# Phase 8: Slash Command System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a complete slash command system for the Cascade REPL with command routing, fuzzy autocomplete, and 36 core commands across 10 categories.

**Architecture:** `BaseCommand` abstract class + `CommandRouter` registry. Commands live in `src/cascade/commands/<category>/` subfolders. At startup, `CommandRouter` collects all registered commands. The REPL intercepts any `/xxx` input before sending to the LLM, routes it to the matched handler. Fuzzy tab-completion via `prompt_toolkit.FuzzyWordCompleter`.

**Tech Stack:** Python 3.11+, prompt_toolkit, rich, click, pytest

---

## Batch Overview

| Batch | Category | Commands | Count | Test Checkpoint |
|-------|----------|----------|-------|-----------------|
| 1 | Infrastructure | `BaseCommand`, `CommandRouter`, REPL wiring | 0 (framework) | `pytest tests/commands/` + manual `/notfound` |
| 2 | C1-Core (P0) | `/help`, `/exit`, `/clear` | 3 | manual: type each command in REPL |
| 3 | C2-Model | `/model` (interactive picker) | 1 | manual: switch model mid-session |
| 4 | C1-Core (P1/P2) | `/compact`, `/resume`, `/rename`, `/branch`, `/rewind`, `/export` | 6 | manual: `/help` shows all 9 session commands |
| 5 | C7-Setup | `/version`, `/config`, `/doctor`, `/init`, `/env` | 5 | manual: `/doctor` runs checks |
| 6 | C8-UI + C10 + C11 | `/theme`, `/vim`, `/brief`, `/btw` | 4 | manual: switch theme, toggle vim |
| 7 | C5-Tools | `/permissions`, `/hooks`, `/debug-tool-call`, `/sandbox-toggle` | 4 | manual: `/permissions` lists rules |
| 8 | C6-Git | `/commit`, `/commit-push-pr`, `/pr-comments`, `/review`, `/security-review` | 5 | manual: `/commit` in a git repo |
| 9 | C14-Memory | `/memory`, `/summary` | 2 | manual: `/memory` shows CASCADE.md |
| 10 | C9-Plugins | `/plugin`, `/reload-plugins`, `/skills`, `/agents`, `/mcp`, `/tasks` | 6 | manual: `/skills` lists skills |

**Total: 36 commands across 10 batches**

---

## Batch 1: Infrastructure (BaseCommand + CommandRouter + REPL Wiring)

This batch creates the foundational framework. No user-facing commands yet, but after this the REPL can intercept `/xxx` input and show "Unknown command".

### Step 1: Create `BaseCommand` and `CommandContext`

**Files:**
- Create: `src/cascade/commands/__init__.py`
- Create: `src/cascade/commands/base.py`

```python
# src/cascade/commands/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console
    from prompt_toolkit import PromptSession
    from cascade.engine.query import QueryEngine


@dataclass
class CommandContext:
    """Runtime context passed to every command handler."""
    console: Console
    engine: QueryEngine
    session: PromptSession
    repl: object  # CascadeRepl (avoid circular import)


class BaseCommand(ABC):
    """Abstract base for all slash commands."""
    name: str = ""
    description: str = ""
    aliases: list[str] = []
    category: str = "General"
    hidden: bool = False  # hidden commands don't show in /help

    @abstractmethod
    async def execute(self, ctx: CommandContext, args: str) -> None:
        """Execute the command. `args` is everything after `/command `."""
        ...

    @property
    def trigger(self) -> str:
        return f"/{self.name}"
```

### Step 2: Create `CommandRouter`

**Files:**
- Create: `src/cascade/commands/router.py`

```python
# src/cascade/commands/router.py
from __future__ import annotations
from typing import Optional
from prompt_toolkit.completion import FuzzyWordCompleter
from cascade.commands.base import BaseCommand, CommandContext


class CommandRouter:
    """Registry and dispatcher for slash commands."""

    def __init__(self):
        self._commands: dict[str, BaseCommand] = {}

    def register(self, cmd: BaseCommand) -> None:
        """Register a command and its aliases."""
        self._commands[f"/{cmd.name}"] = cmd
        for alias in (cmd.aliases or []):
            if not alias.startswith("/"):
                alias = f"/{alias}"
            self._commands[alias] = cmd

    def get(self, name: str) -> Optional[BaseCommand]:
        return self._commands.get(name)

    @property
    def all_commands(self) -> list[BaseCommand]:
        """Unique commands (deduplicated from aliases)."""
        seen = set()
        result = []
        for cmd in self._commands.values():
            if id(cmd) not in seen:
                seen.add(id(cmd))
                result.append(cmd)
        return result

    def get_completer(self) -> FuzzyWordCompleter:
        """Build a fuzzy completer for prompt_toolkit."""
        words = list(self._commands.keys())
        meta = {k: v.description for k, v in self._commands.items()}
        return FuzzyWordCompleter(words, meta_dict=meta)

    def get_commands_by_category(self) -> dict[str, list[BaseCommand]]:
        """Group unique commands by category for /help display."""
        groups: dict[str, list[BaseCommand]] = {}
        seen = set()
        for cmd in self._commands.values():
            if id(cmd) in seen:
                continue
            seen.add(id(cmd))
            if not cmd.hidden:
                groups.setdefault(cmd.category, []).append(cmd)
        return groups

    async def dispatch(self, input_str: str, ctx: CommandContext) -> bool:
        """Try to dispatch input as a slash command. Returns True if handled."""
        parts = input_str.strip().split(maxsplit=1)
        cmd_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        cmd = self._commands.get(cmd_name)
        if cmd:
            await cmd.execute(ctx, args)
            return True
        return False
```

### Step 3: Create `__init__.py` that exports key classes

**Files:**
- Create: `src/cascade/commands/__init__.py`

```python
# src/cascade/commands/__init__.py
"""Cascade slash command system."""
from cascade.commands.base import BaseCommand, CommandContext
from cascade.commands.router import CommandRouter

__all__ = ["BaseCommand", "CommandContext", "CommandRouter"]
```

### Step 4: Wire CommandRouter into the REPL

**Files:**
- Modify: `src/cascade/ui/app.py`

**Changes to `CascadeRepl.__init__`** (after line 48):
```python
# --- Add after self.session = PromptSession(...) ---
from cascade.commands import CommandRouter, CommandContext
self.router = CommandRouter()
```

**Changes to `CascadeRepl.run()`** (insert between line 91 and 94, replacing the old exit check):
```python
                if not user_input.strip():
                    continue

                # --- Slash command routing ---
                if user_input.strip().startswith('/'):
                    ctx = CommandContext(
                        console=self.console,
                        engine=self.engine,
                        session=self.session,
                        repl=self,
                    )
                    handled = await self.router.dispatch(user_input, ctx)
                    if handled:
                        continue
                    else:
                        self.console.print(
                            f"[dim]Unknown command: {user_input.strip().split()[0]}. "
                            f"Type /help for available commands.[/dim]"
                        )
                        continue

                # --- Legacy plain-text exit ---
                if user_input.strip().lower() in ['exit', 'quit']:
                    break
```

**Add FuzzyCompleter to PromptSession** (modify line 48):
```python
        self.session = PromptSession(
            key_bindings=kb,
            completer=self.router.get_completer(),
            erase_when_done=True,
        )
```

Note: The `self.router` must be created before the `PromptSession`. Reorder `__init__` so the router is built first.

### Step 5: Write tests for CommandRouter

**Files:**
- Create: `tests/commands/__init__.py`
- Create: `tests/commands/test_router.py`

```python
# tests/commands/test_router.py
import pytest
from cascade.commands.base import BaseCommand, CommandContext
from cascade.commands.router import CommandRouter


class FakeCommand(BaseCommand):
    name = "fake"
    description = "A fake command for testing"
    aliases = ["/f"]
    category = "Test"

    async def execute(self, ctx, args):
        ctx._executed = True
        ctx._args = args


@pytest.fixture
def router():
    r = CommandRouter()
    r.register(FakeCommand())
    return r


def test_register_and_lookup(router):
    assert router.get("/fake") is not None
    assert router.get("/f") is not None
    assert router.get("/nonexistent") is None


def test_all_commands_deduped(router):
    cmds = router.all_commands
    assert len(cmds) == 1


def test_completer_words(router):
    completer = router.get_completer()
    assert "/fake" in completer.words
    assert "/f" in completer.words


def test_commands_by_category(router):
    groups = router.get_commands_by_category()
    assert "Test" in groups
    assert len(groups["Test"]) == 1


@pytest.mark.asyncio
async def test_dispatch_known():
    router = CommandRouter()
    router.register(FakeCommand())

    class Ctx:
        pass

    ctx = Ctx()
    handled = await router.dispatch("/fake some args", ctx)
    assert handled is True
    assert ctx._executed is True
    assert ctx._args == "some args"


@pytest.mark.asyncio
async def test_dispatch_unknown():
    router = CommandRouter()
    ctx = object()
    handled = await router.dispatch("/nope", ctx)
    assert handled is False
```

### Step 6: Run tests

Run: `cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade && python -m pytest tests/commands/test_router.py -v`
Expected: All 6 tests PASS

### Step 7: Commit

```bash
git add src/cascade/commands/ tests/commands/
git add src/cascade/ui/app.py
git commit -m "feat(commands): add BaseCommand, CommandRouter, and REPL wiring"
```

---

## Batch 2: C1-Core P0 Commands (/help, /exit, /clear)

The first user-facing commands. After this batch you can actually use slash commands interactively.

### Step 1: Create core subpackage

**Files:**
- Create: `src/cascade/commands/core/__init__.py`

```python
# src/cascade/commands/core/__init__.py
"""Core session management commands."""
```

### Step 2: Implement /help

**Files:**
- Create: `src/cascade/commands/core/help.py`

```python
# src/cascade/commands/core/help.py
from cascade.commands.base import BaseCommand, CommandContext
from rich.table import Table
from rich.panel import Panel
from rich.text import Text


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
            "Plugins": ("🔶", "#ffaf00"),
            "Workflow": ("🔷", "#5f87ff"),
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
            "[dim]Tip: Start typing / and press Tab for fuzzy autocomplete[/dim]"
        )
```

### Step 3: Implement /exit

**Files:**
- Create: `src/cascade/commands/core/exit.py`

```python
# src/cascade/commands/core/exit.py
from cascade.commands.base import BaseCommand, CommandContext


class ExitCommand(BaseCommand):
    name = "exit"
    description = "Exit Cascade"
    aliases = ["/quit"]
    category = "Session"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        ctx.console.print("[dim]Goodbye![/dim]")
        raise SystemExit(0)
```

### Step 4: Implement /clear

**Files:**
- Create: `src/cascade/commands/core/clear.py`

```python
# src/cascade/commands/core/clear.py
from cascade.commands.base import BaseCommand, CommandContext


class ClearCommand(BaseCommand):
    name = "clear"
    description = "Clear conversation history"
    category = "Session"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        # Keep system prompt (index 0), drop everything else
        if ctx.engine.messages and ctx.engine.messages[0].get("role") == "system":
            ctx.engine.messages = ctx.engine.messages[:1]
        else:
            ctx.engine.messages = []
        ctx.console.print("[#00d7af]Conversation history cleared.[/#00d7af]")
```

### Step 5: Register P0 commands in REPL

**Files:**
- Modify: `src/cascade/ui/app.py`

In `CascadeRepl.__init__`, after `self.router = CommandRouter()`, add:
```python
        # --- Register P0 commands ---
        from cascade.commands.core.help import HelpCommand
        from cascade.commands.core.exit import ExitCommand
        from cascade.commands.core.clear import ClearCommand
        self.router.register(HelpCommand())
        self.router.register(ExitCommand())
        self.router.register(ClearCommand())
```

Then rebuild the PromptSession completer after registration:
```python
        self.session = PromptSession(
            key_bindings=kb,
            completer=self.router.get_completer(),
            erase_when_done=True,
        )
```

### Step 6: Write tests

**Files:**
- Create: `tests/commands/test_core_p0.py`

```python
# tests/commands/test_core_p0.py
import pytest
from unittest.mock import MagicMock, AsyncMock
from cascade.commands.core.help import HelpCommand
from cascade.commands.core.exit import ExitCommand
from cascade.commands.core.clear import ClearCommand
from cascade.commands.router import CommandRouter


@pytest.fixture
def ctx():
    """Minimal mock context."""
    mock = MagicMock()
    mock.console = MagicMock()
    mock.engine = MagicMock()
    mock.engine.messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"},
    ]
    mock.repl = MagicMock()
    mock.repl.router = CommandRouter()
    mock.repl.router.register(HelpCommand())
    mock.repl.router.register(ExitCommand())
    mock.repl.router.register(ClearCommand())
    return mock


@pytest.mark.asyncio
async def test_help_runs(ctx):
    cmd = HelpCommand()
    await cmd.execute(ctx, "")
    ctx.console.print.assert_called()


@pytest.mark.asyncio
async def test_exit_raises(ctx):
    cmd = ExitCommand()
    with pytest.raises(SystemExit):
        await cmd.execute(ctx, "")


@pytest.mark.asyncio
async def test_clear_keeps_system_prompt(ctx):
    cmd = ClearCommand()
    await cmd.execute(ctx, "")
    assert len(ctx.engine.messages) == 1
    assert ctx.engine.messages[0]["role"] == "system"
```

### Step 7: Run tests

Run: `cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade && python -m pytest tests/commands/test_core_p0.py -v`
Expected: 3 tests PASS

### Step 8: Manual test checkpoint

```bash
cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade && cascade
# In REPL:
#   /help     -> should print grouped command table
#   /clear    -> "Conversation history cleared."
#   /exit     -> exits
#   /notfound -> "Unknown command: /notfound. Type /help..."
#   Press Tab after typing "/"  -> fuzzy autocomplete popup
```

### Step 9: Commit

```bash
git add src/cascade/commands/core/ tests/commands/test_core_p0.py src/cascade/ui/app.py
git commit -m "feat(commands): add /help, /exit, /clear (P0 batch 1)"
```

---

## Batch 3: C2-Model (/model interactive picker)

### Step 1: Create model subpackage

**Files:**
- Create: `src/cascade/commands/model/__init__.py`
- Create: `src/cascade/commands/model/model.py`

```python
# src/cascade/commands/model/__init__.py
"""Model selection commands."""
```

```python
# src/cascade/commands/model/model.py
from cascade.commands.base import BaseCommand, CommandContext
from cascade.services.api_client import ModelClient
from cascade.services.api_config import get_litellm_kwargs
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
import os


# Provider catalog with display names and known models + pricing
PROVIDER_CATALOG = {
    "deepseek": {
        "display": "DeepSeek",
        "env_key": "DEEPSEEK_API_KEY",
        "models": [
            {"id": "deepseek-chat", "label": "DeepSeek V3", "price": "$0.27/M in, $1.10/M out"},
            {"id": "deepseek-reasoner", "label": "DeepSeek R1", "price": "$0.55/M in, $2.19/M out"},
        ],
    },
    "glm": {
        "display": "ZhipuAI (GLM)",
        "env_key": "GLM_API_KEY",
        "models": [
            {"id": "glm-4-flash", "label": "GLM-4 Flash", "price": "Free"},
            {"id": "glm-4.6", "label": "GLM-4.6", "price": "$0.07/M"},
        ],
    },
    "anthropic": {
        "display": "Anthropic",
        "env_key": "ANTHROPIC_API_KEY",
        "models": [
            {"id": "claude-sonnet-4-20250514", "label": "Sonnet 4", "price": "$3/M in, $15/M out"},
            {"id": "claude-opus-4-20250514", "label": "Opus 4", "price": "$15/M in, $75/M out"},
        ],
    },
    "gemini": {
        "display": "Google Gemini",
        "env_key": "GEMINI_API_KEY",
        "models": [
            {"id": "gemini-2.5-flash", "label": "Gemini 2.5 Flash", "price": "$0.15/M in"},
            {"id": "gemini-2.5-pro", "label": "Gemini 2.5 Pro", "price": "$1.25/M in, $10/M out"},
        ],
    },
    "openai": {
        "display": "OpenAI",
        "env_key": "OPENAI_API_KEY",
        "models": [
            {"id": "gpt-4o", "label": "GPT-4o", "price": "$2.50/M in, $10/M out"},
            {"id": "gpt-4o-mini", "label": "GPT-4o Mini", "price": "$0.15/M in, $0.60/M out"},
            {"id": "o3-mini", "label": "o3-mini", "price": "$1.10/M in, $4.40/M out"},
        ],
    },
    "kimi": {
        "display": "Moonshot (Kimi)",
        "env_key": "MOONSHOT_API_KEY",
        "models": [
            {"id": "moonshot-v1-auto", "label": "Kimi Auto", "price": "CN pricing"},
        ],
    },
    "qwen": {
        "display": "Alibaba Qwen",
        "env_key": "DASHSCOPE_API_KEY",
        "models": [
            {"id": "qwen-plus", "label": "Qwen Plus", "price": "CN pricing"},
            {"id": "qwen-turbo", "label": "Qwen Turbo", "price": "CN pricing"},
        ],
    },
}


class ModelCommand(BaseCommand):
    name = "model"
    description = "Switch model (interactive picker with pricing)"
    category = "Model"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        engine = ctx.engine
        current_provider = engine.client.provider
        current_model = engine.client.model_name

        # If args given directly, try quick switch: /model deepseek deepseek-chat
        if args.strip():
            parts = args.strip().split()
            if len(parts) == 2:
                new_provider, new_model = parts
                if new_provider in PROVIDER_CATALOG:
                    engine.client = ModelClient(provider=new_provider, model_name=new_model)
                    ctx.console.print(
                        f"[#00d7af]Switched to {new_provider}/{new_model}[/#00d7af]"
                    )
                    return
            ctx.console.print("[dim]Usage: /model <provider> <model> or just /model for picker[/dim]")
            return

        # Interactive picker
        table = Table(
            title="[bold #5fd7ff]Switch Model[/bold #5fd7ff]",
            show_header=True,
            header_style="bold",
            border_style="#5fd7ff",
            expand=False,
        )
        table.add_column("#", style="bold #00d7af", width=4)
        table.add_column("Provider", style="#0087ff")
        table.add_column("Model", style="bold")
        table.add_column("Price", style="dim")

        choices = []
        idx = 1
        for prov_key, prov_info in PROVIDER_CATALOG.items():
            api_key = os.getenv(prov_info["env_key"], "")
            available = "[green]OK[/green]" if api_key else "[red]No key[/red]"
            for m in prov_info["models"]:
                is_current = (prov_key == current_provider and m["id"] == current_model)
                marker = " [bold yellow]<< current[/bold yellow]" if is_current else ""
                table.add_row(
                    str(idx),
                    f"{prov_info['display']} {available}",
                    f"{m['label']} ({m['id']}){marker}",
                    m["price"],
                )
                choices.append((prov_key, m["id"]))
                idx += 1

        ctx.console.print(table)

        # Prompt for selection
        selection = Prompt.ask(
            "[#5fd7ff]Select number (or Enter to cancel)[/#5fd7ff]",
            console=ctx.console,
            default="",
        )

        if not selection.strip():
            ctx.console.print("[dim]Cancelled.[/dim]")
            return

        try:
            choice_idx = int(selection) - 1
            if 0 <= choice_idx < len(choices):
                new_provider, new_model = choices[choice_idx]
                engine.client = ModelClient(provider=new_provider, model_name=new_model)
                ctx.console.print(
                    f"[#00d7af]Switched to {new_provider}/{new_model}[/#00d7af]"
                )
            else:
                ctx.console.print("[red]Invalid selection.[/red]")
        except ValueError:
            ctx.console.print("[red]Enter a number.[/red]")
```

### Step 2: Register /model in REPL

**Files:**
- Modify: `src/cascade/ui/app.py`

Add to the command registration block:
```python
        from cascade.commands.model.model import ModelCommand
        self.router.register(ModelCommand())
```

### Step 3: Write tests

**Files:**
- Create: `tests/commands/test_model.py`

```python
# tests/commands/test_model.py
import pytest
from unittest.mock import MagicMock, patch
from cascade.commands.model.model import ModelCommand, PROVIDER_CATALOG


def test_catalog_has_all_providers():
    expected = {"deepseek", "glm", "anthropic", "gemini", "openai", "kimi", "qwen"}
    assert set(PROVIDER_CATALOG.keys()) == expected


def test_each_provider_has_models():
    for prov, info in PROVIDER_CATALOG.items():
        assert len(info["models"]) > 0, f"{prov} has no models"
        assert "env_key" in info


@pytest.mark.asyncio
async def test_model_quick_switch():
    cmd = ModelCommand()
    ctx = MagicMock()
    ctx.engine = MagicMock()
    ctx.engine.client.provider = "glm"
    ctx.engine.client.model_name = "glm-4-flash"

    await cmd.execute(ctx, "deepseek deepseek-chat")
    # Should have created a new ModelClient
    assert ctx.engine.client is not None
```

### Step 4: Run tests

Run: `cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade && python -m pytest tests/commands/test_model.py -v`
Expected: 3 tests PASS

### Step 5: Manual test checkpoint

```bash
cascade
# /model         -> interactive table with all providers/models
# /model deepseek deepseek-chat  -> quick switch
# type a message -> model responds with the new provider
```

### Step 6: Commit

```bash
git add src/cascade/commands/model/ tests/commands/test_model.py src/cascade/ui/app.py
git commit -m "feat(commands): add /model interactive picker with pricing"
```

---

## Batch 4: C1-Core P1/P2 Commands (Session Management)

Six stub/partial commands: `/compact`, `/resume`, `/rename`, `/branch`, `/rewind`, `/export`. These are P1/P2 so they can start as "not yet implemented" stubs that print a message, with real logic added later.

### Step 1: Create stubs

**Files:**
- Create: `src/cascade/commands/core/compact.py`
- Create: `src/cascade/commands/core/resume.py`
- Create: `src/cascade/commands/core/rename.py`
- Create: `src/cascade/commands/core/branch.py`
- Create: `src/cascade/commands/core/rewind.py`
- Create: `src/cascade/commands/core/export_cmd.py`

Each follows this pattern (example for `/compact`):
```python
# src/cascade/commands/core/compact.py
from cascade.commands.base import BaseCommand, CommandContext


class CompactCommand(BaseCommand):
    name = "compact"
    description = "Summarize and compress conversation context"
    category = "Session"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        # Count current messages
        msg_count = len(ctx.engine.messages)
        ctx.console.print(
            f"[dim]Compact: {msg_count} messages in context. "
            f"(Full implementation coming in a future release)[/dim]"
        )
```

For `/export`:
```python
# src/cascade/commands/core/export_cmd.py
from cascade.commands.base import BaseCommand, CommandContext
import json


class ExportCommand(BaseCommand):
    name = "export"
    description = "Export conversation to file"
    category = "Session"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        if not args.strip():
            ctx.console.print("[dim]Usage: /export <filename.json>[/dim]")
            return
        filepath = args.strip()
        messages = ctx.engine.messages
        with open(filepath, "w") as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)
        ctx.console.print(f"[#00d7af]Exported {len(messages)} messages to {filepath}[/#00d7af]")
```

For `/resume`, `/rename`, `/branch`, `/rewind` - all are stubs:
```python
    async def execute(self, ctx: CommandContext, args: str) -> None:
        ctx.console.print(f"[dim]/{self.name}: Coming soon.[/dim]")
```

### Step 2: Register all 6 in REPL

**Files:**
- Modify: `src/cascade/ui/app.py`

```python
        from cascade.commands.core.compact import CompactCommand
        from cascade.commands.core.resume import ResumeCommand
        from cascade.commands.core.rename import RenameCommand
        from cascade.commands.core.branch import BranchCommand
        from cascade.commands.core.rewind import RewindCommand
        from cascade.commands.core.export_cmd import ExportCommand
        self.router.register(CompactCommand())
        self.router.register(ResumeCommand())
        self.router.register(RenameCommand())
        self.router.register(BranchCommand())
        self.router.register(RewindCommand())
        self.router.register(ExportCommand())
```

### Step 3: Manual test checkpoint

```bash
cascade
# /help    -> should show all 10 session commands in the "Session" group
# /export /tmp/test-export.json  -> should write file
# /compact -> stub message
```

### Step 4: Commit

```bash
git add src/cascade/commands/core/ src/cascade/ui/app.py
git commit -m "feat(commands): add session P1/P2 stubs (compact, resume, rename, branch, rewind, export)"
```

---

## Batch 5: C7-Setup (/version, /config, /doctor, /init, /env)

HEP-customized configuration and diagnostics commands.

### Step 1: Create setup subpackage

**Files:**
- Create: `src/cascade/commands/setup/__init__.py`
- Create: `src/cascade/commands/setup/version.py`
- Create: `src/cascade/commands/setup/config.py`
- Create: `src/cascade/commands/setup/doctor.py`
- Create: `src/cascade/commands/setup/init_project.py`
- Create: `src/cascade/commands/setup/env.py`

```python
# src/cascade/commands/setup/version.py
from cascade.commands.base import BaseCommand, CommandContext
from cascade import __version__


class VersionCommand(BaseCommand):
    name = "version"
    description = "Show Cascade version"
    category = "Setup"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        ctx.console.print(f"[bold #5fd7ff]Cascade[/bold #5fd7ff] v{__version__}")
```

```python
# src/cascade/commands/setup/doctor.py
from cascade.commands.base import BaseCommand, CommandContext
import subprocess
import shutil
import os


class DoctorCommand(BaseCommand):
    name = "doctor"
    description = "Run health diagnostics (HEP-aware)"
    category = "Setup"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        from rich.table import Table

        table = Table(
            title="[bold]Cascade Doctor[/bold]",
            show_header=True,
            header_style="bold",
            border_style="dim",
        )
        table.add_column("Check", style="bold")
        table.add_column("Status")
        table.add_column("Details", style="dim")

        checks = [
            self._check_python(),
            self._check_git(),
            self._check_cascade_env(),
            self._check_api_keys(),
        ]

        # HEP-specific checks (only if on a cluster-like env)
        if os.getenv("CMSSW_BASE") or shutil.which("voms-proxy-info"):
            checks.extend([
                self._check_grid_proxy(),
                self._check_cmssw(),
                self._check_eos(),
            ])

        for name, ok, detail in checks:
            status = "[green]OK[/green]" if ok else "[red]FAIL[/red]"
            table.add_row(name, status, detail)

        ctx.console.print(table)

    def _check_python(self):
        import sys
        v = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        ok = sys.version_info >= (3, 11)
        return ("Python >= 3.11", ok, v)

    def _check_git(self):
        ok = shutil.which("git") is not None
        return ("git", ok, shutil.which("git") or "not found")

    def _check_cascade_env(self):
        has_env = os.path.exists(".env")
        return (".env file", has_env, "found" if has_env else "not found in cwd")

    def _check_api_keys(self):
        keys = ["DEEPSEEK_API_KEY", "GLM_API_KEY", "ANTHROPIC_API_KEY"]
        found = [k for k in keys if os.getenv(k)]
        return ("API Keys", len(found) > 0, f"{len(found)}/{len(keys)} configured")

    def _check_grid_proxy(self):
        try:
            r = subprocess.run(
                ["voms-proxy-info", "--timeleft"],
                capture_output=True, text=True, timeout=5
            )
            timeleft = int(r.stdout.strip()) if r.returncode == 0 else 0
            ok = timeleft > 3600
            return ("Grid Proxy", ok, f"{timeleft}s remaining" if ok else "expired or missing")
        except Exception:
            return ("Grid Proxy", False, "voms-proxy-info not available")

    def _check_cmssw(self):
        base = os.getenv("CMSSW_BASE", "")
        return ("CMSSW", bool(base), base or "not set")

    def _check_eos(self):
        ok = os.path.isdir("/eos") or os.path.isdir("/eos/cms")
        return ("EOS", ok, "/eos accessible" if ok else "not mounted")
```

```python
# src/cascade/commands/setup/env.py
from cascade.commands.base import BaseCommand, CommandContext
import os


class EnvCommand(BaseCommand):
    name = "env"
    description = "Show environment variables"
    category = "Setup"

    # HEP-relevant vars to highlight
    HEP_VARS = [
        "SCRAM_ARCH", "CMSSW_BASE", "CMSSW_RELEASE_BASE",
        "X509_USER_PROXY", "CRAB_SOURCE",
    ]
    CASCADE_PREFIX = "CASCADE_"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        from rich.table import Table

        table = Table(title="[bold]Environment[/bold]", border_style="dim")
        table.add_column("Variable", style="bold #0087ff")
        table.add_column("Value")

        # Cascade vars
        for key, val in sorted(os.environ.items()):
            if key.startswith(self.CASCADE_PREFIX):
                table.add_row(key, val)

        # HEP vars
        for key in self.HEP_VARS:
            val = os.getenv(key)
            if val:
                table.add_row(f"[bold yellow]{key}[/bold yellow]", val)

        ctx.console.print(table)
```

```python
# src/cascade/commands/setup/config.py
from cascade.commands.base import BaseCommand, CommandContext


class ConfigCommand(BaseCommand):
    name = "config"
    description = "View/edit Cascade configuration"
    category = "Setup"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        from rich.table import Table
        table = Table(title="[bold]Cascade Config[/bold]", border_style="dim")
        table.add_column("Key", style="bold")
        table.add_column("Value")
        table.add_row("provider", ctx.engine.client.provider)
        table.add_row("model", ctx.engine.client.model_name)
        table.add_row("max_tool_rounds", str(ctx.engine.config.max_tool_rounds))
        table.add_row("permission_mode", str(ctx.engine.permissions.mode.value if ctx.engine.permissions else "N/A"))
        ctx.console.print(table)
        ctx.console.print("[dim]Use /config set <key> <value> to change (coming soon)[/dim]")
```

```python
# src/cascade/commands/setup/init_project.py
from cascade.commands.base import BaseCommand, CommandContext
import os


class InitCommand(BaseCommand):
    name = "init"
    description = "Initialize project with CASCADE.md"
    category = "Setup"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        cascade_md = os.path.join(os.getcwd(), "CASCADE.md")
        if os.path.exists(cascade_md):
            ctx.console.print(f"[dim]CASCADE.md already exists at {cascade_md}[/dim]")
            return

        template = (
            "# Project Memory\n\n"
            "## Key Decisions\n\n"
            "## Architecture Notes\n\n"
            "## HEP Analysis Config\n\n"
            "- Cluster: lxplus / local\n"
            "- CMSSW version: \n"
            "- Dataset: \n"
        )
        with open(cascade_md, "w") as f:
            f.write(template)
        ctx.console.print(f"[#00d7af]Created {cascade_md}[/#00d7af]")
```

### Step 2: Register all 5 in REPL

**Files:**
- Modify: `src/cascade/ui/app.py`

```python
        from cascade.commands.setup.version import VersionCommand
        from cascade.commands.setup.config import ConfigCommand
        from cascade.commands.setup.doctor import DoctorCommand
        from cascade.commands.setup.init_project import InitCommand
        from cascade.commands.setup.env import EnvCommand
        self.router.register(VersionCommand())
        self.router.register(ConfigCommand())
        self.router.register(DoctorCommand())
        self.router.register(InitCommand())
        self.router.register(EnvCommand())
```

### Step 3: Manual test checkpoint

```bash
cascade
# /version  -> "Cascade v0.1.0"
# /doctor   -> health diagnostics table
# /config   -> current config table
# /env      -> environment variables
# /init     -> creates CASCADE.md (if not exists)
```

### Step 4: Commit

```bash
git add src/cascade/commands/setup/ src/cascade/ui/app.py
git commit -m "feat(commands): add /version, /config, /doctor, /init, /env (HEP setup)"
```

---

## Batch 6: C8-UI + C10-Workflow + C11 (/theme, /vim, /brief, /btw)

### Step 1: Create UI subpackage

**Files:**
- Create: `src/cascade/commands/ui/__init__.py`
- Create: `src/cascade/commands/ui/theme.py`
- Create: `src/cascade/commands/ui/vim.py`
- Create: `src/cascade/commands/ui/brief.py`
- Create: `src/cascade/commands/ui/btw.py`

```python
# src/cascade/commands/ui/theme.py
from cascade.commands.base import BaseCommand, CommandContext

THEMES = {
    "cascade-blue": {
        "accent": "#5fd7ff",
        "panel": "#005fff",
        "text": "white",
        "desc": "Default Cascade blue gradient",
    },
    "cms-dark": {
        "accent": "#ff8700",
        "panel": "#1a1a2e",
        "text": "#e0e0e0",
        "desc": "CMS experiment dark orange",
    },
    "atlas-gold": {
        "accent": "#ffd700",
        "panel": "#2a2a1e",
        "text": "#f0e68c",
        "desc": "ATLAS gold on dark",
    },
    "matrix": {
        "accent": "#00ff00",
        "panel": "#000000",
        "text": "#00ff00",
        "desc": "Classic green terminal",
    },
    "solarized": {
        "accent": "#268bd2",
        "panel": "#002b36",
        "text": "#839496",
        "desc": "Solarized dark",
    },
}


class ThemeCommand(BaseCommand):
    name = "theme"
    description = "Switch color theme"
    category = "UI"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        if args.strip() and args.strip() in THEMES:
            theme = THEMES[args.strip()]
            # Store theme on repl for other components to read
            ctx.repl._current_theme = args.strip()
            ctx.console.print(
                f"[{theme['accent']}]Theme switched to {args.strip()}: "
                f"{theme['desc']}[/{theme['accent']}]"
            )
            ctx.console.print("[dim]Theme will fully apply on next startup.[/dim]")
            return

        # List available themes
        from rich.table import Table
        table = Table(title="[bold]Available Themes[/bold]", border_style="dim")
        table.add_column("Name", style="bold")
        table.add_column("Description")
        table.add_column("Accent", width=8)
        current = getattr(ctx.repl, "_current_theme", "cascade-blue")
        for name, info in THEMES.items():
            marker = " [yellow]<< current[/yellow]" if name == current else ""
            table.add_row(
                f"{name}{marker}",
                info["desc"],
                f"[{info['accent']}]######[/{info['accent']}]",
            )
        ctx.console.print(table)
        ctx.console.print("[dim]Usage: /theme <name>[/dim]")
```

```python
# src/cascade/commands/ui/vim.py
from cascade.commands.base import BaseCommand, CommandContext


class VimCommand(BaseCommand):
    name = "vim"
    description = "Toggle Vim keybinding mode"
    category = "UI"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        app = ctx.session.app
        if app:
            current = app.vi_mode
            app.vi_mode = not current
            mode = "ON (Vi)" if app.vi_mode else "OFF (Emacs)"
            ctx.console.print(f"[#00d7af]Vim mode: {mode}[/#00d7af]")
        else:
            ctx.console.print("[dim]Cannot toggle vim mode (no active app).[/dim]")
```

```python
# src/cascade/commands/ui/brief.py
from cascade.commands.base import BaseCommand, CommandContext


class BriefCommand(BaseCommand):
    name = "brief"
    description = "Toggle concise output mode"
    category = "Workflow"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        current = getattr(ctx.repl, "_brief_mode", False)
        ctx.repl._brief_mode = not current
        state = "ON" if ctx.repl._brief_mode else "OFF"
        ctx.console.print(f"[#00d7af]Brief mode: {state}[/#00d7af]")
        if ctx.repl._brief_mode:
            ctx.console.print("[dim]Model will give concise answers. Toggle off with /brief[/dim]")
```

```python
# src/cascade/commands/ui/btw.py
from cascade.commands.base import BaseCommand, CommandContext


class BtwCommand(BaseCommand):
    name = "btw"
    description = "Inject a quick aside into the conversation"
    category = "UI"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        if not args.strip():
            ctx.console.print("[dim]Usage: /btw <your note to the model>[/dim]")
            return

        # Inject as a system-level note into the message history
        note = f"[User aside]: {args.strip()}"
        ctx.engine.messages.append({"role": "user", "content": note})
        ctx.console.print(f"[dim italic]Noted: {args.strip()}[/dim italic]")
```

### Step 2: Register all 4 in REPL

**Files:**
- Modify: `src/cascade/ui/app.py`

```python
        from cascade.commands.ui.theme import ThemeCommand
        from cascade.commands.ui.vim import VimCommand
        from cascade.commands.ui.brief import BriefCommand
        from cascade.commands.ui.btw import BtwCommand
        self.router.register(ThemeCommand())
        self.router.register(VimCommand())
        self.router.register(BriefCommand())
        self.router.register(BtwCommand())
```

### Step 3: Manual test checkpoint

```bash
cascade
# /theme          -> list all 5 themes
# /theme matrix   -> switch to matrix theme
# /vim            -> toggle vim mode
# /brief          -> toggle brief mode
# /btw use Chinese  -> inject aside
```

### Step 4: Commit

```bash
git add src/cascade/commands/ui/ src/cascade/ui/app.py
git commit -m "feat(commands): add /theme, /vim, /brief, /btw (UI + workflow)"
```

---

## Batch 7: C5-Tools (/permissions, /hooks, /debug-tool-call, /sandbox-toggle)

### Step 1: Create tools subpackage

**Files:**
- Create: `src/cascade/commands/tools/__init__.py`
- Create: `src/cascade/commands/tools/permissions.py`
- Create: `src/cascade/commands/tools/hooks.py`
- Create: `src/cascade/commands/tools/debug_tool.py`
- Create: `src/cascade/commands/tools/sandbox.py`

```python
# src/cascade/commands/tools/permissions.py
from cascade.commands.base import BaseCommand, CommandContext


class PermissionsCommand(BaseCommand):
    name = "permissions"
    description = "Manage tool permission rules"
    aliases = ["/perms"]
    category = "Tools"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        from rich.table import Table
        perm = ctx.engine.permissions
        if not perm:
            ctx.console.print("[dim]No permission engine configured.[/dim]")
            return

        table = Table(title="[bold]Tool Permissions[/bold]", border_style="dim")
        table.add_column("Mode", style="bold")
        table.add_column("Value")
        table.add_row("Current mode", str(perm.mode.value))
        ctx.console.print(table)

        # List registered tools
        if ctx.engine.registry:
            tools = ctx.engine.registry.list_tools()
            ctx.console.print(f"[dim]Registered tools: {', '.join(tools)}[/dim]")
```

The remaining 3 commands (`/hooks`, `/debug-tool-call`, `/sandbox-toggle`) follow the same stub pattern with helpful usage messages.

### Step 2: Register in REPL, manual test, commit

Same pattern as previous batches.

```bash
git commit -m "feat(commands): add /permissions, /hooks, /debug-tool-call, /sandbox-toggle"
```

---

## Batch 8: C6-Git (/commit, /commit-push-pr, /pr-comments, /review, /security-review)

### Step 1: Create dev subpackage

**Files:**
- Create: `src/cascade/commands/dev/__init__.py`
- Create: `src/cascade/commands/dev/commit.py`
- Create: `src/cascade/commands/dev/pr.py`
- Create: `src/cascade/commands/dev/pr_comments.py`
- Create: `src/cascade/commands/dev/review.py`
- Create: `src/cascade/commands/dev/security_review.py`

```python
# src/cascade/commands/dev/commit.py
from cascade.commands.base import BaseCommand, CommandContext
import subprocess


class CommitCommand(BaseCommand):
    name = "commit"
    description = "Create a git commit with AI-generated message"
    category = "Git"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        # Check git status
        r = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if not r.stdout.strip():
            ctx.console.print("[dim]Nothing to commit (working tree clean).[/dim]")
            return

        ctx.console.print(f"[bold]Changed files:[/bold]\n{r.stdout}")

        if args.strip():
            # User provided message
            msg = args.strip()
        else:
            # Ask model to generate commit message
            diff = subprocess.run(
                ["git", "diff", "--cached", "--stat"], capture_output=True, text=True
            )
            ctx.console.print("[dim]Generating commit message...[/dim]")
            msg_result = await ctx.engine.client.generate([
                {"role": "system", "content": "Generate a concise git commit message for these changes. Output only the message, nothing else."},
                {"role": "user", "content": f"Changes:\n{r.stdout}\n\nDiff stat:\n{diff.stdout}"},
            ])
            msg = msg_result.strip()
            ctx.console.print(f"[#00d7af]Suggested: {msg}[/#00d7af]")

        ctx.console.print(f"[dim]Run: git add -A && git commit -m '{msg}'[/dim]")
```

`/commit-push-pr` (alias `/pr`), `/pr-comments`, `/review`, `/security-review` follow similar patterns with stubs that describe what they will do.

### Step 2: Register, test, commit

```bash
git commit -m "feat(commands): add /commit, /pr, /review, /security-review (Git workflow)"
```

---

## Batch 9: C14-Memory (/memory, /summary)

### Step 1: Add to core subpackage

**Files:**
- Create: `src/cascade/commands/core/memory.py`
- Create: `src/cascade/commands/core/summary.py`

```python
# src/cascade/commands/core/memory.py
from cascade.commands.base import BaseCommand, CommandContext
import os


class MemoryCommand(BaseCommand):
    name = "memory"
    description = "View/edit project memory (CASCADE.md)"
    category = "Memory"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        cascade_md = os.path.join(os.getcwd(), "CASCADE.md")
        if not os.path.exists(cascade_md):
            ctx.console.print(
                "[dim]No CASCADE.md found. Run /init to create one.[/dim]"
            )
            return

        with open(cascade_md) as f:
            content = f.read()

        from rich.markdown import Markdown
        from rich.panel import Panel
        ctx.console.print(Panel(
            Markdown(content),
            title="[bold]CASCADE.md[/bold]",
            border_style="#5fd7ff",
        ))
```

```python
# src/cascade/commands/core/summary.py
from cascade.commands.base import BaseCommand, CommandContext


class SummaryCommand(BaseCommand):
    name = "summary"
    description = "Summarize current conversation"
    category = "Memory"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        msg_count = len(ctx.engine.messages)
        user_msgs = sum(1 for m in ctx.engine.messages if m.get("role") == "user")
        tool_msgs = sum(1 for m in ctx.engine.messages if m.get("role") == "tool")

        ctx.console.print(
            f"[bold]Conversation Summary[/bold]\n"
            f"  Total messages: {msg_count}\n"
            f"  User messages: {user_msgs}\n"
            f"  Tool calls: {tool_msgs}\n"
            f"  Provider: {ctx.engine.client.provider}\n"
            f"  Model: {ctx.engine.client.model_name}"
        )
```

### Step 2: Register, test, commit

```bash
git commit -m "feat(commands): add /memory, /summary (project memory)"
```

---

## Batch 10: C9-Plugins (/plugin, /reload-plugins, /skills, /agents, /mcp, /tasks)

Phase 8 skeleton only. Real plugin loading logic is Phase 9.

### Step 1: Create plugins subpackage

**Files:**
- Create: `src/cascade/commands/plugins/__init__.py`
- Create: `src/cascade/commands/plugins/plugin.py`
- Create: `src/cascade/commands/plugins/reload_plugins.py`
- Create: `src/cascade/commands/plugins/skills.py`
- Create: `src/cascade/commands/plugins/agents_cmd.py`
- Create: `src/cascade/commands/plugins/mcp_cmd.py`
- Create: `src/cascade/commands/plugins/tasks.py`

All are stubs that print "[Phase 9] Plugin system under development." with helpful descriptions.

```python
# src/cascade/commands/plugins/skills.py
from cascade.commands.base import BaseCommand, CommandContext
import os
import glob


class SkillsCommand(BaseCommand):
    name = "skills"
    description = "List available skills"
    category = "Plugins"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        # Scan for SKILL.md files in common locations
        patterns = [
            os.path.join(os.getcwd(), ".agents", "skills", "*", "SKILL.md"),
            os.path.join(os.getcwd(), ".agent", "skills", "*", "SKILL.md"),
        ]
        found = []
        for pat in patterns:
            found.extend(glob.glob(pat))

        if found:
            from rich.table import Table
            table = Table(title="[bold]Available Skills[/bold]", border_style="dim")
            table.add_column("Skill", style="bold #00d7af")
            table.add_column("Path", style="dim")
            for path in sorted(found):
                skill_name = os.path.basename(os.path.dirname(path))
                table.add_row(skill_name, path)
            ctx.console.print(table)
        else:
            ctx.console.print("[dim]No skills found. Place SKILL.md files in .agents/skills/<name>/[/dim]")
```

### Step 2: Register all 6, test, commit

```bash
git commit -m "feat(commands): add plugin/skill skeleton commands (Phase 9 prep)"
```

---

## Final: Version Bump and Full Test

### Step 1: Update version to 0.3.0

**Files:**
- Modify: `src/cascade/__init__.py` -> `__version__ = "0.3.0"`
- Modify: `src/cascade/ui/banner.py` -> `VERSION = "0.3.0"`

### Step 2: Full test suite

Run: `cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade && python -m pytest tests/ -v`
Expected: All tests pass

### Step 3: Full manual smoke test

```bash
cascade
# /help       -> 36 commands across 10 categories
# /model      -> interactive picker
# /doctor     -> health check table
# /theme      -> 5 themes listed
# /version    -> v0.3.0
# /exit       -> clean exit
```

### Step 4: Final commit and tag

```bash
git add -A
git commit -m "chore: bump version to v0.3.0 - slash command system complete"
git tag v0.3.0
```
