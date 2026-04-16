# Phase 9.6: Batch 6 — 规则与上下文命令 (2 commands)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 实现 `/rules` 和 `/context` 两个命令，含 CASCADE.md 加载基础设施。

**架构:** `BaseCommand` + `CommandContext` + Textual widgets（`OptionList`、`TextArea`）。

**前置条件:** Phase 9.4.5 (Batch 4.5) 完成。

---

## 📊 命令总览

| 命令 | Claude Code 对应 | Cascade 实现 | 备注 |
|------|-----------------|-------------|------|
| `/rules` | `/memory` (memory.tsx, 90行) | ✅ **超越 Claude Code** | OptionList 选择 + TextArea 内置编辑器 + 热加载 |
| `/context` | `context-noninteractive.ts` (326行) | ⚠️ **STUB** | 缺 `analyzeContextUsage` 引擎，字符÷4 粗估 |

> [!IMPORTANT]
> **命名变更:** Claude Code 的 `/memory` 在 Cascade 中改名为 `/rules`。
> 原因：CASCADE.md 的实际用途是"给 AI 的项目规则"，`/memory` 名称有误导性。
>
> **`/rules` 的前置条件：** `build_system_prompt()` 当前不读 CASCADE.md。
> Task 1 添加 CASCADE.md 加载是必须的前置工作。

---

## 设计亮点：`/rules` vs Claude Code `/memory`

| 特性 | Claude Code `/memory` | Cascade `/rules` |
|------|----------------------|-------------------|
| 文件选择 | JSX `MemoryFileSelector` | Textual `OptionList` |
| 编辑方式 | 调用 `$EDITOR`（vim/nano），需退出 TUI | **Textual `TextArea` 内置编辑器**，鼠标操作 |
| 编辑后生效 | ❌ 需要重启 session | ✅ **热加载**，当场生效 |
| 用户门槛 | 需要会用 vim/nano | 鼠标点击 + 键盘输入，零门槛 |

---

## 实施步骤

### Task 1: CASCADE.md 加载基础设施（前置）

**原因:** `build_system_prompt()` 当前不读任何 CASCADE.md。

**Files:**
- Modify: `src/cascade/bootstrap/system_prompt.py`

```python
# src/cascade/bootstrap/system_prompt.py
import os
from cascade.bootstrap.setup import detect_environment


# CASCADE.md search paths (mirrors Claude Code's CLAUDE.md hierarchy)
# Reference: claude-code src/utils/claudemd.ts getMemoryFiles()
CASCADE_MD_PATHS = [
    ("project", lambda: os.path.join(os.getcwd(), "CASCADE.md")),
    ("project", lambda: os.path.join(os.getcwd(), ".cascade", "CASCADE.md")),
    ("user",    lambda: os.path.expanduser("~/.cascade/CASCADE.md")),
    ("global",  lambda: os.path.expanduser("~/.config/cascade/CASCADE.md")),
]


def get_cascade_md_files() -> list[dict]:
    """Discover all CASCADE.md files at project/user/global levels.

    Reference: claude-code src/utils/claudemd.ts getMemoryFiles()
    Returns list of {"type": str, "path": str, "content": str}.
    """
    found = []
    for level, path_fn in CASCADE_MD_PATHS:
        path = path_fn()
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                if content.strip():
                    found.append({"type": level, "path": path, "content": content})
            except OSError:
                pass
    return found


def build_system_prompt(custom_prompt: str | None = None) -> str:
    env = detect_environment()
    base = f"""You are Cascade, an AI assistant for High-Energy Physics workflows.

Environment:
- Python: {env['python_version']}
- Platform: {env['platform']}
- CWD: {env['cwd']}
- ROOT available: {env['has_root']}
- CMSSW available: {env['has_cmssw']}
- HTCondor available: {env['has_condor']}
- Host: {env['hostname']}

You have access to tools for file operations, shell commands, and HEP-specific tasks.
Always explain what you plan to do before executing tools.
"""
    # Load CASCADE.md rules into system prompt
    cascade_files = get_cascade_md_files()
    for cf in cascade_files:
        base += f"\n\n# Rules ({cf['type']}: {cf['path']})\n{cf['content']}"

    if custom_prompt:
        base += f"\n\nAdditional Instructions:\n{custom_prompt}"
    return base
```

**验证:**
```bash
cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade && source .venv/bin/activate
python -c "from cascade.bootstrap.system_prompt import get_cascade_md_files; print(get_cascade_md_files())"
```

**Commit:**
```bash
git add src/cascade/bootstrap/system_prompt.py
git commit -m "feat(bootstrap): load CASCADE.md rules into system prompt"
```

---

### Task 2: 创建 /rules 命令（OptionList + TextArea）

**Files:**
- Create: `src/cascade/commands/rules/__init__.py`
- Create: `src/cascade/commands/rules/rules.py`
- Create: `src/cascade/commands/rules/editor_screen.py`

#### `__init__.py`

```python
# src/cascade/commands/rules/__init__.py
```

#### `rules.py` — 命令入口

```python
# src/cascade/commands/rules/rules.py
"""Rules file management command.

Reference: claude-code src/commands/memory/memory.tsx (90 lines)
Claude Code impl: type='local-jsx'. Renders JSX MemoryFileSelector
for interactive file picking. Opens selected file in $VISUAL/$EDITOR.
Claude Code name: /memory. Cascade renamed to /rules because
CASCADE.md contains project rules/instructions, not conversation memory.
Cascade impl: Textual OptionList for file selection + TextArea
inline editor (mouse-friendly, no vim/nano required). Hot-reloads
system prompt after save so changes take effect immediately.
"""
import os
from cascade.commands.base import BaseCommand, CommandContext
from cascade.bootstrap.system_prompt import CASCADE_MD_PATHS


class RulesCommand(BaseCommand):
    name = "rules"
    description = "Edit CASCADE.md project rules"
    category = "Rules"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        # Build file list with status
        files = []
        for level, path_fn in CASCADE_MD_PATHS:
            path = path_fn()
            exists = os.path.isfile(path)
            size = os.path.getsize(path) if exists else 0
            files.append({
                "level": level,
                "path": path,
                "exists": exists,
                "size": size,
            })

        # Push the editor screen onto the Textual screen stack
        from cascade.commands.rules.editor_screen import RulesEditorScreen
        await ctx.app.push_screen(RulesEditorScreen(files, ctx.engine))
```

#### `editor_screen.py` — Textual Screen with OptionList + TextArea

```python
# src/cascade/commands/rules/editor_screen.py
"""Textual Screen for rules file selection and inline editing.

Uses OptionList for file selection and TextArea for mouse-friendly editing.
Hot-reloads system prompt on save via engine.set_system_prompt().
"""
import os
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, OptionList, TextArea, Static
from textual.containers import Vertical, Horizontal
from textual.binding import Binding


class RulesEditorScreen(Screen):
    """Two-phase screen: select file → edit in TextArea."""

    BINDINGS = [
        Binding("escape", "cancel", "Back / Cancel"),
        Binding("ctrl+s", "save", "Save & Reload"),
    ]

    CSS = """
    RulesEditorScreen {
        background: $surface;
    }
    #file-list {
        height: auto;
        max-height: 12;
        margin: 1 2;
    }
    #editor-area {
        height: 1fr;
        margin: 0 2 1 2;
    }
    #status-bar {
        height: 1;
        dock: bottom;
        background: $accent;
        color: $text;
        padding: 0 2;
    }
    """

    def __init__(self, files: list[dict], engine) -> None:
        super().__init__()
        self.files = files
        self.engine = engine
        self.current_path: str | None = None
        self.editing = False

    def compose(self) -> ComposeResult:
        yield Static("[bold]CASCADE.md Rules[/bold]  Select a file to edit:\n", id="title")
        option_list = OptionList(id="file-list")
        for f in self.files:
            status = f"● {f['size']} bytes" if f["exists"] else "○ (create new)"
            option_list.add_option(
                f"[{f['level'].title()}]  {f['path']}  {status}"
            )
        yield option_list
        yield TextArea(id="editor-area", language="markdown", show_line_numbers=True)
        yield Static("↑↓ Select · Enter Edit · Ctrl+S Save · Esc Cancel", id="status-bar")

    def on_mount(self) -> None:
        # Hide editor until a file is selected
        self.query_one("#editor-area", TextArea).display = False

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """User selected a file — load it into TextArea."""
        file_info = self.files[event.option_index]
        self.current_path = file_info["path"]

        # Read or create content
        if file_info["exists"]:
            with open(self.current_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        else:
            # Create parent dirs + default content
            os.makedirs(os.path.dirname(self.current_path), exist_ok=True)
            content = "# CASCADE Rules\n\n<!-- Add project-specific rules here -->\n"

        # Show editor
        editor = self.query_one("#editor-area", TextArea)
        editor.load_text(content)
        editor.display = True
        editor.focus()
        self.editing = True

        # Hide file list
        self.query_one("#file-list", OptionList).display = False
        self.query_one("#title", Static).update(
            f"[bold]Editing:[/bold] {self.current_path}\n"
        )
        self.query_one("#status-bar", Static).update(
            "Ctrl+S Save & Reload · Esc Cancel"
        )

    def action_save(self) -> None:
        """Save file and hot-reload system prompt."""
        if not self.current_path or not self.editing:
            return

        editor = self.query_one("#editor-area", TextArea)
        content = editor.text

        # Write to disk
        os.makedirs(os.path.dirname(self.current_path), exist_ok=True)
        with open(self.current_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Hot-reload system prompt
        from cascade.bootstrap.system_prompt import build_system_prompt
        self.engine.set_system_prompt(build_system_prompt())

        # Return to chat
        self.app.pop_screen()
        self.app.post_message_to_chat(
            f"[#00d7af]✓ Saved & reloaded:[/#00d7af] {self.current_path}"
        )

    def action_cancel(self) -> None:
        """Cancel editing / go back."""
        if self.editing:
            # Back to file list
            self.editing = False
            self.current_path = None
            self.query_one("#editor-area", TextArea).display = False
            self.query_one("#file-list", OptionList).display = True
            self.query_one("#title", Static).update(
                "[bold]CASCADE.md Rules[/bold]  Select a file to edit:\n"
            )
            self.query_one("#status-bar", Static).update(
                "↑↓ Select · Enter Edit · Ctrl+S Save · Esc Cancel"
            )
        else:
            # Exit screen entirely
            self.app.pop_screen()
```

**Commit:**
```bash
git add src/cascade/commands/rules/
git commit -m "feat(commands): add /rules with OptionList + TextArea inline editor"
```

---

### Task 3: 创建 /context 命令（STUB）

> [!WARNING]
> **STUB 实现。** 使用字符÷4 粗估 token 数。完整版需要 `analyzeContextUsage` 引擎
> （含 microcompact、MCP tools、Skills/Agents token 统计），计划在 v0.4.0+ 实现。

**Files:**
- Create: `src/cascade/commands/rules/context.py`

```python
# src/cascade/commands/rules/context.py
"""Context window usage visualization.

Reference: claude-code src/commands/context/context-noninteractive.ts (326 lines)
Claude Code impl: collectContextData() → analyzeContextUsage() → Markdown table.
Precise token counting via microcompactMessages + model tokenizer.
Shows categories: System prompt, Tools, Conversation, Memory, MCP, Skills, Agents.
Cascade impl: STUB. Uses rough char/4 estimation. Missing:
- analyzeContextUsage engine (precise tokenization)
- microcompactMessages (context compression stats)
- MCP tools / Skills / Agents token breakdown
These will be implemented when the full token tracking infrastructure
is built (planned in v0.4.0 Phase 0 Task 8 / long-term plan Phase 2+5).
"""
from cascade.commands.base import BaseCommand, CommandContext


class ContextCommand(BaseCommand):
    name = "context"
    description = "Show context window usage (stub: rough estimates)"
    category = "Rules"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        messages = ctx.engine.messages
        model_name = ctx.engine.client.model_name

        # Categorize message chars (rough estimation)
        user_chars = sum(
            len(str(m.get("content", "")))
            for m in messages if m.get("role") == "user"
        )
        assistant_chars = sum(
            len(str(m.get("content", "")))
            for m in messages if m.get("role") == "assistant"
        )
        system_chars = sum(
            len(str(m.get("content", "")))
            for m in messages if m.get("role") == "system"
        )
        tool_chars = sum(
            len(str(m.get("content", "")))
            for m in messages if m.get("role") == "tool"
        )

        total_chars = user_chars + assistant_chars + system_chars + tool_chars
        total_tokens = total_chars // 4
        max_tokens = self._estimate_max_tokens(model_name)
        pct = min(100.0, (total_tokens / max_tokens * 100)) if max_tokens > 0 else 0

        # Progress bar
        bar_width = 40
        filled = int(bar_width * pct / 100)
        bar_color = "green" if pct < 60 else "yellow" if pct < 85 else "red"
        bar = (
            f"[{bar_color}]{'█' * filled}[/{bar_color}]"
            f"[dim]{'░' * (bar_width - filled)}[/dim]"
        )

        lines = [
            "[bold]Context Usage[/bold]  [dim](stub: rough estimates)[/dim]\n",
            f"  Model: [bold]{model_name}[/bold]",
            f"  Tokens: ~{total_tokens:,} / {max_tokens:,} ({pct:.1f}%)",
            f"  {bar}\n",
            "  [bold]Category Breakdown[/bold]",
            f"    System:    ~{system_chars // 4:,} tokens",
            f"    User:      ~{user_chars // 4:,} tokens",
            f"    Assistant: ~{assistant_chars // 4:,} tokens",
            f"    Tool:      ~{tool_chars // 4:,} tokens",
            f"\n  Messages: {len(messages)} total",
        ]

        await ctx.output_rich("\n".join(lines))

    def _estimate_max_tokens(self, model_name: str) -> int:
        """Rough max context window by model family."""
        name = model_name.lower()
        if "claude" in name:
            return 200_000
        elif "gpt-4o" in name:
            return 128_000
        elif "gpt-4" in name:
            return 128_000
        elif "gemini" in name:
            return 1_000_000
        elif "deepseek" in name:
            return 64_000
        else:
            return 128_000
```

---

### Task 4: 注册到 CascadeApp

**File:** `src/cascade/ui/textual_app.py`

```python
        from cascade.commands.rules.rules import RulesCommand
        from cascade.commands.rules.context import ContextCommand
        self.router.register(RulesCommand())
        self.router.register(ContextCommand())
```

---

### Task 5: 验证 + 手动测试

```bash
cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade && source .venv/bin/activate
python -c "from cascade.ui.textual_app import CascadeApp; print('OK')"
```

```bash
cascade
# /rules    → OptionList 弹出，显示 4 个 CASCADE.md 路径
#           → 选一个 Enter → TextArea 编辑器打开
#           → 鼠标点击编辑，Ctrl+S 保存 → "✓ Saved & reloaded"
#           → AI 立即遵守新规则
# /context  → 显示 token 用量 + 进度条 + "(stub: rough estimates)"
# /help     → Rules 分组含 2 个命令
```

---

## L1~L4 验收标准

| Level | 检查项 | 标准 |
|-------|--------|------|
| L1 | `commands/rules/` 含 4 个 .py 文件 + `system_prompt.py` 已修改 | `ls` + `git diff` |
| L2 | `get_cascade_md_files()` 被 `build_system_prompt()` 调用 | `grep` 确认 |
| L3 | `/rules` 弹出 OptionList → 选择后 TextArea 打开 → Ctrl+S 保存 + 热加载 | 手动验证 |
| L4 | 编辑 CASCADE.md 后 AI 立即遵守新规则 | 对话测试 |

---

## 与 Claude Code 的差异汇总

| 功能 | Claude Code | Cascade | 结果 |
|------|-------------|---------|------|
| 命令名 | `/memory` | `/rules` | ✅ 更直观 |
| 文件选择 | JSX `MemoryFileSelector` | Textual `OptionList` | ✅ 等价 |
| 编辑方式 | `$EDITOR` (vim/nano) | **Textual `TextArea`** (鼠标操作) | ✅ **更好** |
| 编辑后生效 | ❌ 需重启 session | ✅ **热加载** | ✅ **更好** |
| `/context` | 326行精确 token 分析 | 粗估 stub | ⚠️ 待完善 |
