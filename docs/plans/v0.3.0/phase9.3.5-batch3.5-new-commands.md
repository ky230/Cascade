# Phase 9.3.5: Batch 3.5 — 新增核心工作流命令 (2 commands)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 实现 `/copy`, `/status` 两个 Review Report 建议新增的 P0/P1 命令。

> [!WARNING]
> **`/diff` 已移除。** Cascade 有 BashTool，用户可以直接让 AI 执行 `git diff`，
> 结果会进入 `engine.messages` 供 AI 分析。`/diff` 命令反而更弱——输出只给用户看，
> AI 看不到。属于被 BashTool 完全替代的冗余命令。

**架构:** `BaseCommand` + `CommandContext`，新建 `commands/workflow/` 子包。

**前置条件:** Phase 9.3 (Batch 3) 完成。

**来源:** [Phase9-Slash-Commands-v2-Implementation-Review-Report.md](file:///Users/ky230/Desktop/Private/Phase9-Slash-Commands-v2-Implementation-Review-Report.md) — "短期（并入 Phase 9）" 建议。

---

## 📊 命令总览

| 命令 | Claude Code 参考源码 | Cascade 实现级别 | 优先级 |
|------|---------------------|-----------------|--------|
| `/copy` | `src/commands/copy/` — `index.ts` (16行) + `copy.tsx` (371行) | ✅ 简化版（无 code block picker） | P0 |
| ~~`/diff`~~ | ~~`src/commands/diff/`~~ | ❌ **已移除** | 被 BashTool + `git diff` 替代 |
| `/status` | `src/commands/status/` — `index.ts` (13行，`immediate: true`) + `status.tsx` (8行，加载 `Settings/Status` Tab) | ✅ 完整实现（整合原 `/summary` 功能） | P1 |

> [!IMPORTANT]
> `/status` 将原计划中的 `/summary` 命令升级合并。`/summary` 不再作为独立命令，其功能成为 `/status` 的子集。

---

## Claude Code 源码参考详情

### `/copy` 参考分析

**源码:** [copy/index.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/copy/index.ts) — 16行
- `type: 'local-jsx'`
- `description: "Copy Claude's last response to clipboard (or /copy N for the Nth-latest)"`

**源码:** [copy/copy.tsx](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/copy/copy.tsx) — 371行
- **核心功能:**
  - `collectRecentAssistantTexts(messages)` — 从消息列表中按时间倒序提取助手文本（最多 20 条）
  - `extractCodeBlocks(markdown)` — 用 `marked.lexer()` 解析 Markdown 提取代码块
  - `CopyPicker` JSX 组件 — 交互式选择器（Full response / 单个代码块 / Always copy full）
  - `setClipboard(text)` — OSC 52 终端剪贴板协议
  - `writeToFile(text, filename)` — 回退：写入 `/tmp/claude/response.md`
  - `fileExtension(lang)` — 根据代码块语言确定文件扩展名（含 path traversal 防护）
  - `/copy N` 参数 — 向前回溯 N 条助手消息
- **依赖:** `marked`、`setClipboard (OSC 52)`、`getGlobalConfig`、`saveGlobalConfig`、`logEvent`
- **配置:** `copyFullResponse` 全局配置项（跳过 picker）

**Cascade 适配:**
- 无 `marked` 库 → 不做代码块提取，只复制完整回复
- 无 JSX CopyPicker → 直接复制到剪贴板
- 剪贴板：`subprocess.run(['pbcopy'])` (macOS) / `xclip` (Linux)
- 保留 `/copy N` 参数和 `/tmp/cascade/response.md` 文件回退
- 不需要 OSC 52（Cascade 通过 subprocess 处理剪贴板）

### `/diff` 参考分析

**源码:** [diff/index.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/diff/index.ts) — 9行
- `type: 'local-jsx'`
- `description: 'View uncommitted changes and per-turn diffs'`

**源码:** [diff/diff.tsx](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/diff/diff.tsx) — 9行（入口）
- 仅加载 `<DiffDialog messages={context.messages} onDone={onDone} />`
- 实际逻辑在 `components/diff/DiffDialog.js`（未直接在 commands 目录中）
- DiffDialog 功能：显示未提交的 git 变更 + 按 turn 分组的文件修改

**Cascade 适配:**
- 无 `DiffDialog` JSX 组件 → 直接运行 `git diff` + `git diff --cached`
- 输出带语法高亮的 diff 文本（Rich markup 着色 +/- 行）
- 支持 `--staged` 参数查看暂存区

### `/status` 参考分析

**源码:** [status/index.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/status/index.ts) — 13行
- `type: 'local-jsx'`，**`immediate: true`**
- `description: 'Show Claude Code status including version, model, account, API connectivity, and tool statuses'`

**源码:** [status/status.tsx](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/status/status.tsx) — 8行（入口）
- 渲染 `<Settings onClose={onDone} context={context} defaultTab="Status" />`
- Status Tab 内容（来自 Settings 组件）：版本号、当前模型、API 连接状态、account 信息、tool 状态
- 与 `/config` 和 `/stats` 共用同一个 `Settings` 组件的不同 Tab

**另见 `/stats`:**
- [stats/index.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/stats/index.ts) — 11行
- [stats/stats.tsx](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/stats/stats.tsx) — 7行
- 渲染 `<Stats onClose={onDone} />`（使用统计组件）
- Claude Code 将 status 和 stats 分成两个命令

**Cascade 适配:**
- 将 Claude Code 的 `/status` + `/stats` + 原计划 `/summary` 合并为一个 `/status` 命令
- 输出：版本、Provider、Model、消息数量、预估 token 数、工具数、会话时长
- 无 Settings 组件 → Rich markup 文本面板

---

## 实施步骤

### Task 1: 创建 workflow 命令子包

**文件:**
- 创建: `src/cascade/commands/workflow/__init__.py`
- 创建: `src/cascade/commands/workflow/copy.py`
- 创建: `src/cascade/commands/workflow/status.py`

#### `/copy`

```python
# src/cascade/commands/workflow/copy.py
from cascade.commands.base import BaseCommand, CommandContext
import subprocess
import platform
import os
from datetime import datetime


class CopyCommand(BaseCommand):
    """Copy AI response to clipboard.

    Reference: claude-code src/commands/copy/copy.tsx (371 lines)
    Claude Code impl: collectRecentAssistantTexts() extracts up to 20
    assistant messages newest-first. extractCodeBlocks() uses marked.lexer()
    to parse Markdown code blocks. CopyPicker JSX shows interactive selector
    (Full response / individual code blocks / "Always copy full").
    setClipboard() uses OSC 52 terminal protocol. writeToFile() writes
    fallback to /tmp/claude/response.md. Supports /copy N to reach back.
    Cascade impl: simplified — copies full response text via subprocess
    (pbcopy on macOS, xclip on Linux). No code block picker, no OSC 52.
    Retains /copy N parameter and /tmp/cascade/ file fallback.
    """
    name = "copy"
    description = "Copy last AI response to clipboard"
    category = "Workflow"

    COPY_DIR = os.path.join("/tmp", "cascade")

    async def execute(self, ctx: CommandContext, args: str) -> None:
        # Collect assistant messages (ref: collectRecentAssistantTexts)
        assistant_msgs = [
            m for m in ctx.engine.messages
            if m.get("role") == "assistant"
        ]
        if not assistant_msgs:
            await ctx.output_rich("[dim]No assistant message to copy.[/dim]")
            return

        # /copy N — reach back N messages (ref: copy.tsx L341-L355)
        age = 0
        if args.strip():
            try:
                n = int(args.strip())
                if n < 1:
                    raise ValueError
                if n > len(assistant_msgs):
                    await ctx.output_rich(
                        f"[dim]Only {len(assistant_msgs)} assistant "
                        f"messages available.[/dim]"
                    )
                    return
                age = n - 1
            except ValueError:
                await ctx.output_rich(
                    "[dim]Usage: /copy [N] where N is 1 (latest), 2, 3, …[/dim]"
                )
                return

        # Get text from the target message
        msg = assistant_msgs[-(age + 1)]
        text = str(msg.get("content", ""))

        # Copy to clipboard (ref: setClipboard → OSC 52 in Claude Code)
        copied = self._copy_to_clipboard(text)

        # File fallback (ref: writeToFile → /tmp/claude/response.md)
        file_path = self._write_fallback(text)

        char_count = len(text)
        line_count = text.count("\n") + 1

        lines = []
        if copied:
            lines.append(
                f"[#00d7af]Copied to clipboard "
                f"({char_count} chars, {line_count} lines)[/#00d7af]"
            )
        if file_path:
            lines.append(f"[dim]Also written to {file_path}[/dim]")
        elif not copied:
            lines.append(
                "[red]Failed to copy — clipboard not available, "
                "no fallback file written.[/red]"
            )
        await ctx.output_rich("\n".join(lines))

    def _copy_to_clipboard(self, text: str) -> bool:
        """Copy text to system clipboard via subprocess."""
        try:
            if platform.system() == "Darwin":
                p = subprocess.run(
                    ["pbcopy"], input=text.encode(), timeout=5
                )
                return p.returncode == 0
            else:  # Linux
                p = subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input=text.encode(), timeout=5
                )
                return p.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _write_fallback(self, text: str) -> str | None:
        """Write to /tmp/cascade/response.md as fallback."""
        try:
            os.makedirs(self.COPY_DIR, exist_ok=True)
            path = os.path.join(self.COPY_DIR, "response.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            return path
        except OSError:
            return None
```

#### `/diff`

```python
# src/cascade/commands/workflow/diff.py
from cascade.commands.base import BaseCommand, CommandContext
import subprocess


class DiffCommand(BaseCommand):
    """View uncommitted git changes.

    Reference: claude-code src/commands/diff/diff.tsx (9 lines, entry)
    Claude Code impl: lazy-loads <DiffDialog messages={context.messages}
    onDone={onDone} />. The DiffDialog component (in components/diff/)
    shows uncommitted changes + per-turn file diffs in a scrollable JSX
    panel. description: 'View uncommitted changes and per-turn diffs'.
    Cascade impl: runs git diff + git diff --cached via subprocess.
    Outputs colorized diff text using Rich markup (green for +, red for -).
    Supports --staged argument to show only staged changes.
    """
    name = "diff"
    description = "View uncommitted git changes"
    category = "Workflow"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        arg = args.strip().lower()

        if arg == "--staged" or arg == "--cached":
            cmd = ["git", "diff", "--cached"]
            label = "Staged changes"
        elif arg:
            # Arbitrary git diff args passthrough
            cmd = ["git", "diff"] + arg.split()
            label = f"git diff {arg}"
        else:
            cmd = ["git", "diff"]
            label = "Unstaged changes"

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15
            )
        except FileNotFoundError:
            await ctx.output_rich("[red]git not found in PATH.[/red]")
            return
        except subprocess.TimeoutExpired:
            await ctx.output_rich("[red]git diff timed out.[/red]")
            return

        if result.returncode != 0:
            await ctx.output_rich(
                f"[red]git diff failed: {result.stderr.strip()}[/red]"
            )
            return

        diff_text = result.stdout.strip()
        if not diff_text:
            await ctx.output_rich(f"[dim]{label}: no changes.[/dim]")
            return

        # Colorize diff output (ref: DiffDialog renders colored diffs)
        colorized = self._colorize_diff(diff_text)
        await ctx.output_rich(
            f"[bold]{label}[/bold]\n\n{colorized}"
        )

    def _colorize_diff(self, diff: str) -> str:
        """Apply Rich markup to diff lines."""
        lines = []
        for line in diff.split("\n"):
            if line.startswith("+++") or line.startswith("---"):
                lines.append(f"[bold]{line}[/bold]")
            elif line.startswith("+"):
                lines.append(f"[green]{line}[/green]")
            elif line.startswith("-"):
                lines.append(f"[red]{line}[/red]")
            elif line.startswith("@@"):
                lines.append(f"[cyan]{line}[/cyan]")
            else:
                lines.append(line)
        return "\n".join(lines)
```

#### `/status` (合并 `/summary` + `/stats`)

```python
# src/cascade/commands/workflow/status.py
from cascade.commands.base import BaseCommand, CommandContext
import time


class StatusCommand(BaseCommand):
    """Show session status, model info, and usage stats.

    Reference: claude-code src/commands/status/status.tsx (8 lines)
    Claude Code impl: renders <Settings onClose={onDone} context={context}
    defaultTab="Status" />. The Status tab in the Settings component shows:
    version, model, account, API connectivity, tool statuses.
    immediate: true (executes without streaming check).
    Also see: src/commands/stats/stats.tsx — renders <Stats onClose={onDone} />
    which shows usage statistics (separate command in Claude Code).
    Cascade impl: merges Claude Code's /status + /stats + original /summary
    into a single comprehensive status dashboard. Outputs Rich text panel
    with session info, model details, token estimates, and tool counts.
    """
    name = "status"
    description = "Show session status and usage stats"
    aliases = ["/summary", "/stats"]
    category = "Workflow"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        from cascade.ui.banner import VERSION

        # Session stats
        msg_count = len(ctx.engine.messages)
        user_msgs = sum(
            1 for m in ctx.engine.messages if m.get("role") == "user"
        )
        assistant_msgs = sum(
            1 for m in ctx.engine.messages if m.get("role") == "assistant"
        )

        # Token estimate (rough: 4 chars ≈ 1 token)
        total_chars = sum(
            len(str(m.get("content", "")))
            for m in ctx.engine.messages
        )
        est_tokens = total_chars // 4

        # Session duration
        start_time = getattr(ctx.repl, "_session_start", None)
        if start_time:
            elapsed = int(time.time() - start_time)
            minutes, seconds = divmod(elapsed, 60)
            duration = f"{minutes}m {seconds}s"
        else:
            duration = "unknown"

        # Tool count
        tool_count = 0
        if ctx.engine.registry:
            tool_count = len(ctx.engine.registry.list_tools())

        lines = [
            "[bold]Cascade Status[/bold]\n",
            f"  [bold]Version:[/bold]   v{VERSION}",
            f"  [bold]Provider:[/bold]  [#0087ff]{ctx.engine.client.provider}[/#0087ff]",
            f"  [bold]Model:[/bold]     [bold]{ctx.engine.client.model_name}[/bold]",
            "",
            f"  [bold]Session:[/bold]   {duration}",
            f"  [bold]Messages:[/bold]  {msg_count} total  "
            f"({user_msgs} user / {assistant_msgs} assistant)",
            f"  [bold]Est. tokens:[/bold] ~{est_tokens:,}",
            f"  [bold]Tools:[/bold]     {tool_count} registered",
        ]

        # Brief mode indicator
        brief = getattr(ctx.repl, "_brief_mode", False)
        if brief:
            lines.append(f"  [bold]Brief:[/bold]     [yellow]ON[/yellow]")

        await ctx.output_rich("\n".join(lines))
```

### Task 2: 创建 `__init__.py`

```python
# src/cascade/commands/workflow/__init__.py
```

### Task 3: 注册到 CascadeApp

**文件:** 修改 `src/cascade/ui/textual_app.py`

```python
        from cascade.commands.workflow.copy import CopyCommand
        from cascade.commands.workflow.status import StatusCommand
        self.router.register(CopyCommand())
        self.router.register(StatusCommand())
```

### Task 4: 在 CascadeApp.__init__ 中记录 session 开始时间

```python
        import time
        self._session_start = time.time()
```

### Task 5: 验证

```bash
cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade && source .venv/bin/activate
python -c "from cascade.ui.textual_app import CascadeApp; print('OK')"
```

### Task 6: 手动测试

```bash
cascade
# /status        → 显示 Version, Provider, Model, Session, Messages, Tokens, Tools
# /summary       → 同上（别名）
# /stats         → 同上（别名）
# /copy          → 复制最后一条 AI 回复到剪贴板
# /copy 2        → 复制倒数第二条
# /diff           → 显示 git diff（彩色输出）
# /diff --staged  → 显示暂存区变更
# /help           → Workflow 分组含 3 个命令
```

---

## L1~L4 验收标准

| Level | 检查项 | 标准 |
|-------|--------|------|
| L1 | `commands/workflow/` 含 3 个 .py 文件 | `ls` 确认 |
| L2 | 每个命令的 docstring 标注 Claude Code 参考路径和实现差异 | `grep -r "Reference:" src/cascade/commands/workflow/` |
| L3 | `/copy` 正确复制到系统剪贴板 + 写入 `/tmp/cascade/response.md` | 手动验证 |
| L4 | `/summary` 和 `/stats` 别名均触发 `/status` | 手动测试 |

---

## 与 Claude Code 的差异汇总

| 命令 | Claude Code | Cascade | 差异原因 |
|------|-------------|---------|---------|
| `/copy` | 371 行，`marked.lexer()` 代码块提取 + `CopyPicker` JSX 交互选择器 + OSC 52 | subprocess `pbcopy`/`xclip` + 完整复制 | 无 marked、无 JSX、无 OSC 52 |
| ~~`/diff`~~ | ~~9 行入口 → `DiffDialog` JSX~~ | **已移除** | 被 BashTool 替代 |
| `/status` | 8 行入口 → `Settings` 组件 Status Tab（含 API 连接状态、account 信息） | 文本面板合并 status + stats + summary | 三个 Claude Code 命令合一；无 Settings JSX |
