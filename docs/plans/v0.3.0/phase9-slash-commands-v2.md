# Phase 9: Slash Commands v2 — Expand Command Set

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expand from 4 commands to 37 commands across 10 categories. All commands output via `ctx.output()` / `ctx.output_rich()` (Textual-native).

**Pre-requisite:** Phase 8 complete (BaseCommand, CommandRouter, CascadeApp, 4 core commands).

**Architecture reminder:**
- Commands use `ctx.output(text)` for plain text, `ctx.output_rich(markup)` for Rich markup
- No `ctx.console.print()` — that was the old REPL, it no longer exists
- Registration happens in `CascadeApp.__init__()` in `textual_app.py`
- All commands are `async def execute(self, ctx: CommandContext, args: str)`

---

## 📊 Progress Status

| Batch | Status | Commands | Count |
|-------|--------|----------|-------|
| **1: Core P1/P2** | ⬜ | `/compact`, `/resume`, `/rename`, `/branch`, `/rewind`, `/export` | 6 |
| **2: Setup** | ⬜ | `/version`, `/config`, `/doctor`, `/init`, `/env` | 5 |
| **3: UI** | ⬜ | `/theme`, `/brief`, `/btw` | 3 |
| **4: Tools** | ⬜ | `/permissions`, `/hooks`, `/debug-tool-call`, `/sandbox-toggle` | 4 |
| **4.5: Auto Mode** | ⬜ | `/auto` | 1 |
| **5: Git** | ⬜ | `/commit`, `/commit-push-pr`, `/pr-comments`, `/review`, `/security-review` | 5 |
| **6: Memory** | ⬜ | `/memory`, `/summary` | 2 |
| **7: Plugins** | ⬜ | `/plugin`, `/reload-plugins`, `/skills`, `/agents`, `/mcp`, `/tasks` | 6 |
| **Final** | ⬜ | Version bump 0.3.0, full test | — |

**Total: 33 new commands (37 total with Phase 8's 4)**

> **Note:** `/vim` from the original plan is **dropped**. It relied on prompt_toolkit's `vi_mode` which doesn't exist in Textual. May revisit in a future Textual keybinding batch.

---

## Batch 1: Core P1/P2 — Session Management (6 commands)

### Step 1: Create stub commands

**Files:**
- Create: `src/cascade/commands/core/compact.py`
- Create: `src/cascade/commands/core/resume.py`
- Create: `src/cascade/commands/core/rename.py`
- Create: `src/cascade/commands/core/branch.py`
- Create: `src/cascade/commands/core/rewind.py`
- Create: `src/cascade/commands/core/export_cmd.py`

```python
# src/cascade/commands/core/compact.py
from cascade.commands.base import BaseCommand, CommandContext


class CompactCommand(BaseCommand):
    name = "compact"
    description = "Summarize and compress conversation context"
    category = "Session"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        msg_count = len(ctx.engine.messages)
        await ctx.output_rich(
            f"[dim]Compact: {msg_count} messages in context. "
            f"(Full implementation coming in a future release)[/dim]"
        )
```

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
            await ctx.output_rich("[dim]Usage: /export <filename.json>[/dim]")
            return
        filepath = args.strip()
        messages = ctx.engine.messages
        with open(filepath, "w") as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)
        await ctx.output_rich(
            f"[#00d7af]Exported {len(messages)} messages to {filepath}[/#00d7af]"
        )
```

For `/resume`, `/rename`, `/branch`, `/rewind` — all stubs:
```python
    async def execute(self, ctx: CommandContext, args: str) -> None:
        await ctx.output_rich(f"[dim]/{self.name}: Coming soon.[/dim]")
```

### Step 2: Register in CascadeApp

**File:** `src/cascade/ui/textual_app.py`

Add after existing registrations:
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

### Step 3: Verify

```bash
cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade && source .venv/bin/activate
python -c "from cascade.ui.textual_app import CascadeApp; print('OK')"
```

### Step 4: Manual test

```bash
cascade
# /help     → should show 10 commands with Session group expanded
# /export /tmp/test.json → should write file
# /compact  → "Compact: N messages..."
```

### Step 5: Commit

```bash
git add src/cascade/commands/core/ src/cascade/ui/textual_app.py
git commit -m "feat(commands): add session P1/P2 stubs (compact, resume, rename, branch, rewind, export)"
```

---

## Batch 2: Setup (5 commands)

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


class VersionCommand(BaseCommand):
    name = "version"
    description = "Show Cascade version"
    category = "Setup"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        from cascade.ui.banner import VERSION
        await ctx.output_rich(f"[bold #5fd7ff]Cascade[/bold #5fd7ff] v{VERSION}")
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
        lines = ["[bold]Cascade Doctor[/bold]\n"]

        checks = [
            self._check_python(),
            self._check_git(),
            self._check_cascade_env(),
            self._check_api_keys(),
        ]

        # HEP-specific checks (only on cluster-like env)
        if os.getenv("CMSSW_BASE") or shutil.which("voms-proxy-info"):
            checks.extend([
                self._check_grid_proxy(),
                self._check_cmssw(),
            ])

        for name, ok, detail in checks:
            icon = "[green]✓[/green]" if ok else "[red]✗[/red]"
            lines.append(f"  {icon} {name}: [dim]{detail}[/dim]")

        await ctx.output_rich("\n".join(lines))

    def _check_python(self):
        import sys
        v = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        return ("Python >= 3.11", sys.version_info >= (3, 11), v)

    def _check_git(self):
        ok = shutil.which("git") is not None
        return ("git", ok, shutil.which("git") or "not found")

    def _check_cascade_env(self):
        has_env = os.path.exists(".env")
        return (".env file", has_env, "found" if has_env else "not found in cwd")

    def _check_api_keys(self):
        keys = ["DEEPSEEK_API_KEY", "GLM_API_KEY", "ANTHROPIC_API_KEY",
                "GEMINI_API_KEY", "OPENAI_API_KEY"]
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
```

```python
# src/cascade/commands/setup/config.py
from cascade.commands.base import BaseCommand, CommandContext


class ConfigCommand(BaseCommand):
    name = "config"
    description = "View Cascade configuration"
    category = "Setup"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        lines = [
            "[bold]Cascade Config[/bold]\n",
            f"  Provider: [#0087ff]{ctx.engine.client.provider}[/#0087ff]",
            f"  Model:    [bold]{ctx.engine.client.model_name}[/bold]",
            f"  Tools:    {len(ctx.engine.registry.list_tools()) if ctx.engine.registry else 0} registered",
        ]
        if ctx.engine.permissions:
            lines.append(f"  Perms:    {ctx.engine.permissions.mode.value}")
        await ctx.output_rich("\n".join(lines))
```

```python
# src/cascade/commands/setup/env.py
from cascade.commands.base import BaseCommand, CommandContext
import os


class EnvCommand(BaseCommand):
    name = "env"
    description = "Show environment variables"
    category = "Setup"

    CASCADE_PREFIX = "CASCADE_"
    HEP_VARS = ["SCRAM_ARCH", "CMSSW_BASE", "X509_USER_PROXY"]

    async def execute(self, ctx: CommandContext, args: str) -> None:
        lines = ["[bold]Environment[/bold]\n"]

        # Cascade vars
        for key, val in sorted(os.environ.items()):
            if key.startswith(self.CASCADE_PREFIX):
                lines.append(f"  [#0087ff]{key}[/#0087ff] = {val}")

        # HEP vars (if present)
        for key in self.HEP_VARS:
            val = os.getenv(key)
            if val:
                lines.append(f"  [yellow]{key}[/yellow] = {val}")

        if len(lines) == 1:
            lines.append("  [dim]No CASCADE_* or HEP vars found.[/dim]")

        await ctx.output_rich("\n".join(lines))
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
            await ctx.output_rich(f"[dim]CASCADE.md already exists at {cascade_md}[/dim]")
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
        await ctx.output_rich(f"[#00d7af]Created {cascade_md}[/#00d7af]")
```

### Step 2: Register in CascadeApp

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

### Step 3: Verify + commit

```bash
python -c "from cascade.ui.textual_app import CascadeApp; print('OK')"
git add src/cascade/commands/setup/ src/cascade/ui/textual_app.py
git commit -m "feat(commands): add /version, /config, /doctor, /init, /env (HEP setup)"
```

---

## Batch 3: UI (3 commands)

> `/vim` dropped — no prompt_toolkit vi_mode in Textual.

**Files:**
- Create: `src/cascade/commands/ui/__init__.py`
- Create: `src/cascade/commands/ui/theme.py`
- Create: `src/cascade/commands/ui/brief.py`
- Create: `src/cascade/commands/ui/btw.py`

```python
# src/cascade/commands/ui/theme.py
from cascade.commands.base import BaseCommand, CommandContext

THEMES = {
    "cascade-blue": {"accent": "#5fd7ff", "desc": "Default Cascade blue"},
    "cms-dark": {"accent": "#ff8700", "desc": "CMS experiment dark orange"},
    "atlas-gold": {"accent": "#ffd700", "desc": "ATLAS gold on dark"},
    "matrix": {"accent": "#00ff00", "desc": "Classic green terminal"},
    "solarized": {"accent": "#268bd2", "desc": "Solarized dark"},
}


class ThemeCommand(BaseCommand):
    name = "theme"
    description = "Switch color theme"
    category = "UI"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        if args.strip() and args.strip() in THEMES:
            theme = THEMES[args.strip()]
            await ctx.output_rich(
                f"[{theme['accent']}]Theme: {args.strip()} — "
                f"{theme['desc']}[/{theme['accent']}]\n"
                f"[dim]Full theme switching coming in a future release.[/dim]"
            )
            return

        lines = ["[bold]Available Themes[/bold]\n"]
        for name, info in THEMES.items():
            lines.append(
                f"  [{info['accent']}]■[/{info['accent']}] {name} — [dim]{info['desc']}[/dim]"
            )
        lines.append("\n[dim]Usage: /theme <name>[/dim]")
        await ctx.output_rich("\n".join(lines))
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
        await ctx.output_rich(f"[#00d7af]Brief mode: {state}[/#00d7af]")
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
            await ctx.output_rich("[dim]Usage: /btw <your note to the model>[/dim]")
            return
        note = f"[User aside]: {args.strip()}"
        ctx.engine.messages.append({"role": "user", "content": note})
        await ctx.output_rich(f"[dim italic]Noted: {args.strip()}[/dim italic]")
```

### Register + commit

```bash
git add src/cascade/commands/ui/ src/cascade/ui/textual_app.py
git commit -m "feat(commands): add /theme, /brief, /btw (UI + workflow)"
```

---

## Batch 4: Tools (4 commands)

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
    description = "Show tool permission rules"
    aliases = ["/perms"]
    category = "Tools"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        perm = ctx.engine.permissions
        if not perm:
            await ctx.output_rich("[dim]No permission engine configured.[/dim]")
            return

        lines = [
            "[bold]Tool Permissions[/bold]\n",
            f"  Mode: [bold]{perm.mode.value}[/bold]",
        ]

        if ctx.engine.registry:
            tools = ctx.engine.registry.list_tools()
            lines.append(f"  Tools: [dim]{', '.join(tools)}[/dim]")

        await ctx.output_rich("\n".join(lines))
```

`/hooks`, `/debug-tool-call`, `/sandbox-toggle` — stubs with `await ctx.output_rich("[dim]Coming soon.[/dim]")`.

### Register + commit

```bash
git commit -m "feat(commands): add /permissions, /hooks, /debug-tool-call, /sandbox-toggle"
```

---

## Batch 4.5: Auto Mode (1 command)

```python
# src/cascade/commands/tools/auto.py
from cascade.commands.base import BaseCommand, CommandContext
from cascade.permissions.engine import PermissionMode


class AutoCommand(BaseCommand):
    name = "auto"
    description = "Toggle auto-approve mode for safe tools"
    category = "Tools"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        perm = ctx.engine.permissions
        if not perm:
            await ctx.output_rich("[dim]No permission engine configured.[/dim]")
            return

        if args.strip().lower() == "on":
            perm.mode = PermissionMode.AUTO
        elif args.strip().lower() == "off":
            perm.mode = PermissionMode.DEFAULT
        else:
            # Toggle
            if perm.mode == PermissionMode.AUTO:
                perm.mode = PermissionMode.DEFAULT
            else:
                perm.mode = PermissionMode.AUTO

        mode_display = {
            PermissionMode.DEFAULT: "[bold yellow]Default[/bold yellow] (ask every time)",
            PermissionMode.AUTO: "[bold green]Auto[/bold green] (read-only auto-approved)",
            PermissionMode.BYPASS: "[bold red]Bypass[/bold red] (all auto-approved ⚠️)",
        }
        await ctx.output_rich(
            f"Permission mode: {mode_display.get(perm.mode, str(perm.mode))}"
        )

        # Update TUI footer
        if hasattr(ctx.repl, 'update_footer'):
            ctx.repl.update_footer()
```

### Register + commit

```bash
git commit -m "feat(commands): add /auto to toggle permission mode"
```

---

## Batch 5: Git (5 commands)

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
        r = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if not r.stdout.strip():
            await ctx.output_rich("[dim]Nothing to commit (working tree clean).[/dim]")
            return

        await ctx.output_rich(f"[bold]Changed files:[/bold]\n{r.stdout}")

        if args.strip():
            msg = args.strip()
        else:
            diff = subprocess.run(
                ["git", "diff", "--cached", "--stat"], capture_output=True, text=True
            )
            await ctx.output_rich("[dim]Generating commit message...[/dim]")
            msg_result = await ctx.engine.client.generate([
                {"role": "system", "content": "Generate a concise git commit message. Output only the message."},
                {"role": "user", "content": f"Changes:\n{r.stdout}\n\nDiff stat:\n{diff.stdout}"},
            ])
            msg = msg_result.strip()
            await ctx.output_rich(f"[#00d7af]Suggested: {msg}[/#00d7af]")

        await ctx.output_rich(f"[dim]Run: git add -A && git commit -m '{msg}'[/dim]")
```

`/commit-push-pr` (alias `/pr`), `/pr-comments`, `/review`, `/security-review` — stubs.

### Register + commit

```bash
git commit -m "feat(commands): add /commit, /pr, /review, /security-review (Git workflow)"
```

---

## Batch 6: Memory (2 commands)

```python
# src/cascade/commands/core/memory.py
from cascade.commands.base import BaseCommand, CommandContext
import os


class MemoryCommand(BaseCommand):
    name = "memory"
    description = "View project memory (CASCADE.md)"
    category = "Memory"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        cascade_md = os.path.join(os.getcwd(), "CASCADE.md")
        if not os.path.exists(cascade_md):
            await ctx.output_rich(
                "[dim]No CASCADE.md found. Run /init to create one.[/dim]"
            )
            return

        with open(cascade_md) as f:
            content = f.read()
        await ctx.output(content)
```

```python
# src/cascade/commands/core/summary.py
from cascade.commands.base import BaseCommand, CommandContext


class SummaryCommand(BaseCommand):
    name = "summary"
    description = "Summarize current conversation"
    category = "Memory"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        msgs = ctx.engine.messages
        msg_count = len(msgs)
        user_msgs = sum(1 for m in msgs if m.get("role") == "user")
        tool_msgs = sum(1 for m in msgs if m.get("role") == "tool")

        await ctx.output_rich(
            f"[bold]Conversation Summary[/bold]\n"
            f"  Messages: {msg_count}\n"
            f"  User: {user_msgs}\n"
            f"  Tool calls: {tool_msgs}\n"
            f"  Provider: [#0087ff]{ctx.engine.client.provider}[/#0087ff]\n"
            f"  Model: [bold]{ctx.engine.client.model_name}[/bold]"
        )
```

### Register + commit

```bash
git commit -m "feat(commands): add /memory, /summary (project memory)"
```

---

## Batch 7: Plugins (6 commands)

Phase 9 skeleton only. Real plugin loading is Phase 10+.

**Files:**
- Create: `src/cascade/commands/plugins/__init__.py`
- Create: `src/cascade/commands/plugins/plugin.py`
- Create: `src/cascade/commands/plugins/reload_plugins.py`
- Create: `src/cascade/commands/plugins/skills.py`
- Create: `src/cascade/commands/plugins/agents_cmd.py`
- Create: `src/cascade/commands/plugins/mcp_cmd.py`
- Create: `src/cascade/commands/plugins/tasks.py`

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
        patterns = [
            os.path.join(os.getcwd(), ".agents", "skills", "*", "SKILL.md"),
            os.path.join(os.getcwd(), ".agent", "skills", "*", "SKILL.md"),
        ]
        found = []
        for pat in patterns:
            found.extend(glob.glob(pat))

        if found:
            lines = ["[bold]Available Skills[/bold]\n"]
            for path in sorted(found):
                skill_name = os.path.basename(os.path.dirname(path))
                lines.append(f"  [#00d7af]{skill_name}[/#00d7af] — [dim]{path}[/dim]")
            await ctx.output_rich("\n".join(lines))
        else:
            await ctx.output_rich(
                "[dim]No skills found. Place SKILL.md files in .agents/skills/<name>/[/dim]"
            )
```

Other 5 commands — stubs: `await ctx.output_rich("[dim]Plugin system under development.[/dim]")`.

### Register + commit

```bash
git commit -m "feat(commands): add plugin/skill skeleton commands (Phase 10 prep)"
```

---

## Final: Version Bump + Full Test

### Step 1: Update version to 0.3.0

**Files:**
- Modify: `pyproject.toml` → `version = "0.3.0"`
- Modify: `src/cascade/ui/banner.py` → `VERSION = "0.3.0"`

### Step 2: Full test suite

```bash
cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade && source .venv/bin/activate
python -m pytest tests/ -v
```
Expected: All tests pass

### Step 3: Manual smoke test

```bash
cascade
# /help       → 37 commands across 10 categories
# /model      → inline model palette
# /doctor     → health check
# /version    → v0.3.0
# /auto       → toggle permission mode
# /skills     → list skills
# /exit       → clean exit
```

### Step 4: Final commit + tag

```bash
git add -A
git commit -m "chore: bump version to v0.3.0 — slash command system complete"
git tag v0.3.0
```
