# Phase 9.6: Batch 6 — 规则、上下文与 Token 精确化 (2 commands + 1 infra)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 实现 `/rules` 和 `/context`，含 CASCADE.md 加载基础设施 + Token 计算全面精确化。

**架构:** `BaseCommand` + `CommandContext` + Textual widgets（`OptionList`、`TextArea`）。

**前置条件:** Phase 9.4.5 (Batch 4.5) 完成。

---

## 📊 命令与改动总览

| 项目 | Claude Code 对应 | Cascade 实现 | 备注 |
|------|-----------------|-------------|------|
| `/rules` | `/memory` (memory.tsx, 90行) | ✅ **超越 Claude Code** | OptionList 选择 + TextArea 内置编辑器 + 热加载 |
| `/context` | `context-noninteractive.ts` (326行) | ✅ **API 真实值** | API usage → session 累加器 → 命令显示 |
| Token 数据流 | 内置 token 追踪 | ✅ **单一数据流** | API → StreamResult → TurnResult → QueryEngine → 命令 |

> [!IMPORTANT]
> **重大改动：Token 计算全面精确化**
>
> 原状态：所有 token 计算使用 `字符÷4` 粗估（`utils/tokens.py`），误差 ±30-50%
>
> 新状态：**API 真实值优先，LiteLLM 离线仅作 fallback**
> 1. **主数据源** → API response `usage.prompt_tokens`（100% 精确） → session 级累加
> 2. **fallback** → `litellm.token_counter()` 仅在第一次 API 调用之前使用
> 3. **max context window** → `litellm.get_model_info()` 查询，不再硬编码
>
> 影响范围：`query.py`（累加器）+ `/context` `/status` `/compact`（读取器）

> [!IMPORTANT]
> **命名变更:** Claude Code 的 `/memory` 在 Cascade 中改名为 `/rules`。
> 原因：CASCADE.md 的实际用途是"给 AI 的项目规则"，`/memory` 名称有误导性。

---

## 设计亮点

### `/rules` vs Claude Code `/memory`

| 特性 | Claude Code `/memory` | Cascade `/rules` |
|------|----------------------|-------------------|
| 文件选择 | JSX `MemoryFileSelector` | Textual `OptionList` |
| 编辑方式 | 调用 `$EDITOR`（vim/nano），需退出 TUI | **Textual `TextArea`** 内置编辑器，鼠标操作 |
| 编辑后生效 | ❌ 需要重启 session | ✅ **热加载**，当场生效 |
| 用户门槛 | 需要会用 vim/nano | 鼠标点击 + 键盘输入，零门槛 |

### Token 数据流（单一数据源）

```
API response chunk.usage.prompt_tokens (100% 精确)
  → StreamResult.input_tokens
    → TurnResult.input_tokens
      → QueryEngine.session_input_tokens (session 级累加)
        → /context /status /compact 直接读 engine 上的值

fallback (第一次 API 调用之前):
  litellm.token_counter() → 离线 BPE 估算（带 ~ 前缀，标注 "estimate"）

max context window:
  litellm.get_model_info() → 查不到 fallback 128k
```

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

### Task 2: Token 数据流——从 API 真实值到命令显示

> [!IMPORTANT]
> **核心思路：一条清晰的数据流，不搞两套系统。**
>
> ```
> API response chunk.usage.prompt_tokens (100% 精确)
>   → StreamResult.input_tokens
>     → TurnResult.input_tokens
>       → QueryEngine.session_input_tokens (session 级累加)
>         → /context /status /compact 直接读 engine 上的值
> ```
>
> LiteLLM offline tokenizer (`precise_token_count`) 仅作为 **fallback**：
> 在第一次 API 调用之前（没有 API 数据时）提供估算。

**Files (按数据流顺序):**
1. `src/cascade/services/api_client.py` — StreamResult 添加 token 字段 + stream_options (**已完成**)
2. `src/cascade/engine/query.py` — TurnResult 传递 + **QueryEngine 添加 session 累加器**
3. `src/cascade/ui/textual_app.py` — submit 回调中把 TurnResult tokens 累加到 engine
4. `src/cascade/commands/rules/context.py` — 优先读 engine 真实值，无则 fallback 离线
5. `src/cascade/commands/workflow/status.py` — 同上
6. `src/cascade/commands/core/compact.py` — 同上

#### 2a. `api_client.py` — StreamResult 已有 token 字段 ✅ (已实现)

确认 StreamResult 有 `input_tokens: int = 0` / `output_tokens: int = 0`。
确认 `stream_full()` 有 `stream_options={"include_usage": True}`。
确认从最后 chunk 提取 usage。

#### 2b. `query.py` — **添加 session 级累加器**

这是**关键缺失步骤**。当前 `submit()` 返回 `TurnResult` 后 token 数据就丢了。

```python
class QueryEngine:
    def __init__(self, ...):
        ...
        # Session-level token accumulator (from API response.usage)
        self.session_input_tokens: int = 0
        self.session_output_tokens: int = 0

    async def submit(self, ...) -> TurnResult:
        ...
        # 在 submit() 末尾、return TurnResult 之前，累加到 session 级：
        self.session_input_tokens += total_input_tokens
        self.session_output_tokens += total_output_tokens

        return TurnResult(
            output=...,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            ...
        )
```

**注意：** 每个 `return TurnResult(...)` 之前都要加累加（有 3 处 return）。

#### 2c. `/context` — 优先读 engine 真实值

```python
async def execute(self, ctx: CommandContext, args: str) -> None:
    messages = ctx.engine.messages
    model_name = ctx.engine.client.model_name
    provider = ctx.engine.client.provider

    # 优先用 API 返回的真实 token 数
    api_tokens = ctx.engine.session_input_tokens
    if api_tokens > 0:
        # 有 API 数据——显示真实值
        total_tokens = api_tokens
        source_label = "API usage"
    else:
        # 第一次对话前没有 API 数据——用 LiteLLM 离线估算
        kwargs = get_litellm_kwargs(provider, model_name)
        litellm_model = kwargs["model"]
        breakdown = precise_token_count_by_role(messages, litellm_model)
        total_tokens = sum(breakdown.values())
        source_label = "LiteLLM estimate"

    max_tokens = self._get_max_tokens(...)
    # ... 显示进度条，标注来源 source_label
```

#### 2d. `/status` — 同理

```python
# 优先读 API 真实值
api_tokens = ctx.engine.session_input_tokens
if api_tokens > 0:
    token_display = f"{api_tokens:,}"
else:
    kwargs = get_litellm_kwargs(ctx.engine.client.provider, ctx.engine.client.model_name)
    token_display = f"~{precise_token_count(ctx.engine.messages, kwargs['model']):,}"

f"  [bold]Tokens:[/bold] {token_display}"
```

#### 2e. `/compact` — 同理

```python
api_tokens = ctx.engine.session_input_tokens
if api_tokens > 0:
    est_tokens = api_tokens
else:
    kwargs = get_litellm_kwargs(ctx.engine.client.provider, ctx.engine.client.model_name)
    est_tokens = precise_token_count(ctx.engine.messages, kwargs["model"])
```

#### 2f. 验证脚本

```bash
# 启动 cascade
cascade

# 1. 第一次对话前 /context → 应显示 "LiteLLM estimate" + 离线估算值
/context

# 2. 发一条消息
"hello"

# 3. 再次 /context → 应显示 "API usage" + 真实 prompt_tokens
/context

# 4. /status → Tokens 应显示 API 真实值（无 ~）
/status
```

**Commit:**
```bash
git add src/cascade/engine/query.py src/cascade/commands/rules/context.py \
       src/cascade/commands/workflow/status.py src/cascade/commands/core/compact.py
git commit -m "feat(tokens): session-level token accumulator + commands read API real usage"
```

---

### Task 3: 创建 /rules 命令（OptionList + TextArea）

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

### Task 4: 创建 /context 命令（精确版）

**Files:**
- Create/Modify: `src/cascade/commands/rules/context.py`

```python
# src/cascade/commands/rules/context.py
"""Context window usage visualization.

Reference: claude-code src/commands/context/context-noninteractive.ts (326 lines)
Claude Code impl: collectContextData() → analyzeContextUsage() → Markdown table.
Cascade impl: Uses litellm.token_counter() for precise local tokenization
and litellm.get_model_info() for accurate max context window.
Token counts are precise for OpenAI/Anthropic models, near-precise for
others (tiktoken fallback, much better than char/4).
"""
from cascade.commands.base import BaseCommand, CommandContext
from cascade.utils.tokens import precise_token_count_by_role
from cascade.services.api_config import get_litellm_kwargs


class ContextCommand(BaseCommand):
    name = "context"
    description = "Show context window usage"
    category = "Rules"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        messages = ctx.engine.messages
        model_name = ctx.engine.client.model_name
        provider = ctx.engine.client.provider

        # Get LiteLLM model key for precise counting
        kwargs = get_litellm_kwargs(provider, model_name)
        litellm_model = kwargs["model"]

        # Precise token count by role
        breakdown = precise_token_count_by_role(messages, litellm_model)
        total_tokens = sum(breakdown.values())
        max_tokens = self._get_max_tokens(litellm_model)
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
            "[bold]Context Usage[/bold]  [dim](LiteLLM tokenizer)[/dim]\n",
            f"  Model: [bold]{model_name}[/bold]",
            f"  Tokens: {total_tokens:,} / {max_tokens:,} ({pct:.1f}%)",
            f"  {bar}\n",
            "  [bold]Category Breakdown[/bold]",
            f"    System:    {breakdown['system']:,} tokens",
            f"    User:      {breakdown['user']:,} tokens",
            f"    Assistant: {breakdown['assistant']:,} tokens",
            f"    Tool:      {breakdown['tool']:,} tokens",
            f"\n  Messages: {len(messages)} total",
        ]

        await ctx.output_rich("\n".join(lines))

    def _get_max_tokens(self, litellm_model: str) -> int:
        """Query LiteLLM for exact context window size, fallback to 128k."""
        try:
            from litellm import get_model_info
            info = get_model_info(litellm_model)
            return info.get("max_input_tokens", 128_000)
        except Exception:
            return 128_000
```

---

### Task 5: 注册到 CascadeApp

**File:** `src/cascade/ui/textual_app.py`

```python
        from cascade.commands.rules.rules import RulesCommand
        from cascade.commands.rules.context import ContextCommand
        self.router.register(RulesCommand())
        self.router.register(ContextCommand())
```

---

### Task 6: 验证 + 测试

```bash
cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade && source .venv/bin/activate

# 1. Import 检查
python -c "from cascade.ui.textual_app import CascadeApp; print('OK')"
python -c "from cascade.bootstrap.system_prompt import get_cascade_md_files; print('OK')"
python -c "from cascade.utils.tokens import precise_token_count, precise_token_count_by_role; print('OK')"

# 2. Token 精度验证
python -c "
from cascade.utils.tokens import precise_token_count, rough_token_estimate
msgs = [{'role': 'user', 'content': 'Hello, this is a test message for token counting.'}]
rough = rough_token_estimate(msgs[0]['content'])
precise = precise_token_count(msgs, 'gemini/gemini-3.1-flash-lite-preview')
print(f'Rough (char/4): {rough}, Precise (LiteLLM): {precise}')
"

# 3. 手动测试
cascade
# /context  → 精确 token 数 + 正确 max context window（无 ~ 前缀）
# /status   → Tokens 显示精确数值
# /compact  → tokens 显示精确数值
# /rules    → OptionList 弹出 → 选择 → TextArea 编辑 → Ctrl+S → 热加载
# /model 切到 kimi → /context → max tokens 应为 262,144
# /help     → Rules 分组含 /rules + /context
```

---

## L1~L4 验收标准

| Level | 检查项 | 标准 |
|-------|--------|------|
| L1 | `commands/rules/` 含文件 + `system_prompt.py` 已修改 | `ls` + `git diff` |
| L2 | `precise_token_count` 被 `/context` `/status` `/compact` 三个命令使用 | `grep` 确认 |
| L3 | `/context` 显示精确 token 数（无 ~ 前缀）+ 正确 max context window | 手动验证 |
| L4 | `/rules` OptionList → TextArea → Ctrl+S → 热加载 → AI 遵守新规则 | 对话测试 |

---

## 与 Claude Code 的差异汇总

| 功能 | Claude Code | Cascade | 结果 |
|------|-------------|---------|------|
| 命令名 | `/memory` | `/rules` | ✅ 更直观 |
| 文件选择 | JSX `MemoryFileSelector` | Textual `OptionList` | ✅ 等价 |
| 编辑方式 | `$EDITOR` (vim/nano) | **Textual `TextArea`** (鼠标操作) | ✅ **更好** |
| 编辑后生效 | ❌ 需重启 session | ✅ **热加载** | ✅ **更好** |
| Token 计算 | `analyzeContextUsage` 精确引擎 | `litellm.token_counter()` BPE | ✅ 接近 |
| Max context | 内置模型数据库 | `litellm.get_model_info()` | ✅ 等价 |
| API usage | 内置 token 追踪 | `response.usage` 提取 | ✅ 等价 |
