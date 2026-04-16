# Phase 9.4.5: Batch 4.5 — 自动模式命令 (1 command)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 实现 `/auto` 命令 —— 切换工具调用自动批准模式。

**架构:** `BaseCommand` + `CommandContext`，添加到 `commands/tools/` 子包。利用已有的 `PermissionEngine.mode` 在 `AUTO` 和 `BYPASS` 之间切换。

**前置条件:** Phase 9.4 (Batch 4) 完成。

---

## 📊 命令总览

| 命令 | Claude Code 参考源码 | Cascade 实现级别 | 架构限制 |
|------|---------------------|-----------------|---------|
| `/auto` | **无独立命令** — Claude Code 使用 CLI flag `--dangerously-skip-permissions` | ✅ Cascade 原创 | 无——`PermissionEngine` 已支持 `BYPASS` 模式 |

> [!IMPORTANT]
> Claude Code **没有** `/auto` 斜杠命令。自动批准功能通过以下方式实现：
> - CLI 启动参数：`--dangerously-skip-permissions`（跳过所有权限检查）
> - `/sandbox` 命令中的 `auto-allow` 模式（`SandboxManager.isAutoAllowBashIfSandboxedEnabled()`）
> - `/permissions` 中的 allow rules（添加 `Bash(*):*` 等通配规则）
>
> Cascade 的 `/auto` 是原创设计，直接 toggle `PermissionEngine.mode` 在 `AUTO`（默认，destructive 工具需确认）和 `BYPASS`（全部自动批准）之间切换。

---

## 实现原理

**核心机制已存在：**

1. `PermissionEngine`（`src/cascade/permissions/engine.py:38`）已有 `BYPASS` 模式：
   ```python
   if self.mode == PermissionMode.BYPASS:
       return PermissionResult(True, "bypass mode")
   ```

2. `QueryEngine.submit()`（`src/cascade/engine/query.py:119`）每次 tool call 前调用 `self.permissions.check()`

3. **不需要修改任何执行流代码**——只需 toggle `permissions.mode` 即可。

---

## 实施步骤

### Task 1: 创建 auto 命令

**文件:** 创建 `src/cascade/commands/tools/auto.py`

```python
# src/cascade/commands/tools/auto.py
from cascade.commands.base import BaseCommand, CommandContext
from cascade.permissions.engine import PermissionMode


class AutoCommand(BaseCommand):
    """Toggle automatic tool approval mode.

    Reference: NO direct Claude Code slash command equivalent.
    Claude Code implements similar functionality via:
    1. CLI flag: --dangerously-skip-permissions (skips all permission checks)
    2. /sandbox auto-allow mode (SandboxManager.isAutoAllowBashIfSandboxedEnabled())
    3. /permissions allow rules (e.g., Bash(*):* wildcard rules)
    Cascade impl: ORIGINAL design. Toggles PermissionEngine.mode between
    AUTO (destructive tools require confirmation) and BYPASS (all tools
    auto-approved). Designed for HEP batch workflows where manual
    confirmation of every cmsRun/hadd call is impractical.
    """
    name = "auto"
    description = "Toggle automatic tool approval"
    category = "Tools"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        perms = ctx.engine.permissions
        if perms is None:
            await ctx.output_rich("[dim]No permission system configured.[/dim]")
            return

        if perms.mode == PermissionMode.BYPASS:
            perms.mode = PermissionMode.AUTO
            await ctx.output_rich(
                "[#00d7af]Auto-approve: OFF[/#00d7af]\n"
                "[dim]Tool calls will require manual confirmation.[/dim]"
            )
        else:
            perms.mode = PermissionMode.BYPASS
            await ctx.output_rich(
                "[bold yellow]⚠ Auto-approve: ON[/bold yellow]\n"
                "[dim]All tool calls will be approved automatically.\n"
                "Use /auto again to disable.[/dim]"
            )
```

### Task 2: 注册到 CascadeApp

**文件:** 修改 `src/cascade/ui/textual_app.py`

在 ToolsCommand 注册后添加：
```python
        from cascade.commands.tools.auto import AutoCommand
        self.router.register(AutoCommand())
```

### Task 3: 验证

```bash
cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade && source .venv/bin/activate
python -c "from cascade.ui.textual_app import CascadeApp; print('OK')"
```

### Task 4: 手动测试

```bash
cascade
# /auto   → "⚠ Auto-approve: ON" (黄色警告)
# /auto   → "Auto-approve: OFF" (绿色确认)
# /help   → Tools 分组含 /auto
```

---

## L1~L4 验收标准

| Level | 检查项 | 标准 |
|-------|--------|------|
| L1 | `commands/tools/auto.py` 存在 | `ls` 确认 |
| L2 | 命令 docstring 标注 Claude Code 三种相关机制 | `grep "Reference:" src/cascade/commands/tools/auto.py` |
| L3 | toggle 正确切换 `PermissionMode`；ON 时显示黄色警告 | 手动验证 |
| L4 | 连续两次 `/auto` 回到 OFF（AUTO 模式） | 手动测试 |

---

## 安全考量

| 风险 | 缓解措施 |
|------|---------|
| 用户误开 auto 模式导致破坏性工具调用 | ⚠ 黄色警告 + 明确提示 "Use /auto again to disable" |
| auto 模式跨 session 持久化 | 不持久化——每次启动默认 AUTO |
| 与 `--dangerously-skip-permissions` CLI flag 冲突 | Cascade 暂无此 CLI flag，未来添加时需要协调 |

## 与 Claude Code 功能对比

| 功能 | Claude Code | Cascade `/auto` |
|------|-------------|-----------------|
| 跳过所有权限 | `--dangerously-skip-permissions` (CLI flag) | `/auto` toggle (runtime) |
| 沙箱内自动批准 | `/sandbox` auto-allow mode | 不区分沙箱/非沙箱 |
| 按工具类型自动批准 | `/permissions` allow rules (granular) | 全部或无（binary toggle） |
| 安全警告 | 名称含 "dangerously" | ⚠ 黄色警告 + 提示 |
| 持久化 | CLI flag 持续整个 session | toggle 持续整个 session |
