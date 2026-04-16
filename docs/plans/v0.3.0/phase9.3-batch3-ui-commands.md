# Phase 9.3: Batch 3 — UI 与交互命令 (3 commands)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 实现 `/theme`, `/btw`, `/shortcuts` 三个 UI 交互命令。

> [!WARNING]
> **`/brief` 已移除。** 审查 Claude Code 源码后发现：`/brief` 的真实功能是切换模型输出管道
> （从纯文本 → 必须使用 `SendUserMessage` 工具），依赖 Kairos/BriefTool 基建。
> Cascade 没有这套基建且不计划实现。简单的 system prompt 注入过于 trivial，不值得单独命令。
> 如果已实现，需要删除 `src/cascade/commands/ui/brief.py` 并从 `textual_app.py` 取消注册。

**架构:** `BaseCommand` + `CommandContext`，新建 `commands/ui/` 子包。

**前置条件:** Phase 9.2 (Batch 2) 完成。

---

## 📊 命令总览

| 命令 | Claude Code 参考源码 | Cascade 实现级别 | 架构限制 |
|------|---------------------|-----------------|---------|
| `/theme` | `src/commands/theme/` — `index.ts` + `theme.tsx` (57行，`ThemePicker` JSX) | ✅ 文本选择版 | 无 `ThemePicker` JSX 组件，用文本列表替代 |
| ~~`/brief`~~ | ~~`src/commands/brief.ts` (131行，Kairos/GrowthBook/analytics)~~ | ❌ **已移除** | 依赖 Kairos/BriefTool 输出路由，Cascade 无此基建 |
| `/btw` | `src/commands/btw/` — `index.ts` + `btw.tsx` (243行，`BtwSideQuestion` JSX) | ⚠️ 简化版 | 无 side question fork/cache 系统 |
| `/shortcuts` | `src/commands/keybindings/` — `index.ts` + `keybindings.ts` (54行) | ✅ Cascade 原创 | Claude Code 的 `/keybindings` 是打开配置文件编辑器；Cascade 改为显示快捷键列表 |

> [!NOTE]
> `/shortcuts` 是 Review Report 建议新增的 P1 命令。Claude Code 有 `/keybindings` 命令但功能不同（打开编辑器编辑 keybindings 配置文件）。Cascade 的 `/shortcuts` 参考 Gemini CLI 的 `/shortcuts`（显示快捷键列表），更适合 Textual TUI 用户。

---

## Claude Code 源码参考详情

### `/theme` 参考分析

**源码:** [theme/index.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/theme/index.ts) — 11行
- `type: 'local-jsx'`

**源码:** [theme/theme.tsx](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/theme/theme.tsx) — 57行
- 渲染 `<ThemePicker>` JSX 组件（从 `components/ThemePicker.js` 导入）
- 用户选择主题后调用 `setTheme(setting)` + `onDone("Theme set to ...")`
- 支持 Esc 取消
- 依赖 `useTheme()` hook（Ink 框架的主题系统）

**Cascade 适配:** Textual 有自己的主题系统但 Cascade 暂未集成。改为预定义主题色板 + 文本列出 + 未来接入 Textual CSS 变量。

### `/brief` 参考分析

**源码:** [brief.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/brief.ts) — 131行
- `type: 'local-jsx'`，`immediate: true`
- `isEnabled()` 检查 Kairos feature flag + GrowthBook `tengu_kairos_brief_config`
- toggle `isBriefOnly` 状态：开启后模型必须使用 `BriefTool` 输出
- 注入 `<system-reminder>` meta message 确保模型行为切换
- 级联影响：`setUserMsgOptIn(newState)` 控制工具可用性
- analytics: `logEvent('tengu_brief_mode_toggled', ...)`

**Cascade 适配:** 剥离所有 Kairos/GrowthBook/analytics 依赖。核心逻辑简化为 toggle 一个 `_brief_mode` boolean，通过 `ctx.repl` 属性传递给 TUI。

### `/btw` 参考分析

**源码:** [btw/index.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/btw/index.ts) — 14行
- `type: 'local-jsx'`，`immediate: true`，`argumentHint: '<question>'`

**源码:** [btw/btw.tsx](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/btw/btw.tsx) — 243行
- 渲染 `<BtwSideQuestion>` JSX 组件
- 核心：`runSideQuestion()` — 在独立 fork 中向 LLM 发送 side question
- `buildCacheSafeParams()` — 复用主线程的 cache params 保证 prompt cache hit
- 用户输出: Markdown 渲染 + ScrollBox + Spinner 动画
- 键盘交互: ↑↓ 滚动，Esc/Enter/Space 关闭
- analytics: `saveGlobalConfig` 记录 `btwUseCount`

**Cascade 适配:** Cascade 没有 side question fork 系统。简化为将用户的 aside 注入到 `engine.messages` 中作为上下文补充（不触发独立 LLM 调用）。

### `/shortcuts` 参考分析（对标 Claude Code `/keybindings` + Gemini `/shortcuts`）

**Claude Code 源码:** [keybindings/index.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/keybindings/index.ts) — 14行
- `name: 'keybindings'`，`type: 'local'`
- `isEnabled: () => isKeybindingCustomizationEnabled()`（preview feature）

**Claude Code 源码:** [keybindings/keybindings.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/commands/keybindings/keybindings.ts) — 54行
- 功能：创建/打开 keybindings 配置文件（`generateKeybindingsTemplate()` + `editFileInEditor()`）
- 不是"显示快捷键列表"，而是"编辑快捷键配置"

**Cascade 适配:** 功能重新定义。参考 Gemini CLI 的 `/shortcuts` 命令，显示 Cascade Textual TUI 中所有可用的键盘快捷键列表。这是 Cascade 原创功能。

---

## 实施步骤

### Task 0: 重构 `styles.py` — 多主题支持

> [!IMPORTANT]
> **这是本 Batch 的核心改动。** 将 `styles.py` 从单一硬编码 TCSS 字符串重构为多主题系统。
> `/theme` 命令调用 Textual 的 `app.stylesheet` API 实现运行时主题切换。

**文件:** 修改 `src/cascade/ui/styles.py`

**设计参考:**
- Gemini CLI `theme-manager.ts` (662 行) — 主题注册、激活、终端背景适配
- Gemini CLI `theme.ts` (693 行) — `ColorsTheme` 语义色板定义
- CMS Logo 配色：蓝 `#005EB8`、金 `#F5A623`、红 `#D32F2F`

**改动说明:**
1. 提取颜色常量为 `ThemeColors` dataclass
2. 用 f-string 模板生成 TCSS（颜色参数化）
3. 导出 `THEMES: dict[str, ThemeColors]` 和 `get_tcss(theme_name) -> str`

```python
# src/cascade/ui/styles.py
"""TCSS themes for Cascade Textual TUI.

Design reference:
- Gemini CLI theme-manager.ts (662 lines): ThemeManager singleton, 17 built-in themes
- Gemini CLI theme.ts (693 lines): ColorsTheme with semantic color tokens
- CMS Logo colors: blue #005EB8, gold #F5A623, red #D32F2F
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ThemeColors:
    """Semantic color tokens for a Cascade theme."""
    name: str
    description: str
    bg_primary: str       # Main background
    bg_secondary: str     # Input area, footer, message boxes
    bg_tertiary: str      # Prompt container
    fg_primary: str       # Main text
    fg_secondary: str     # Placeholder, help text
    accent: str           # Brand color (banner, focus, scrollbar)
    border: str           # Borders, separators
    tool_color: str       # Tool call label
    error_color: str      # Error highlights
    msg_border: str       # Message area border


# ── Theme Definitions ──

THEME_DARK = ThemeColors(
    name="dark",
    description="Default dark (GitHub Dark)",
    bg_primary="#0d1117",
    bg_secondary="#161b22",
    bg_tertiary="#1c2128",
    fg_primary="#c9d1d9",
    fg_secondary="#484f58",
    accent="#5fd7ff",
    border="#30363d",
    tool_color="#ff8700",
    error_color="#ff5f5f",
    msg_border="#484f58",
)

THEME_LIGHT = ThemeColors(
    name="light",
    description="Clean light",
    bg_primary="#ffffff",
    bg_secondary="#f6f8fa",
    bg_tertiary="#eef1f5",
    fg_primary="#24292f",
    fg_secondary="#6e7781",
    accent="#0969da",
    border="#d0d7de",
    tool_color="#bf5700",
    error_color="#cf222e",
    msg_border="#afb8c1",
)

THEME_CMS = ThemeColors(
    name="cms",
    description="CMS experiment (blue & gold)",
    bg_primary="#0a1628",
    bg_secondary="#112240",
    bg_tertiary="#1a3358",
    fg_primary="#e2e8f0",
    fg_secondary="#7b8dad",
    accent="#005EB8",        # CMS blue
    border="#1e3a5f",
    tool_color="#F5A623",    # CMS gold
    error_color="#D32F2F",   # CMS red
    msg_border="#2a5082",
)


THEMES: dict[str, ThemeColors] = {
    "dark": THEME_DARK,
    "light": THEME_LIGHT,
    "cms": THEME_CMS,
}

DEFAULT_THEME = "dark"


def build_tcss(c: ThemeColors) -> str:
    """Generate Textual CSS string from a ThemeColors palette."""
    return f"""
Screen {{
    background: {c.bg_primary};
    layout: vertical;
}}

/* ── Banner (ASCII art) ── */

#banner {{
    background: {c.bg_primary};
    color: {c.accent};
    padding: 0 0;
    height: auto;
}}

/* ── Status bar (model + path) ── */

#status-bar {{
    height: auto;
    width: auto;
    background: {c.bg_primary};
    color: {c.fg_primary};
    padding: 0 1;
    margin: 1 1 0 1;
    border: round #555555;
}}

#help-text {{
    height: 1;
    background: {c.bg_primary};
    color: {c.fg_secondary};
    margin: 0 1 1 1;
}}

/* ── Prompt Container ── */

#input-section {{
    height: auto;
    padding-bottom: 0;
}}

#prompt-container {{
    height: auto;
    min-height: 1;
    width: 1fr;
    layout: horizontal;
    align: left middle;
    margin: 1 0 0 0;
    padding: 0 1;
    background: {c.bg_tertiary};
    border-top: inner {c.bg_tertiary};
    border-bottom: inner {c.bg_tertiary};
    border-left: none;
    border-right: none;
    layers: base surface overlay;
}}

#prompt-label {{
    height: 1;
    width: 2;
    background: transparent;
    layer: surface;
}}

#prompt-input {{
    layer: surface;
    width: 1fr;
    background: transparent;
}}

#prompt-input .text-area--cursor-line {{
    background: transparent;
}}

#prompt-placeholder {{
    content-align: left middle;
    height: 1;
    color: {c.fg_secondary};
    background: transparent;
    layer: overlay;
    position: absolute;
    offset: 2 0;
}}

/* ── Chat history scroll container ── */

#chat-history {{
    background: {c.bg_primary};
    height: 1fr;
    scrollbar-background: {c.bg_primary};
    scrollbar-color: {c.border};
    scrollbar-color-hover: {c.accent};
    scrollbar-color-active: {c.accent};
}}

/* ── Message labels ── */

.ai-label {{
    height: 1;
    background: {c.bg_primary};
    color: {c.accent};
    padding: 0 1;
    margin-top: 1;
    text-style: bold;
}}

.tool-label {{
    height: 1;
    background: {c.bg_primary};
    color: {c.tool_color};
    padding: 0 1;
    margin-top: 1;
}}

/* ── Message TextAreas ── */

.message-area {{
    background: {c.bg_secondary};
    color: {c.fg_primary};
    border: round {c.border};
    margin: 0 1;
    padding: 0 1;
    min-height: 3;
    height: auto;
    overflow: hidden hidden;
    scrollbar-size: 0 0;
}}

.message-area:focus {{
    border: round {c.accent};
}}

.user-msg-box {{
    width: auto;
    min-width: 10;
    max-width: 100%;
    height: auto;
    background: {c.bg_primary};
    color: {c.fg_primary};
    border: round {c.accent};
    border-title-color: {c.accent};
    padding: 0 1;
    margin: 0 1;
}}

.ai-msg {{
    border: round {c.msg_border};
    background: {c.bg_primary};
    margin: 0 1;
    padding: 0 1;
}}

.tool-msg {{
    border: round {c.tool_color};
}}

.tool-msg-error {{
    border: round {c.error_color};
}}

.system-msg {{
    background: {c.bg_primary};
    color: {c.fg_secondary};
    border: none;
    margin: 0 1;
    min-height: 1;
    height: auto;
}}

/* ── Spinner ── */

.spinner {{
    height: 1;
    background: {c.bg_primary};
    padding: 0 1;
    margin: 0 1;
}}

/* ── Input ── */

#prompt-input {{
    height: auto;
    max-height: 15;
    width: 1fr;
    background: transparent;
    padding: 0 0;
    margin: 0 0;
    border: none;
}}

#prompt-input:focus {{
    border: none;
}}

PromptInput > .text-area--cursor-line {{
    background: transparent;
}}

Input {{
    background: {c.bg_primary};
    color: {c.fg_primary};
    border: none;
    padding: 0 0;
    height: 1;
}}

Input:focus {{
    border: none;
}}

/* ── Footer bar (model) ── */

#footer-bar {{
    height: 1;
    dock: bottom;
    background: {c.bg_secondary};
    color: {c.fg_secondary};
    padding: 0 1;
}}

/* ── Rich markup messages ── */

.rich-msg {{
    background: {c.bg_primary};
    color: {c.fg_primary};
    padding: 0 1;
    margin: 0 1;
    height: auto;
}}

/* ── Command palette items ── */

.palette-item {{
    height: 1;
    background: transparent;
    padding: 0 1;
    margin: 0;
    width: 100%;
}}

.palette-item.active {{
    background: {c.accent};
}}

/* ── Notifications / Toast ── */
Toast {{
    width: auto;
    min-width: 20;
    max-width: 50;
    padding: 0 1;
    margin: 0 1 1 0;
    background: {c.bg_secondary};
    color: {c.fg_primary};
    border-left: tall {c.accent};
}}

Toast.-information {{
    border-left: tall {c.accent};
}}

Toast > .toast--title {{
    color: {c.accent};
    text-style: bold;
}}
Toast.-information > .toast--title {{
    color: {c.accent};
}}
"""


def get_tcss(theme_name: str | None = None) -> str:
    """Return TCSS string for the given theme name (default: dark)."""
    name = theme_name or DEFAULT_THEME
    colors = THEMES.get(name, THEMES[DEFAULT_THEME])
    return build_tcss(colors)


# Backward compat: existing code imports CASCADE_TCSS
CASCADE_TCSS = get_tcss("dark")
```

**关键要点:**
- `CASCADE_TCSS` 保持向后兼容，现有代码不需要改动即可运行
- `get_tcss(name)` 是新入口，`/theme` 命令通过它获取新主题 CSS
- `ThemeColors` 是 frozen dataclass，确保主题定义不可变

### Task 1: 创建 UI 命令子包

**文件:**
- 创建: `src/cascade/commands/ui/__init__.py`
- 创建: `src/cascade/commands/ui/theme.py`
- 创建: `src/cascade/commands/ui/brief.py`
- 创建: `src/cascade/commands/ui/btw.py`
- 创建: `src/cascade/commands/ui/shortcuts.py`

#### `/theme` — 运行时主题切换（完整实现）

```python
# src/cascade/commands/ui/theme.py
from cascade.commands.base import BaseCommand, CommandContext
from cascade.ui.styles import THEMES, get_tcss, DEFAULT_THEME


class ThemeCommand(BaseCommand):
    """Switch color theme with live preview.

    Reference: claude-code src/commands/theme/theme.tsx (57 lines)
    Claude Code impl: renders <ThemePicker> JSX component using Ink's
    useTheme() hook. User selects from interactive picker, theme applied
    instantly via setTheme(setting).

    Also ref: Gemini CLI theme-manager.ts (662 lines) — ThemeManager
    singleton with 17 built-in themes (Dracula, Solarized, Tokyo Night,
    GitHub, etc.), custom JSON file loading, terminal background detection.

    Cascade impl: 3 built-in themes (dark, light, cms). Theme switch is
    instant — regenerates TCSS from ThemeColors palette and applies via
    Textual's stylesheet.source + refresh_css(). No ThemePicker JSX,
    no terminal background detection.
    """
    name = "theme"
    description = "Switch color theme"
    category = "UI"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        arg = args.strip().lower()

        if arg and arg in THEMES:
            # Apply theme: regenerate TCSS and hot-reload
            new_css = get_tcss(arg)
            app = ctx.repl  # The CascadeApp instance
            app.stylesheet.source = new_css
            app.refresh_css()
            app._current_theme = arg

            t = THEMES[arg]
            await ctx.output_rich(
                f"[{t.accent}]■[/{t.accent}] "
                f"[bold]Theme: {t.name}[/bold] — {t.description}"
            )
            return

        if arg and arg not in THEMES:
            await ctx.output_rich(
                f"[red]Unknown theme: {arg}[/red]\n"
                f"[dim]Available: {', '.join(THEMES.keys())}[/dim]"
            )
            return

        # List all themes
        current = getattr(ctx.repl, "_current_theme", DEFAULT_THEME)
        lines = ["[bold]Available Themes[/bold]\n"]
        for name, t in THEMES.items():
            marker = "●" if name == current else "○"
            color = t.accent if name == current else "dim"
            lines.append(
                f"  [{color}]{marker}[/{color}] "
                f"[{t.accent}]■[/{t.accent}] "
                f"[bold]{name}[/bold] — [dim]{t.description}[/dim]"
            )
        lines.append(f"\n[dim]Usage: /theme <{'|'.join(THEMES.keys())}>[/dim]")
        await ctx.output_rich("\n".join(lines))
```

> [!IMPORTANT]
> **运行时切换机制：** `app.stylesheet.source = new_css` + `app.refresh_css()`。
> 这是 Textual 的官方 API，会立即重新解析 CSS 并重绘所有 widget。
> 如果 Textual 版本不支持 `stylesheet.source` 直接赋值，回退方案是
> `app.css = new_css`（Textual 0.40+ 支持）。

#### `/brief`

```python
# src/cascade/commands/ui/brief.py
from cascade.commands.base import BaseCommand, CommandContext


class BriefCommand(BaseCommand):
    """Toggle concise output mode.

    Reference: claude-code src/commands/brief.ts (131 lines)
    Claude Code impl: toggles isBriefOnly state, controlled by Kairos
    feature flag + GrowthBook config. When on, model must use BriefTool
    for all output. Injects <system-reminder> meta messages. Tracks
    analytics via logEvent('tengu_brief_mode_toggled').
    Cascade impl: simplified toggle of _brief_mode boolean on repl.
    No Kairos, no GrowthBook, no analytics, no BriefTool integration.
    """
    name = "brief"
    description = "Toggle concise output mode"
    category = "UI"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        current = getattr(ctx.repl, "_brief_mode", False)
        ctx.repl._brief_mode = not current
        state = "ON" if ctx.repl._brief_mode else "OFF"
        await ctx.output_rich(f"[#00d7af]Brief mode: {state}[/#00d7af]")
```

#### `/btw`

```python
# src/cascade/commands/ui/btw.py
from cascade.commands.base import BaseCommand, CommandContext


class BtwCommand(BaseCommand):
    """Inject a quick aside into the conversation.

    Reference: claude-code src/commands/btw/btw.tsx (243 lines)
    Claude Code impl: renders <BtwSideQuestion> JSX component that
    forks a side question to the LLM via runSideQuestion() with
    cache-safe params. Shows Markdown response in ScrollBox with
    Spinner animation. Supports keyboard scrolling (↑↓) and dismiss
    (Esc/Enter/Space). Tracks btwUseCount in global config.
    Cascade impl: simplified — injects the aside as a user message
    into engine.messages context. Does NOT trigger a separate LLM
    call (no side question fork system). The aside provides context
    for the next model turn.
    """
    name = "btw"
    description = "Inject a quick aside into the conversation"
    category = "UI"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        if not args.strip():
            await ctx.output_rich(
                "[dim]Usage: /btw <your note to the model>[/dim]"
            )
            return
        note = f"[User aside]: {args.strip()}"
        ctx.engine.messages.append({"role": "user", "content": note})
        await ctx.output_rich(
            f"[dim italic]Noted: {args.strip()}[/dim italic]"
        )
```

#### `/shortcuts` — 新增命令

```python
# src/cascade/commands/ui/shortcuts.py
from cascade.commands.base import BaseCommand, CommandContext


class ShortcutsCommand(BaseCommand):
    """Display keyboard shortcuts for the Cascade TUI.

    Reference: claude-code src/commands/keybindings/keybindings.ts (54 lines)
    Claude Code impl: name='keybindings', creates/opens keybindings
    config file for editing (generateKeybindingsTemplate + editFileInEditor).
    NOT a shortcuts display — it's a config editor.
    Cascade impl: ORIGINAL design inspired by Gemini CLI's /shortcuts.
    Displays a formatted list of all available keyboard shortcuts in
    the Textual TUI. This is a Cascade differentiator.
    """
    name = "shortcuts"
    description = "Show keyboard shortcuts"
    aliases = ["/keys", "/keybindings"]
    category = "UI"

    SHORTCUTS = [
        ("Navigation", [
            ("↑ / ↓", "Scroll through conversation history"),
            ("Tab", "Cycle input focus"),
            ("Esc", "Cancel current operation / close modal"),
        ]),
        ("Editing", [
            ("Enter", "Send message"),
            ("Shift+Enter", "New line in input"),
            ("Ctrl+C", "Cancel streaming response"),
        ]),
        ("Commands", [
            ("/help", "Show all available commands"),
            ("/model", "Switch AI model"),
            ("/compact", "Compress conversation context"),
            ("/export", "Export conversation to file"),
        ]),
        ("Clipboard", [
            ("c", "Copy code block (when focused)"),
            ("Ctrl+Y", "Yank last AI response"),
        ]),
    ]

    async def execute(self, ctx: CommandContext, args: str) -> None:
        lines = ["[bold]Keyboard Shortcuts[/bold]\n"]
        for group_name, shortcuts in self.SHORTCUTS:
            lines.append(f"  [bold #5fd7ff]{group_name}[/bold #5fd7ff]")
            for key, desc in shortcuts:
                lines.append(
                    f"    [bold]{key:<16}[/bold] [dim]{desc}[/dim]"
                )
            lines.append("")
        await ctx.output_rich("\n".join(lines))
```

### Task 2: 创建 `__init__.py`

```python
# src/cascade/commands/ui/__init__.py
```

### Task 3: 注册到 CascadeApp

**文件:** 修改 `src/cascade/ui/textual_app.py`

```python
        from cascade.commands.ui.theme import ThemeCommand
        from cascade.commands.ui.brief import BriefCommand
        from cascade.commands.ui.btw import BtwCommand
        from cascade.commands.ui.shortcuts import ShortcutsCommand
        self.router.register(ThemeCommand())
        self.router.register(BriefCommand())
        self.router.register(BtwCommand())
        self.router.register(ShortcutsCommand())
```

### Task 4: 初始化 CascadeApp 中的 theme 状态

**文件:** 修改 `src/cascade/ui/textual_app.py` — 在 `__init__` 中添加：

```python
        self._current_theme = "dark"
```

### Task 5: 验证

```bash
cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade && source .venv/bin/activate
python -c "from cascade.ui.styles import THEMES, get_tcss; print(list(THEMES.keys())); print(len(get_tcss('cms')))"
python -c "from cascade.ui.textual_app import CascadeApp; print('OK')"
```

### Task 6: 手动测试

```bash
cascade
# /theme           → 列出 3 个主题 (dark ●, light ○, cms ○)
# /theme light     → 整个 TUI 切换为浅色！（白底黑字蓝强调）
# /theme cms       → 切换为 CMS 配色（深蓝底、金色工具标签、CMS 蓝强调）
# /theme dark      → 切回默认暗色
# /theme foobar    → 红色提示 "Unknown theme"
# /brief           → "Brief mode: ON"
# /brief           → "Brief mode: OFF"（再次 toggle）
# /btw remember this is a ttH analysis  → "Noted: ..."
# /shortcuts       → 所有快捷键分组显示
# /keys            → 同上（别名）
# /help            → UI 分组含 4 个命令
```

---

## L1~L4 验收标准

| Level | 检查项 | 标准 |
|-------|--------|------|
| L1 | `commands/ui/` 含 5 个 .py 文件；`styles.py` 导出 `THEMES` dict 含 3 个主题 | `ls` + `python -c "from cascade.ui.styles import THEMES; print(len(THEMES))"` → 3 |
| L2 | 每个命令有 docstring 标注 Claude Code + Gemini CLI 参考路径 | `grep -r "Reference:" src/cascade/commands/ui/` |
| L3 | `/theme light` 立即切换整个 TUI 为浅色配色；`/theme cms` 切换为 CMS 蓝金配色 | 手动验证——背景色、文字色、边框色全部变化 |
| L4 | `/keys` 和 `/keybindings` 别名工作；连续 `/theme dark` → `/theme light` → `/theme dark` 无 CSS 残留 | 手动测试来回切换 3 次 |

---

## CMS 主题配色参考

| Token | 颜色 | 来源 |
|-------|------|------|
| `accent` (CMS Blue) | `#005EB8` | CMS Logo 主色 |
| `tool_color` (CMS Gold) | `#F5A623` | CMS Logo 金色弧线 |
| `error_color` (CMS Red) | `#D32F2F` | CMS Logo 红色粒子轨迹 |
| `bg_primary` | `#0a1628` | 深蓝底——CMS 蓝的暗化版 |
| `bg_secondary` | `#112240` | 次暗蓝 |
| `fg_primary` | `#e2e8f0` | 浅灰白文字 |

---

## 与 Claude Code 的差异汇总

| 命令 | Claude Code | Cascade | 差异原因 |
|------|-------------|---------|---------| 
| `/theme` | JSX `ThemePicker` 交互式选择器 | **3 主题 + 运行时 CSS 热切换** | Textual `refresh_css()` 替代 Ink JSX |
| `/brief` | 131 行，Kairos + GrowthBook + analytics + BriefTool | 6 行，toggle boolean | 无 SaaS 依赖 |
| `/btw` | 243 行，独立 LLM fork + ScrollBox + Spinner | 注入消息到 messages 列表 | 无 side question fork 系统 |
| `/shortcuts` | `/keybindings`：编辑配置文件 | 显示快捷键列表 | 不同的产品定义（参考 Gemini CLI） |
