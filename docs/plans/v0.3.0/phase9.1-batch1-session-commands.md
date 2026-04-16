# Phase 9.1: Batch 1 — 会话管理命令 (6 commands)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 实现 `/compact`, `/resume`, `/rename`, `/branch`, `/rewind`, `/export` 六个会话管理命令。

**架构:** 基于 Phase 8 的 `BaseCommand` + `CommandContext` 架构，所有命令通过 `ctx.output()` / `ctx.output_rich()` 输出。

**技术栈:** Python 3.11+, Textual TUI, Rich markup

**前置条件:** Phase 8 完成（`BaseCommand`, `CommandRouter`, `CascadeApp`, 4 个核心命令 `/clear` `/exit` `/help` `/model`）

---

## 📊 命令总览

| 命令 | Claude Code 参考源码 | Cascade 实现级别 | 架构限制 |
|------|---------------------|-----------------|---------|
| `/compact` | `src/commands/compact/index.ts` + `compact.ts` (288行) | ⚠️ Stub + 基础统计 | 无 session memory / microcompact / reactive compact 系统 |
| `/resume` | `src/commands/resume/index.ts` (lazy-load `resume.js`) | ⚠️ Stub | 无会话持久化存储 |
| `/rename` | `src/commands/rename/index.ts` (`immediate: true`) | ⚠️ Stub | 无会话命名系统 |
| `/branch` | `src/commands/branch/index.ts` (alias `fork`) | ⚠️ Stub | 无会话分叉机制 |
| `/rewind` | `src/commands/rewind/index.ts` (alias `checkpoint`) | ⚠️ Stub | 无 checkpoint/快照系统 |
| `/export` | `src/commands/export/index.ts` + `export.tsx` (91行) | ✅ 完整实现 | 无限制，直接写文件 |

> [!IMPORTANT]
> **6 个命令中只有 `/export` 和 `/compact`（基础版）可以完整实现。**
> 其余 4 个因为 Cascade 当前没有会话持久化层（Phase 10+ 才有），只能作为 Stub 注册。
> Stub 不是空壳——它们会输出有用的状态信息（如消息数量），为未来的完整实现预留接口。

---

## Claude Code 源码参考详情

### `/compact` 参考分析

**源码位置:** `claude-code-src-haha/src/commands/compact/`
- [index.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/compact/index.ts) — 命令注册元数据（16行）
- [compact.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/compact/compact.ts) — 核心实现（288行）

**Claude Code 的 compact 做了什么：**
1. `trySessionMemoryCompaction()` — 优先尝试 session memory 压缩
2. `microcompactMessages()` — 预处理：去除冗余 token
3. `compactConversation()` — 核心：调用 LLM 生成对话摘要替换历史
4. `reactiveCompactOnPromptTooLong()` — 响应式压缩（feature flag）
5. 支持 `customInstructions` 参数（用户自定义压缩指令）
6. 依赖：`services/compact/`, `services/SessionMemory/`, hooks 系统

**Cascade 可以做到的：**
- 统计当前消息数量和 token 估算
- 调用 LLM 生成对话摘要
- 用摘要替换 `engine.messages` 列表
- 不支持：session memory、microcompact、reactive compact、hooks

### `/export` 参考分析

**源码位置:** `claude-code-src-haha/src/commands/export/`
- [index.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/export/index.ts) — 元数据（12行）
- [export.tsx](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/export/export.tsx) — 实现（91行）

**Claude Code 的 export 做了什么：**
1. `renderMessagesToPlainText()` — 将消息渲染为纯文本
2. 支持 `args` 直接指定文件名（跳过对话框）
3. 无参数时：`ExportDialog` JSX 组件，显示文件名输入框
4. 自动生成文件名：`YYYY-MM-DD-HHmmss-<sanitized-first-prompt>.txt`
5. `sanitizeFilename()` — 清理特殊字符
6. `extractFirstPrompt()` — 从首条用户消息提取摘要

**Cascade 可以做到的：**
- 全部功能，因为只需要文件 I/O + JSON 序列化
- 简化版：不需要 ExportDialog（Textual 直接输出到文件）
- 支持 JSON 格式导出（比 Claude Code 的 txt 更实用）

### `/resume`, `/rename`, `/branch`, `/rewind` 参考分析

这 4 个命令在 Claude Code 中都是 `local-jsx` 类型，lazy-load 实际组件：
- [resume/index.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/resume/index.ts) — aliases: `['continue']`, argumentHint: `'[conversation id or search term]'`
- [rename/index.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/rename/index.ts) — `immediate: true`
- [branch/index.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/branch/index.ts) — aliases: `['fork']`（当 FORK_SUBAGENT feature 关闭时）
- [rewind/index.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/rewind/index.ts) — aliases: `['checkpoint']`, `type: 'local'`

**Cascade 当前无法完整实现的原因：**
- 没有 `SessionStorage` / `ConversationDB`（没有 SQLite/文件持久化层）
- 没有 `checkpoint` 快照机制（git stash 式的消息状态保存）
- 这些是 Phase 10 "会话管理" 的核心基建

---

## 实施步骤

### Task 1: 创建 session 命令子包

**文件:**
- 创建: `src/cascade/commands/core/compact.py`
- 创建: `src/cascade/commands/core/resume.py`
- 创建: `src/cascade/commands/core/rename.py`
- 创建: `src/cascade/commands/core/branch.py`
- 创建: `src/cascade/commands/core/rewind.py`
- 创建: `src/cascade/commands/core/export_cmd.py`

#### `/compact` — 基础版实现

```python
# src/cascade/commands/core/compact.py
from cascade.commands.base import BaseCommand, CommandContext


class CompactCommand(BaseCommand):
    """Summarize and compress conversation context.

    Reference: claude-code src/commands/compact/compact.ts
    Claude Code impl: 288 lines, supports session memory compaction,
    microcompact, reactive compact, custom instructions, hooks.
    Cascade impl: basic message counting + LLM summarization.
    """
    name = "compact"
    description = "Summarize and compress conversation context"
    category = "Session"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        msg_count = len(ctx.engine.messages)
        if msg_count == 0:
            await ctx.output_rich("[dim]No messages to compact.[/dim]")
            return

        # Estimate token count (rough: 4 chars ≈ 1 token)
        total_chars = sum(
            len(str(m.get("content", ""))) for m in ctx.engine.messages
        )
        est_tokens = total_chars // 4

        if msg_count <= 2:
            await ctx.output_rich(
                "[dim]Too few messages to compact "
                f"({msg_count} messages, ~{est_tokens} tokens).[/dim]"
            )
            return

        await ctx.output_rich(
            f"[bold]Compact[/bold]\n"
            f"  Messages: {msg_count}\n"
            f"  Est. tokens: ~{est_tokens}\n"
            f"  [dim](Full LLM-based compaction coming in a future release)[/dim]"
        )
```

#### `/export` — 完整实现

```python
# src/cascade/commands/core/export_cmd.py
from cascade.commands.base import BaseCommand, CommandContext
import json
import os
from datetime import datetime


class ExportCommand(BaseCommand):
    """Export conversation to file.

    Reference: claude-code src/commands/export/export.tsx
    Claude Code impl: 91 lines, supports txt export with ExportDialog,
    auto-generated filenames from first prompt, sanitizeFilename().
    Cascade impl: JSON export with auto-generated filenames.
    """
    name = "export"
    description = "Export conversation to file"
    category = "Session"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        messages = ctx.engine.messages
        if not messages:
            await ctx.output_rich("[dim]No messages to export.[/dim]")
            return

        if args.strip():
            filepath = args.strip()
        else:
            # Auto-generate filename (ref: Claude Code's formatTimestamp)
            ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
            # Extract first prompt summary (ref: extractFirstPrompt)
            first_user = next(
                (m for m in messages if m.get("role") == "user"), None
            )
            suffix = ""
            if first_user:
                content = str(first_user.get("content", ""))[:50]
                # Sanitize (ref: sanitizeFilename)
                suffix = "".join(
                    c if c.isalnum() or c in " -" else ""
                    for c in content
                ).strip().replace(" ", "-")[:30]
            filename = f"{ts}-{suffix}.json" if suffix else f"conversation-{ts}.json"
            filepath = os.path.join(os.getcwd(), filename)

        # Ensure .json extension
        if not filepath.endswith(".json"):
            filepath = filepath.rsplit(".", 1)[0] + ".json" if "." in filepath else filepath + ".json"

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(messages, f, indent=2, ensure_ascii=False)
            msg_count = len(messages)
            await ctx.output_rich(
                f"[#00d7af]Exported {msg_count} messages to {filepath}[/#00d7af]"
            )
        except OSError as e:
            await ctx.output_rich(f"[red]Export failed: {e}[/red]")
```

#### Stub 模板（`/resume`, `/rename`, `/branch`, `/rewind`）

```python
# src/cascade/commands/core/resume.py
from cascade.commands.base import BaseCommand, CommandContext


class ResumeCommand(BaseCommand):
    """Resume a previous conversation.

    Reference: claude-code src/commands/resume/index.ts
    Claude Code impl: aliases=['continue'], lazy-loads resume.js
    with session picker UI. Requires SessionStorage.
    Cascade impl: Stub — session persistence not yet available.
    """
    name = "resume"
    description = "Resume a previous conversation"
    aliases = ["/continue"]
    category = "Session"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        await ctx.output_rich(
            "[dim]/resume: Session persistence coming in Phase 10. "
            "Currently, conversations are not saved between sessions.[/dim]"
        )
```

```python
# src/cascade/commands/core/rename.py
from cascade.commands.base import BaseCommand, CommandContext


class RenameCommand(BaseCommand):
    """Rename the current conversation.

    Reference: claude-code src/commands/rename/index.ts
    Claude Code impl: immediate=true, lazy-loads rename.js.
    Cascade impl: Stub — no conversation naming system yet.
    """
    name = "rename"
    description = "Rename the current conversation"
    category = "Session"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        await ctx.output_rich(
            "[dim]/rename: Conversation naming coming in Phase 10.[/dim]"
        )
```

```python
# src/cascade/commands/core/branch.py
from cascade.commands.base import BaseCommand, CommandContext


class BranchCommand(BaseCommand):
    """Create a branch of the current conversation.

    Reference: claude-code src/commands/branch/index.ts
    Claude Code impl: aliases=['fork'] (when FORK_SUBAGENT off).
    Cascade impl: Stub — no conversation branching system yet.
    """
    name = "branch"
    description = "Create a branch of the current conversation"
    aliases = ["/fork"]
    category = "Session"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        await ctx.output_rich(
            "[dim]/branch: Conversation branching coming in Phase 10.[/dim]"
        )
```

```python
# src/cascade/commands/core/rewind.py
from cascade.commands.base import BaseCommand, CommandContext


class RewindCommand(BaseCommand):
    """Restore conversation to a previous point.

    Reference: claude-code src/commands/rewind/index.ts
    Claude Code impl: aliases=['checkpoint'], type='local'.
    Cascade impl: Stub — no checkpoint/snapshot system yet.
    """
    name = "rewind"
    description = "Restore conversation to a previous point"
    aliases = ["/checkpoint"]
    category = "Session"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        await ctx.output_rich(
            "[dim]/rewind: Conversation checkpoints coming in Phase 10.[/dim]"
        )
```

### Task 2: 注册到 CascadeApp

**文件:** 修改 `src/cascade/ui/textual_app.py`

在现有注册之后添加:
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

### Task 3: 验证

```bash
cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade && source .venv/bin/activate
python -c "from cascade.ui.textual_app import CascadeApp; print('OK')"
```

### Task 4: 手动测试

```bash
cascade
# /help     → 应显示 10 个命令，Session 分组展开
# /export /tmp/test.json → 应写入文件
# /compact  → "Compact: N messages..."
# /resume   → 显示 Phase 10 提示
# /fork     → 应触发 /branch（别名）
```

---

## L1~L4 验收标准

| Level | 检查项 | 标准 |
|-------|--------|------|
| L1 存在性 | 6 个 .py 文件存在于 `commands/core/` | `ls src/cascade/commands/core/` 显示所有文件 |
| L2 结构性 | 每个命令继承 `BaseCommand`，有 `name`, `description`, `category`, `execute()` | `grep -r "class.*BaseCommand" src/cascade/commands/core/` |
| L3 内容性 | `/export` 能正确写出 JSON；`/compact` 显示统计；Stub 显示提示文字 | 手动 `/export /tmp/test.json` → 文件有效 |
| L4 功能性 | `/help` 显示 Session 分组包含 6 个命令；别名 `/fork` `/checkpoint` `/continue` 工作 | 手动测试所有别名 |

---

## 后续 Batch

| 批次 | 文件 | 命令 |
|------|------|------|
| **9.2** | `phase9.2-batch2-setup-commands.md` | `/version`, `/config`, `/doctor`, `/init`, `/env` |
| **9.3** | `phase9.3-batch3-ui-commands.md` | `/theme`, `/brief`, `/btw`, `/shortcuts` (**新增**) |
| **9.3.5** | `phase9.3.5-batch3.5-new-commands.md` | `/copy`, `/diff`, `/status` (**新增 P0**) |
| **9.4** | `phase9.4-batch4-tools-commands.md` | `/permissions`, `/hooks`, `/debug-tool-call`, `/sandbox-toggle`, `/tools` (**新增**) |
| **9.4.5** | `phase9.4.5-auto-mode.md` | `/auto` |
| **9.5** | `phase9.5-batch5-git-commands.md` | `/commit`, `/commit-push-pr`, `/pr-comments`, `/review`, `/security-review` |
| **9.6** | `phase9.6-batch6-memory-commands.md` | `/memory`, `/summary` → 合并升级为 `/status` 子功能 |
| **9.7** | `phase9.7-batch7-plugin-commands.md` | `/plugin`, `/reload-plugins`, `/skills`, `/agents`, `/mcp`, `/tasks` |
