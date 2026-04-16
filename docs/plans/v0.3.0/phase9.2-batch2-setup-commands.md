# Phase 9.2: Batch 2 — 设置与诊断命令 (5 commands)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 实现 `/version`, `/config`, `/doctor`, `/init`, `/env` 五个设置与诊断命令。

**架构:** `BaseCommand` + `CommandContext`，新建 `commands/setup/` 子包。

**前置条件:** Phase 9.1 (Batch 1) 完成。

---

## 📊 命令总览

| 命令 | Claude Code 参考源码 | Cascade 实现级别 | 架构限制 |
|------|---------------------|-----------------|---------|
| `/version` | `src/commands/version.ts` (23行) | ✅ 完整实现 | 无 |
| `/config` | `src/commands/config/` — `index.ts` (alias `settings`) + `config.tsx` (打开 Settings 面板) | ✅ 完整实现（文本输出版） | 无 JSX Settings 面板，用文本列表替代 |
| `/doctor` | `src/commands/doctor/` — `index.ts` + `doctor.tsx` (加载 `screens/Doctor.js`) | ✅ 完整实现 + HEP 扩展 | 无 |
| `/init` | `src/commands/init.ts` (257行，`type: 'prompt'`) | ⚠️ 简化版 | Claude Code 用 8 阶段 prompt 驱动 LLM 生成；Cascade 写静态模板 |
| `/env` | `src/commands/env/index.js` (已禁用的 stub) | ✅ Cascade 原创实现 | Claude Code 实际已禁用此命令 (`isEnabled: false`) |

---

## Claude Code 源码参考详情

### `/version` 参考分析

**源码:** [version.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/version.ts) — 23行
- `type: 'local'`，内部只读 `MACRO.VERSION` 和 `MACRO.BUILD_TIME`
- `isEnabled: () => process.env.USER_TYPE === 'ant'`（仅 Anthropic 内部可见）
- `supportsNonInteractive: true`

**Cascade 适配:** 直接从 `banner.py` 读 `VERSION` 常量，无限制。

### `/config` 参考分析

**源码:** [config/index.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/config/index.ts) — 12行
- `aliases: ['settings']`
- `type: 'local-jsx'`，加载 `Settings` JSX 组件（`defaultTab="Config"`）

**源码:** [config/config.tsx](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/config/config.tsx) — 7行
- 直接渲染 `<Settings onClose={onDone} context={context} defaultTab="Config" />`
- `Settings` 组件是一个多 Tab 面板（Config / Status / Stats 等）

**Cascade 适配:** Textual 没有 Settings 面板组件。用 Rich markup 文本列表展示当前配置，包括 Provider、Model、Tools、Permissions。

### `/doctor` 参考分析

**源码:** [doctor/index.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/doctor/index.ts) — 13行
- `type: 'local-jsx'`，`isEnabled: () => !isEnvTruthy(process.env.DISABLE_DOCTOR_COMMAND)`

**源码:** [doctor/doctor.tsx](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/doctor/doctor.tsx) — 7行（入口）
- 加载 `screens/Doctor.js`（JSX 全屏诊断界面）
- 实际 Doctor 组件检查：Node.js 版本、git、API key、npm 版本、网络连通性

**Cascade 适配:** 完全重写 Python 版，增加 HEP 领域特有检查：
- `voms-proxy-info --timeleft`（Grid Proxy 证书）
- `CMSSW_BASE`（CMS 软件框架）
- `SCRAM_ARCH`（编译架构）

### `/init` 参考分析

**源码:** [init.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/init.ts) — 257行
- `type: 'prompt'`（最复杂的命令类型——注入 prompt 让 LLM 执行）
- 包含 `OLD_INIT_PROMPT`（简单版）和 `NEW_INIT_PROMPT`（8 阶段版）
- 8 阶段工作流：问用户 → 扫描代码库 → 提问填补空白 → 写 CLAUDE.md → 写 CLAUDE.local.md → 创建 skills → 建议优化 → 总结
- 使用 `AskUserQuestion` 工具进行多轮交互
- 依赖 `projectOnboardingState`、`envUtils`

**Cascade 适配:** Cascade 没有 `type: 'prompt'` 命令模式。简化为写静态 `CASCADE.md` 模板文件（含 HEP 特有字段），未来升级为 LLM 驱动的代码库分析。

### `/env` 参考分析

**源码:** [env/index.js](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/env/index.js) — 2行
- `isEnabled: () => false, isHidden: true, name: 'stub'`
- **Claude Code 实际已禁用此命令！** 只是一个隐藏的 stub。

**Cascade 适配:** Cascade 原创实现——显示 `CASCADE_*` 环境变量 + HEP 特有变量（`SCRAM_ARCH`, `CMSSW_BASE`, `X509_USER_PROXY`）。这是 Cascade 差异化的地方。

---

## 实施步骤

### Task 1: 创建 setup 子包

**文件:**
- 创建: `src/cascade/commands/setup/__init__.py`
- 创建: `src/cascade/commands/setup/version.py`
- 创建: `src/cascade/commands/setup/config.py`
- 创建: `src/cascade/commands/setup/doctor.py`
- 创建: `src/cascade/commands/setup/init_project.py`
- 创建: `src/cascade/commands/setup/env.py`

#### `/version`

```python
# src/cascade/commands/setup/version.py
from cascade.commands.base import BaseCommand, CommandContext


class VersionCommand(BaseCommand):
    """Show Cascade version.

    Reference: claude-code src/commands/version.ts (23 lines)
    Claude Code impl: reads MACRO.VERSION + MACRO.BUILD_TIME,
    only visible to Anthropic internal users (USER_TYPE === 'ant').
    Cascade impl: reads VERSION from banner.py, always visible.
    """
    name = "version"
    description = "Show Cascade version"
    category = "Setup"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        from cascade.ui.banner import VERSION
        await ctx.output_rich(f"[bold #5fd7ff]Cascade[/bold #5fd7ff] v{VERSION}")
```

#### `/config`

```python
# src/cascade/commands/setup/config.py
from cascade.commands.base import BaseCommand, CommandContext


class ConfigCommand(BaseCommand):
    """View Cascade configuration.

    Reference: claude-code src/commands/config/config.tsx (7 lines)
    Claude Code impl: opens <Settings> JSX panel with defaultTab="Config".
    aliases: ['settings']. The Settings component has multi-tab UI
    (Config / Status / Stats tabs).
    Cascade impl: text-based config display (no JSX panel).
    """
    name = "config"
    description = "View Cascade configuration"
    aliases = ["/settings"]
    category = "Setup"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        lines = [
            "[bold]Cascade Config[/bold]\n",
            f"  Provider: [#0087ff]{ctx.engine.client.provider}[/#0087ff]",
            f"  Model:    [bold]{ctx.engine.client.model_name}[/bold]",
        ]
        if ctx.engine.registry:
            tool_count = len(ctx.engine.registry.list_tools())
            lines.append(f"  Tools:    {tool_count} registered")
        if ctx.engine.permissions:
            lines.append(f"  Perms:    {ctx.engine.permissions.mode.value}")
        await ctx.output_rich("\n".join(lines))
```

#### `/doctor`

```python
# src/cascade/commands/setup/doctor.py
from cascade.commands.base import BaseCommand, CommandContext
import subprocess
import shutil
import os


class DoctorCommand(BaseCommand):
    """Run health diagnostics (HEP-aware).

    Reference: claude-code src/commands/doctor/doctor.tsx (7 lines, entry)
    Claude Code impl: loads screens/Doctor.js JSX component with
    full-screen diagnostic UI. Checks: Node version, git, API keys,
    npm, network connectivity.
    isEnabled: () => !isEnvTruthy(DISABLE_DOCTOR_COMMAND)
    Cascade impl: Python text-based diagnostics with HEP-specific
    checks (grid proxy, CMSSW, SCRAM_ARCH) not present in Claude Code.
    """
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

        # HEP-specific checks (only on cluster-like environments)
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
            return ("Grid Proxy", ok,
                    f"{timeleft}s remaining" if ok else "expired or missing")
        except Exception:
            return ("Grid Proxy", False, "voms-proxy-info not available")

    def _check_cmssw(self):
        base = os.getenv("CMSSW_BASE", "")
        return ("CMSSW", bool(base), base or "not set")
```

#### `/init`

```python
# src/cascade/commands/setup/init_project.py
from cascade.commands.base import BaseCommand, CommandContext
import os


class InitCommand(BaseCommand):
    """Initialize project with CASCADE.md.

    Reference: claude-code src/commands/init.ts (257 lines)
    Claude Code impl: type='prompt', injects a massive prompt (OLD_INIT_PROMPT
    or NEW_INIT_PROMPT with 8-phase workflow) that drives the LLM to analyze
    the codebase and generate CLAUDE.md, CLAUDE.local.md, skills, and hooks.
    Uses AskUserQuestion tool for multi-turn interaction.
    Cascade impl: simplified — writes a static CASCADE.md template with
    HEP-specific fields. Full LLM-driven init requires 'prompt' command
    type which Cascade doesn't support yet (Phase 10+).
    """
    name = "init"
    description = "Initialize project with CASCADE.md"
    category = "Setup"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        cascade_md = os.path.join(os.getcwd(), "CASCADE.md")
        if os.path.exists(cascade_md):
            await ctx.output_rich(
                f"[dim]CASCADE.md already exists at {cascade_md}[/dim]"
            )
            return

        template = (
            "# CASCADE.md\n\n"
            "This file provides guidance to Cascade when working "
            "with code in this repository.\n\n"
            "## Key Decisions\n\n"
            "## Architecture Notes\n\n"
            "## Build & Test Commands\n\n"
            "## HEP Analysis Config\n\n"
            "- Cluster: lxplus / local\n"
            "- CMSSW version: \n"
            "- Dataset: \n"
            "- Analysis framework: \n"
        )
        with open(cascade_md, "w") as f:
            f.write(template)
        await ctx.output_rich(
            f"[#00d7af]Created {cascade_md}[/#00d7af]\n"
            f"[dim]Edit this file to customize Cascade's behavior.[/dim]"
        )
```

#### `/env`

```python
# src/cascade/commands/setup/env.py
from cascade.commands.base import BaseCommand, CommandContext
import os


class EnvCommand(BaseCommand):
    """Show environment variables relevant to Cascade.

    Reference: claude-code src/commands/env/index.js (2 lines)
    Claude Code impl: DISABLED stub — isEnabled: () => false, isHidden: true.
    The command exists in the codebase but is never shown to users.
    Cascade impl: ORIGINAL implementation showing CASCADE_* env vars
    and HEP-specific variables (SCRAM_ARCH, CMSSW_BASE, X509_USER_PROXY).
    This is a Cascade differentiator — Claude Code doesn't offer this.
    """
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

### Task 2: 创建 `__init__.py`

```python
# src/cascade/commands/setup/__init__.py
```
（空文件）

### Task 3: 注册到 CascadeApp

**文件:** 修改 `src/cascade/ui/textual_app.py`

在 Batch 1 注册之后添加:
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

### Task 4: 验证

```bash
cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade && source .venv/bin/activate
python -c "from cascade.ui.textual_app import CascadeApp; print('OK')"
```

### Task 5: 手动测试

```bash
cascade
# /version    → v0.2.x
# /config     → Provider + Model + Tools 列表
# /settings   → 同上（别名）
# /doctor     → 所有检查项 ✓/✗
# /init       → 在 cwd 创建 CASCADE.md (如果不存在)
# /env        → CASCADE_* 和 HEP 变量
# /help       → Setup 分组应含 5 个命令
```

---

## L1~L4 验收标准

| Level | 检查项 | 标准 |
|-------|--------|------|
| L1 存在性 | `commands/setup/` 目录含 6 个 .py 文件 | `ls` 确认 |
| L2 结构性 | 每个命令继承 `BaseCommand`，有 docstring 标注 Claude Code 参考路径 | `grep -r "Reference: claude-code" src/cascade/commands/setup/` |
| L3 内容性 | `/doctor` 在 HEP 环境显示 Grid Proxy 和 CMSSW；`/init` 创建包含 HEP 字段的 `CASCADE.md` | 手动验证 |
| L4 功能性 | `/settings` 别名正确触发 `/config`；`/help` 的 Setup 分组含 5 个命令 | 手动测试 |

---

## 与 Claude Code 的差异汇总

| 命令 | Claude Code | Cascade | 差异原因 |
|------|-------------|---------|---------|
| `/version` | 仅内部可见 (`USER_TYPE=ant`) | 始终可见 | Cascade 不区分内外部用户 |
| `/config` | JSX Settings 多 Tab 面板 | Rich 文本列表 | Textual ≠ Ink/React JSX |
| `/doctor` | 通用 JS 环境检查 | +HEP 检查 (grid proxy, CMSSW) | Cascade 面向 HEP 物理学家 |
| `/init` | 257 行 prompt 驱动 LLM 8 阶段工作流 | 静态模板写入 | 无 `type: 'prompt'` 命令支持 |
| `/env` | **已禁用** (`isEnabled: false`) | 完整实现，HEP 变量 | Cascade 原创差异化功能 |
