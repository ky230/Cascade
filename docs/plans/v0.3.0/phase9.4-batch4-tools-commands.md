# Phase 9.4: Batch 4 — 工具管理命令 (1 command)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 实现 `/tools` 命令（Cascade 原创）。

> [!WARNING]
> **以下命令已移除：**
> - ~~`/permissions`~~ — 当前 PermissionEngine 只有 mode 属性，无 allow/deny list。等 Phase 6 (v0.9.0) Advanced Permission System 完成后再加。
> - ~~`/hooks`~~ — 等 Phase 7 (v0.10.0) Hooks & CASCADE.md Rules 基建完成后再加。
> - ~~`/sandbox`~~ — Claude Code 的沙箱依赖闭源 `@anthropic-ai/sandbox-runtime` 包（986 行适配器 + 未知规模 runtime），Long-term Plan 不包含此功能。
> - ~~`/debug-tool-call`~~ — Claude Code 自己也已禁用（`isEnabled: false, isHidden: true`），纯废代码。

**架构:** `BaseCommand` + `CommandContext`，新建 `commands/tools/` 子包。

**前置条件:** Phase 9.3.5 (Batch 3.5) 完成。

---

## 📊 命令总览

| 命令 | Claude Code 参考源码 | Cascade 实现级别 | 备注 |
|------|---------------------|-----------------|------|
| `/tools` | **无直接对应** — Claude Code 工具信息分散在 `/status` + `/permissions` | ✅ Cascade 原创 | 灵感来自 Gemini CLI |
| ~~`/permissions`~~ | `src/commands/permissions/` | ❌ **已移除** | 等 Phase 6 |
| ~~`/hooks`~~ | `src/commands/hooks/` | ❌ **已移除** | 等 Phase 7 |
| ~~`/sandbox`~~ | `src/commands/sandbox-toggle/` (986行+) | ❌ **已移除** | 不实现 |
| ~~`/debug-tool-call`~~ | `src/commands/debug-tool-call/` (已禁用) | ❌ **已移除** | CC 也禁用了 |

---

## Claude Code 源码参考详情

### `/tools` — Cascade 原创

Claude Code 没有独立的 `/tools` 命令。工具信息分散在：
- `/status` → Settings 组件的 Status Tab 中显示 tool statuses
- `/permissions` → PermissionRuleList 中显示工具列表
- `getTools(permissionContext)` — 运行时工具注册

Cascade 的 `/tools` 将这些信息整合为一个独立命令，灵感来自 Gemini CLI。

---

## 实施步骤

### Task 1: 创建 tools 命令子包

**文件:**
- 创建: `src/cascade/commands/tools/__init__.py`
- 创建: `src/cascade/commands/tools/tools_list.py`

#### `/tools`

```python
# src/cascade/commands/tools/tools_list.py
from cascade.commands.base import BaseCommand, CommandContext


class ToolsCommand(BaseCommand):
    """List all registered tools and their status.

    Reference: NO direct Claude Code equivalent.
    Claude Code distributes tool info across /status (Settings Status Tab),
    /permissions (PermissionRuleList), and getTools() runtime API.
    Cascade impl: ORIGINAL command inspired by Gemini CLI. Consolidates
    all tool information into a single command: name, description, and
    enabled/disabled status. This is a Cascade differentiator.
    """
    name = "tools"
    description = "List all registered tools"
    category = "Tools"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        registry = getattr(ctx.engine, "registry", None)
        if not registry:
            await ctx.output_rich("[dim]No tool registry available.[/dim]")
            return

        tools = registry.list_tools()
        if not tools:
            await ctx.output_rich("[dim]No tools registered.[/dim]")
            return

        lines = [f"[bold]Tools ({len(tools)} registered)[/bold]\n"]
        for tool in sorted(tools, key=lambda t: t.name):
            desc = getattr(tool, "description", "")[:60]
            lines.append(
                f"  [green]●[/green] [bold]{tool.name}[/bold]"
                f"  [dim]{desc}[/dim]"
            )
        await ctx.output_rich("\n".join(lines))
```

### Task 2: 创建 `__init__.py`

```python
# src/cascade/commands/tools/__init__.py
```

### Task 3: 注册到 CascadeApp

**文件:** 修改 `src/cascade/ui/textual_app.py`

```python
        from cascade.commands.tools.tools_list import ToolsCommand
        self.router.register(ToolsCommand())
```

### Task 4: 验证

```bash
cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade && source .venv/bin/activate
python -c "from cascade.ui.textual_app import CascadeApp; print('OK')"
```

### Task 5: 手动测试

```bash
cascade
# /tools            → 列出所有注册工具 + 描述
# /help             → Tools 分组含 1 个命令
```

---

## L1~L4 验收标准

| Level | 检查项 | 标准 |
|-------|--------|------|
| L1 | `commands/tools/` 含 2 个 .py 文件 | `ls` 确认 |
| L2 | docstring 标注 "NO direct Claude Code equivalent" + Gemini CLI 灵感 | `grep -r "Reference:" src/cascade/commands/tools/` |
| L3 | `/tools` 正确列出 registry 中所有工具（5 个） | 手动验证 |
| L4 | `/help` 的 Tools 分组只含 1 个命令 | 手动测试 |

---

## 与 Claude Code 的差异汇总

| 命令 | Claude Code | Cascade | 差异原因 |
|------|-------------|---------|---------| 
| `/tools` | **不存在** | ✅ Cascade 原创 | 行业共识功能，CC 信息分散 |
| ~~`/permissions`~~ | JSX `PermissionRuleList` | **已移除** | 等 Phase 6 权限基建 |
| ~~`/hooks`~~ | `HooksConfigMenu` JSX | **已移除** | 等 Phase 7 Hooks 基建 |
| ~~`/sandbox`~~ | 闭源 `sandbox-runtime` 包 | **已移除** | 不实现 |
| ~~`/debug-tool-call`~~ | `isEnabled: false` | **已移除** | CC 也禁用了 |
