# Phase 9.7: Batch 7 — 插件与高级命令 (6 commands)

> [!CAUTION]
> **❌ 已取消 (2026-04-16)**
>
> 原因：6 个命令中 `/model` 已在 Phase 9.4 实现，`/plugin` `/insights` 仅为 stub，
> `/skills` `/cost` `/effort` 依赖底层基础设施（cost_tracker, model_config 等），
> 将在 Long-Term Plan Phase 2-3 建好基础设施后实现。
>
> 对应 long-term plan 位置：
> - `/cost` → Phase 2 Task 7 (cost_tracker.py)
> - `/model` → Phase 3 Task 10.5 (model_config.py)
> - `/plugin` → Long-term Task 17
> - `/skills` → Long-term Task 18

> **For Claude:** ~~REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.~~

**目标:** ~~实现 `/plugin`, `/skills`, `/model`, `/cost`, `/effort`, `/insights` 六个插件管理与高级功能命令。~~

**架构:** `BaseCommand` + `CommandContext`，新建 `commands/advanced/` 子包。

**前置条件:** Phase 9.6 (Batch 6) 完成。

**注：** 这是 Phase 9 的最后一个 batch。**已取消，后续随底层基础设施逐步实现。**

---

## 📊 命令总览

| 命令 | Claude Code 参考源码 | Cascade 实现级别 | 架构限制 |
|------|---------------------|-----------------|---------|
| `/plugin` | `src/commands/plugin/` — 17 个文件，**总计 ~830KB**（巨型 JSX 管理界面） | ⚠️ Stub | 无 plugin marketplace 系统 |
| `/skills` | `src/commands/skills/skills.tsx` (8行，渲染 `SkillsMenu` JSX) | ✅ 文本列表版 | 无 JSX `SkillsMenu` |
| `/model` | `src/commands/model/` — `index.ts` (17行) + `model.tsx` (37KB，动态 `renderModelName`) | ✅ 简化版 | 无模型切换器 JSX |
| `/cost` | `src/commands/cost/` — `index.ts` (24行) + `cost.ts` (25行，`formatTotalCost`) | ✅ 文本版 | 无 `cost-tracker` 精确统计 |
| `/effort` | `src/commands/effort/` — `index.ts` (14行) + `effort.tsx` (22KB，JSX slider) | ✅ 文本选择版 | 无 JSX effort slider |
| `/insights` | `src/commands/insights.ts` — **3,201 行**（最长命令文件） | ⚠️ Stub | 依赖 `SessionStorage`、Opus 分析、facet extraction |

> [!WARNING]
> **`/plugin` 目录是 Claude Code 最庞大的命令模块：** 17 个文件、800KB+ 代码。
> 包含 `BrowseMarketplace.tsx` (119KB)、`ManagePlugins.tsx` (321KB) 等巨型组件。
> 这是一个完整的 marketplace 系统，远超 Cascade Phase 9 的范围。
>
> **`/insights` 是 Claude Code 中单文件最长的命令：** 3,201 行。
> 功能包括：遍历所有历史 session → 提取 facets（用 Opus 分析） → 生成 HTML 报告。
> 依赖 `SessionStorage` + LLM 调用 + HTML 生成 + 远程 homespace 数据收集。

---

## Claude Code 源码参考详情

### `/plugin` 参考分析

**源码:** [plugin/index.tsx](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/plugin/index.tsx) — 11行
- `type: 'local-jsx'`，`immediate: true`
- `aliases: ['plugins', 'marketplace']`
- `description: 'Manage Claude Code plugins'`

**源码目录结构（17 个文件，~830KB 总计）：**
- `plugin.tsx` (1.6KB) — 入口
- `ManagePlugins.tsx` (321KB) — 已安装插件管理
- `BrowseMarketplace.tsx` (119KB) — 浏览 marketplace
- `DiscoverPlugins.tsx` (106KB) — 插件发现
- `ManageMarketplaces.tsx` (118KB) — marketplace 管理
- `PluginSettings.tsx` (128KB) — 插件设置
- `UnifiedInstalledCell.tsx` (44KB) — 已安装插件 UI
- `AddMarketplace.tsx` (21KB) — 添加 marketplace
- `PluginErrors.tsx` (23KB) — 错误处理
- `PluginOptionsDialog.tsx` (34KB) — 配置选项
- `PluginOptionsFlow.tsx` (18KB) — 配置流程
- `ValidatePlugin.tsx` (12KB) — 插件验证
- `PluginTrustWarning.tsx` (3.9KB) — 安全警告
- `pluginDetailsHelpers.tsx` (12KB) — 辅助函数
- `parseArgs.ts` (2.8KB) — 参数解析
- `usePagination.ts` (4.9KB) — 分页

**另见:** [reload-plugins/reload-plugins.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/reload-plugins/reload-plugins.ts) — 62行
- `refreshActivePlugins(context.setAppState)` 重新加载所有插件
- 输出：enabled_count, command_count, agent_count, hook_count, mcp_count, lsp_count

**Cascade 适配:** Cascade 没有 plugin/marketplace 系统。Stub 输出提示。

### `/skills` 参考分析

**源码:** [skills/skills.tsx](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/skills/skills.tsx) — 8行
- 渲染 `<SkillsMenu onExit={onDone} commands={context.options.commands} />`
- Skills = prompt commands（从 `.claude/commands/` 目录加载）

**Cascade 适配:** 扫描 `commands/` 目录和 router 注册表，列出所有可用 slash commands（等效于 skills）。

### `/model` 参考分析

**源码:** [model/index.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/model/index.ts) — 17行
- `type: 'local-jsx'`
- `description` 动态 getter：`"Set the AI model ... (currently ${renderModelName(getMainLoopModel())})"`
- `immediate` 动态 getter：`shouldInferenceConfigCommandBeImmediate()`

**源码:** `model/model.tsx` — 37KB（完整的模型选择器 JSX）

**Cascade 适配:** 显示当前 model + 文本列出 provider 支持的可选模型。

### `/cost` 参考分析

**源码:** [cost/index.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/cost/index.ts) — 24行
- `type: 'local'`，`supportsNonInteractive: true`
- `isHidden` getter：对 Claude AI 订阅用户隐藏（除非是 ant）

**源码:** [cost/cost.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/cost/cost.ts) — 25行
- `formatTotalCost()` — 从 `cost-tracker.js` 获取
- 订阅用户显示订阅/过额状态；API 用户显示实际费用

**Cascade 适配:** 基于 token 估算的粗略费用计算。

### `/effort` 参考分析

**源码:** [effort/index.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/effort/index.ts) — 14行
- `type: 'local-jsx'`
- `argumentHint: '[low|medium|high|max|auto]'`

**源码:** `effort/effort.tsx` — 22KB（JSX effort slider）

**Cascade 适配:** 文本选择 + 设置 `engine.effort` 参数。

### `/insights` 参考分析

**源码:** [insights.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/insights.ts) — **3,201 行**
- `type: 'prompt'` → 前 800 行已读取
- 功能：遍历所有历史 session 文件，提取统计数据和 facets，用 Opus 模型分析，生成 HTML 报告
- 数据结构：`SessionMeta`（25+ 字段）、`SessionFacets`（12 字段）、`AggregatedData`（30+ 字段）
- 内含 Anthropic 内部特有逻辑（Coder remote host 数据收集、ant-only 统计）
- HTML 报告包含：Dashboard、Session Timeline、Tool Usage、Language Stats 等

**Cascade 适配:** Stub — 依赖 SessionStorage（Phase 10）和 LLM facet extraction。

---

## 实施步骤

### Task 1: 创建 advanced 命令子包

**文件:**
- 创建: `src/cascade/commands/advanced/__init__.py`
- 创建: `src/cascade/commands/advanced/plugin.py`
- 创建: `src/cascade/commands/advanced/skills.py`
- 创建: `src/cascade/commands/advanced/model.py`
- 创建: `src/cascade/commands/advanced/cost.py`
- 创建: `src/cascade/commands/advanced/effort.py`
- 创建: `src/cascade/commands/advanced/insights.py`

#### `/plugin`

```python
# src/cascade/commands/advanced/plugin.py
from cascade.commands.base import BaseCommand, CommandContext


class PluginCommand(BaseCommand):
    """Manage Cascade plugins.

    Reference: claude-code src/commands/plugin/ — 17 files, ~830KB total
    Claude Code impl: type='local-jsx', immediate=true.
    aliases=['plugins','marketplace']. Massive JSX-based plugin management:
    ManagePlugins.tsx (321KB), BrowseMarketplace.tsx (119KB),
    DiscoverPlugins.tsx (106KB), PluginSettings.tsx (128KB), etc.
    Also: reload-plugins/reload-plugins.ts (62 lines) — refreshActivePlugins()
    reloads all plugins + counts (plugins, commands, agents, hooks, MCP, LSP).
    Cascade impl: Stub — plugin/marketplace system not implemented.
    """
    name = "plugin"
    description = "Manage Cascade plugins"
    aliases = ["/plugins"]
    category = "Advanced"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        await ctx.output_rich(
            "[dim]/plugin: Plugin marketplace coming in a future release.\n"
            "Currently Cascade uses built-in tools only.[/dim]"
        )
```

#### `/skills`

```python
# src/cascade/commands/advanced/skills.py
from cascade.commands.base import BaseCommand, CommandContext


class SkillsCommand(BaseCommand):
    """List available slash commands (skills).

    Reference: claude-code src/commands/skills/skills.tsx (8 lines)
    Claude Code impl: renders <SkillsMenu onExit={onDone}
    commands={context.options.commands} />. Skills = prompt commands loaded
    from .claude/commands/ directory. SkillsMenu shows interactive list.
    Cascade impl: text-based list of all registered slash commands
    from the CommandRouter, grouped by category.
    """
    name = "skills"
    description = "List available slash commands"
    category = "Advanced"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        router = getattr(ctx.repl, "router", None)
        if not router:
            await ctx.output_rich("[dim]No command router available.[/dim]")
            return

        commands = router.list_commands()
        if not commands:
            await ctx.output_rich("[dim]No commands registered.[/dim]")
            return

        # Group by category
        groups: dict[str, list] = {}
        for cmd in commands:
            cat = getattr(cmd, "category", "Other")
            if getattr(cmd, "hidden", False):
                continue
            groups.setdefault(cat, []).append(cmd)

        lines = [f"[bold]Slash Commands ({len(commands)} total)[/bold]\n"]
        for cat in sorted(groups.keys()):
            lines.append(f"  [bold #5fd7ff]{cat}[/bold #5fd7ff]")
            for cmd in sorted(groups[cat], key=lambda c: c.name):
                lines.append(
                    f"    /{cmd.name:<20} [dim]{cmd.description}[/dim]"
                )
            lines.append("")
        await ctx.output_rich("\n".join(lines))
```

#### `/model`

```python
# src/cascade/commands/advanced/model.py
from cascade.commands.base import BaseCommand, CommandContext


class ModelCommand(BaseCommand):
    """Switch AI model.

    Reference: claude-code src/commands/model/index.ts (17 lines)
    + model.tsx (37KB JSX model picker)
    Claude Code impl: type='local-jsx'. Dynamic description getter shows
    current model via renderModelName(getMainLoopModel()). Dynamic
    immediate getter via shouldInferenceConfigCommandBeImmediate().
    model.tsx renders full interactive model selector with provider info.
    Cascade impl: shows current model + lists configured alternatives.
    Model switching implementation depends on engine.client architecture.
    """
    name = "model"
    description = "Switch AI model"
    category = "Advanced"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        current = ctx.engine.client.model_name
        provider = ctx.engine.client.provider

        if args.strip():
            # Attempt to switch model
            new_model = args.strip()
            try:
                ctx.engine.client.model_name = new_model
                await ctx.output_rich(
                    f"[#00d7af]Model switched:[/#00d7af] "
                    f"{current} → [bold]{new_model}[/bold]"
                )
            except Exception as e:
                await ctx.output_rich(
                    f"[red]Failed to switch model:[/red] {e}"
                )
            return

        await ctx.output_rich(
            f"[bold]Current Model[/bold]\n"
            f"  Provider: [#0087ff]{provider}[/#0087ff]\n"
            f"  Model:    [bold]{current}[/bold]\n\n"
            f"[dim]Usage: /model <model-name>[/dim]"
        )
```

#### `/cost`

```python
# src/cascade/commands/advanced/cost.py
from cascade.commands.base import BaseCommand, CommandContext


class CostCommand(BaseCommand):
    """Show estimated session cost.

    Reference: claude-code src/commands/cost/cost.ts (25 lines)
    Claude Code impl: type='local', supportsNonInteractive=true.
    isHidden for Claude AI subscribers (except ants).
    call() checks isClaudeAISubscriber() → shows subscription status
    or formatTotalCost() from cost-tracker.js.
    Cascade impl: estimates cost from token count * per-token pricing.
    No cost-tracker integration (tokens are estimated, not tracked).
    """
    name = "cost"
    description = "Show estimated session cost"
    category = "Advanced"

    # Rough per-million-token pricing (USD)
    PRICING = {
        "claude": {"input": 3.0, "output": 15.0},
        "gpt-4o": {"input": 2.5, "output": 10.0},
        "gemini": {"input": 1.25, "output": 5.0},
        "deepseek": {"input": 0.27, "output": 1.10},
    }

    async def execute(self, ctx: CommandContext, args: str) -> None:
        messages = ctx.engine.messages
        model = ctx.engine.client.model_name.lower()

        input_chars = sum(
            len(str(m.get("content", "")))
            for m in messages if m.get("role") in ("user", "system")
        )
        output_chars = sum(
            len(str(m.get("content", "")))
            for m in messages if m.get("role") == "assistant"
        )

        input_tokens = input_chars // 4
        output_tokens = output_chars // 4

        # Find pricing
        pricing = self.PRICING.get("claude")  # default
        for key, p in self.PRICING.items():
            if key in model:
                pricing = p
                break

        input_cost = input_tokens / 1_000_000 * pricing["input"]
        output_cost = output_tokens / 1_000_000 * pricing["output"]
        total_cost = input_cost + output_cost

        await ctx.output_rich(
            f"[bold]Session Cost Estimate[/bold]\n\n"
            f"  Input:  ~{input_tokens:,} tokens  →  ${input_cost:.4f}\n"
            f"  Output: ~{output_tokens:,} tokens  →  ${output_cost:.4f}\n"
            f"  [bold]Total:  ${total_cost:.4f}[/bold]\n\n"
            f"[dim]Estimates based on approximate token counts "
            f"and public pricing.[/dim]"
        )
```

#### `/effort`

```python
# src/cascade/commands/advanced/effort.py
from cascade.commands.base import BaseCommand, CommandContext


class EffortCommand(BaseCommand):
    """Set effort level for model responses.

    Reference: claude-code src/commands/effort/index.ts (14 lines)
    + effort.tsx (22KB JSX slider)
    Claude Code impl: type='local-jsx'.
    argumentHint='[low|medium|high|max|auto]'. Dynamic immediate getter.
    effort.tsx renders interactive slider component for effort selection.
    Cascade impl: text-based effort selection. Sets engine parameter
    that affects model temperature/max_tokens/thinking budget.
    """
    name = "effort"
    description = "Set effort level"
    category = "Advanced"

    LEVELS = ["low", "medium", "high", "max", "auto"]

    async def execute(self, ctx: CommandContext, args: str) -> None:
        arg = args.strip().lower()
        current = getattr(ctx.engine, "effort", "auto")

        if arg and arg in self.LEVELS:
            ctx.engine.effort = arg
            indicators = {
                "low": "⚡", "medium": "⚙️",
                "high": "🔥", "max": "🚀", "auto": "🤖"
            }
            await ctx.output_rich(
                f"{indicators[arg]} [bold]Effort: {arg}[/bold]"
            )
            return

        lines = ["[bold]Effort Level[/bold]\n"]
        for level in self.LEVELS:
            marker = "●" if level == current else "○"
            color = "green" if level == current else "dim"
            lines.append(f"  [{color}]{marker} {level}[/{color}]")
        lines.append(f"\n[dim]Usage: /effort <{'|'.join(self.LEVELS)}>[/dim]")
        await ctx.output_rich("\n".join(lines))
```

#### `/insights`

```python
# src/cascade/commands/advanced/insights.py
from cascade.commands.base import BaseCommand, CommandContext


class InsightsCommand(BaseCommand):
    """View usage insights and analytics.

    Reference: claude-code src/commands/insights.ts (3,201 lines)
    Claude Code impl: THE LONGEST single command file. type='prompt'.
    Functions: scans all historical session files → extracts SessionMeta
    (25+ fields) → uses Opus model for facet extraction (satisfaction,
    friction, goals, outcomes) → aggregates into AggregatedData (30+ fields)
    → generates interactive HTML dashboard (Dashboard, Session Timeline,
    Tool Usage, Language Stats, Multi-clauding detection).
    Also includes Anthropic-internal Coder remote host data collection.
    Cascade impl: Stub — requires SessionStorage (Phase 10) and LLM
    facet extraction. Will be one of the last commands to reach full parity.
    """
    name = "insights"
    description = "View usage insights and analytics"
    category = "Advanced"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        # Basic session stats (what we can provide without SessionStorage)
        msg_count = len(ctx.engine.messages)
        user_msgs = sum(
            1 for m in ctx.engine.messages if m.get("role") == "user"
        )
        total_chars = sum(
            len(str(m.get("content", "")))
            for m in ctx.engine.messages
        )

        await ctx.output_rich(
            "[bold]Session Insights[/bold]\n\n"
            f"  Messages: {msg_count}\n"
            f"  User messages: {user_msgs}\n"
            f"  Est. tokens: ~{total_chars // 4:,}\n\n"
            "[dim]Full insights dashboard (historical sessions, "
            "facet analysis, HTML reports) requires SessionStorage "
            "(Phase 10).[/dim]"
        )
```

### Task 2: 注册到 CascadeApp

**文件:** 修改 `src/cascade/ui/textual_app.py`

```python
        from cascade.commands.advanced.plugin import PluginCommand
        from cascade.commands.advanced.skills import SkillsCommand
        from cascade.commands.advanced.model import ModelCommand
        from cascade.commands.advanced.cost import CostCommand
        from cascade.commands.advanced.effort import EffortCommand
        from cascade.commands.advanced.insights import InsightsCommand
        self.router.register(PluginCommand())
        self.router.register(SkillsCommand())
        self.router.register(ModelCommand())
        self.router.register(CostCommand())
        self.router.register(EffortCommand())
        self.router.register(InsightsCommand())
```

### Task 3: 验证 + 手动测试

```bash
cascade
# /model                → 显示当前 provider + model
# /model claude-3.5-sonnet → 切换模型
# /cost                 → 显示估算费用
# /effort               → 列出 5 个级别 + 当前选择
# /effort high          → 切换到 high
# /skills               → 分类列出所有 slash commands
# /plugin               → 显示 future release 提示
# /plugins              → 同上（别名）
# /insights             → 显示基础 session 统计
# /help                 → Advanced 分组含 6 个命令
```

---

## L1~L4 验收标准

| Level | 检查项 | 标准 |
|-------|--------|------|
| L1 | `commands/advanced/` 含 7 个 .py 文件 | `ls` 确认 |
| L2 | 每个命令 docstring 标注 Claude Code 参考路径和文件大小 | `grep -r "Reference:" src/cascade/commands/advanced/` |
| L3 | `/model` 显示当前模型；`/cost` 输出估算费用；`/effort` 可 toggle | 手动验证 |
| L4 | `/plugins` 别名触发 `/plugin`；`/skills` 按 category 分组 | 手动测试 |

---

## 与 Claude Code 的差异汇总

| 命令 | Claude Code | Cascade | 差异原因 |
|------|-------------|---------|---------|
| `/plugin` | 17 个文件 ~830KB，完整 marketplace + 插件管理 JSX | Stub | 无 plugin/marketplace 系统 |
| `/skills` | 8 行 → `SkillsMenu` JSX | 文本列表分组显示 | 无 JSX |
| `/model` | 17 行 + 37KB `model.tsx` JSX 选择器 | 文本显示 + `/model <name>` 参数 | 无 JSX 选择器 |
| `/cost` | 25 行 `formatTotalCost()` + 订阅状态 | token 估算 × 公开定价 | 无 `cost-tracker` |
| `/effort` | 14 行 + 22KB `effort.tsx` JSX slider | 文本选择 5 级 | 无 JSX slider |
| `/insights` | **3,201 行**，Opus facet extraction + HTML 报告 + homespace 收集 | Stub + 基础统计 | 无 SessionStorage + 无 LLM 分析 |

---

## Phase 9 完整统计

| Batch | 文件 | 命令数 | 命令列表 |
|-------|------|--------|---------|
| 9.1 | Session | 6 | `/compact`, `/resume`, `/rename`, `/branch`, `/rewind`, `/export` |
| 9.2 | Setup | 5 | `/version`, `/config`, `/doctor`, `/init`, `/env` |
| 9.3 | UI | 4 | `/theme`, `/brief`, `/btw`, `/shortcuts` |
| 9.3.5 | Workflow | 3 | `/copy`, `/diff`, `/status` |
| 9.4 | Tools | 5 | `/permissions`, `/hooks`, `/debug-tool-call`, `/sandbox`, `/tools` |
| 9.4.5 | Auto | 1 | `/auto` |
| 9.5 | Git | 5 | `/commit`, `/commit-push-pr`, `/pr-comments`, `/review`, `/security-review` |
| 9.6 | Memory | 2 | `/memory`, `/context` |
| 9.7 | Advanced | 6 | `/plugin`, `/skills`, `/model`, `/cost`, `/effort`, `/insights` |
| **合计** | | **37** | |
