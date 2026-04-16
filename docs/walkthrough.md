# Cascade v2 Architecture Rewrite — Walkthrough

> 基于 Claude Code 8 层架构的完全重写。每个 Phase 完成后更新此文档。

---

# [v0.2.0] - Foundation & Shell Architecture
*The foundational rewrite establishing the 8-layer architecture, CLI loop, Reactive State, Tool Registry, and UI Streaming.*

---

## Phase 0: Infrastructure & Cleanup ✅
- **Completed:** 2026-04-01
- **Branch:** `refactor/repl-architecture`

### Changes
- **Scaffolded 8-layer directory structure** under `src/cascade/`:
  - `cli/commands/`, `bootstrap/`, `engine/`, `tools/hep/`, `permissions/`, `services/{mcp,memory,remote}/`, `state/`, `types/`
- **Deleted deprecated modules:**
  - `src/cascade/api/` (→ will be replaced by `services/api_client.py`)
  - `src/cascade/core/` (→ will be replaced by `engine/` + `tools/base.py`)
- **Migrated CLI entry:** `src/cascade/cli.py` → `src/cascade/cli/main.py`
- **Updated `pyproject.toml`** entry point to `cascade.cli.main:main`
- **Temporarily commented out** broken import in `ui/app.py` (`cascade.core.agent` → marked `TODO(phase3)`)

### Tests
- `tests/test_architecture.py` — 3 tests PASSED:
  - `test_package_structure_exists`
  - `test_deprecated_dirs_removed`
  - `test_cli_moved`

### Commits
```
12afbd3  chore: scaffold Cascade v2 8-layer directory structure
256427d  refactor: drop deprecated api/core modules and move CLI entry
```

---

## Phase 1: CLI Entry & Bootstrap ✅
- **Completed:** 2026-04-01
- **Branch:** `refactor/repl-architecture`

### Changes
- **Implemented Click CLI Framework:**
  - Added `click` dependency to `pyproject.toml`.
  - Created `src/cascade/cli/main.py` as the main `click.group` entry point.
  - Created initial `chat` subcommand (`src/cascade/cli/commands/chat.py`).
- **Environment Detection Bootstrap:**
  - Added `setup.py` to auto-detect High-Energy Physics environment variables (Python version, ROOT, CMSSW, HTCondor, CWD, platform).
  - Added `system_prompt.py` to build the foundational context payload for the LLM.

### Tests
- `tests/test_cli.py` — 2 tests PASSED (`test_cli_help`, `test_chat_help`)
- `tests/test_bootstrap.py` — 2 tests PASSED (`test_detect_environment`, `test_build_system_prompt`)

### Commits
```
3a756c0  feat(cli): implement Click-based subcommands framework
8cc76fb  feat(bootstrap): HEP environment detection and system prompt builder
```

## Phase 2: Reactive State & API Streaming ✅
- **Completed:** 2026-04-01
- **Branch:** `refactor/repl-architecture`

### Changes
- **Immutable AppState and Reactive Store:**
  - Created `src/cascade/state/app_state.py` containing the `AppState` dataclass.
  - Created `src/cascade/state/store.py` with subscriber logic (`subscribe`/`set_state`/`get_state`).
- **API Streaming Support:**
  - Added `src/cascade/services/api_config.py` with `get_litellm_kwargs` for multi-provider API proxying.
  - Implemented `src/cascade/services/api_client.py` with the asynchronous `ModelClient.stream(...)` generator.

### Tests
- `tests/test_state.py` — 3 tests PASSED (`test_store_get_set`, `test_store_subscribe`, `test_store_unsubscribe`)
- `tests/test_api_client.py` — 1 test PASSED (`test_api_client_stream`)

### Commits
```
555a58f  feat(state): implement immutable AppState and reactive Store
cbf3e34  feat(api): add async stream extraction to ModelClient
```

## Phase 3: Core Query Engine ✅
- **Completed:** 2026-04-01
- **Branch:** `refactor/repl-architecture`

### Changes
- **QueryEngine:** Created `src/cascade/engine/query.py` with:
  - Multi-turn conversation loop maintaining mutable `messages` transcript
  - `set_system_prompt()` for injecting bootstrap context
  - `submit()` async method streaming tokens via `ModelClient.stream()`
  - `_extract_tool_calls()` placeholder for Phase 4 tool dispatch
  - `TurnResult` dataclass capturing output, tool_uses, and stop_reason

### Tests
- `tests/test_query_engine.py` — 3 tests PASSED:
  - `test_query_engine_basic_loop` — token streaming + transcript recording
  - `test_query_engine_system_prompt` — system prompt injection
  - `test_query_engine_multi_turn` — multi-turn conversation memory

### Commits
```
923af5e  feat(engine): implement base QueryEngine loop and TurnResult
```

## Phase 4: Tool System ✅
- **Completed:** 2026-04-01
- **Branch:** `refactor/repl-architecture`

### Changes
- **BaseTool & ToolRegistry:** `src/cascade/tools/base.py` and `registry.py`
  - Abstract `BaseTool` class with `execute()`, `get_input_schema()`, permissions, destructiveness flags
  - `ToolRegistry` for registration, dispatch, and OpenAI-compatible JSON schema generation
- **6 Core Tools implemented:**
  - `BashTool` — shell execution with timeout and exit code tracking
  - `FileReadTool` — read files with optional line range
  - `FileWriteTool` — create/overwrite files
  - `GrepTool` — grep -rnI wrapper with 50-match cap
  - `GlobTool` — glob.glob wrapper with 100-file cap

### Tests
- `tests/test_tools_registry.py` — 4 tests PASSED
- `tests/test_bash_tool.py` — 4 tests PASSED
- `tests/test_file_search_tools.py` — 6 tests PASSED
- **Full suite: 30/30 PASSED**

### Commits
```
022da23  feat(tools): implement typed BaseTool and ToolRegistry
29ae19a  feat(tools): implement robust BashTool with timeouts
4eec946  feat(tools): implement FileRead, FileWrite, Grep, and Glob tools
```

## Phase 5: Permission & Security ✅
- **Completed:** 2026-04-01
- **Branch:** `refactor/repl-architecture`

### Changes
- **PermissionEngine:** Created `src/cascade/permissions/engine.py`
  - Defines `PermissionMode` (`DEFAULT`, `AUTO`, `BYPASS`)
  - Evaluates tool safety (`is_read_only`, `is_destructive`) against the selected mode
  - Integrates an async interactive prompt fallback (`ask_user`) for non-automatic approvals

### Tests
- `tests/test_permissions.py` — 5 tests PASSED (covering all modes and tool types)
- **Full suite: 35/35 PASSED**

### Commits
```
1a99887  feat(permissions): implement mode-based PermissionEngine (Auto/Ask/Bypass)
```

## Phase 6: UI Rendering Integration ✅
- **Completed:** 2026-04-01
- **Branch:** `refactor/repl-architecture`

> **Note:** `renderer.py`, `app.py` (CascadeRepl), and `chat.py` were superseded and deleted in Phase 8.5. The Textual-based `CascadeApp` is now the sole UI entry point.

### Changes
- **MessageRenderer:** Created `src/cascade/ui/renderer.py`
  - Leverages `rich` to render Markdown `Panel` blocks for tool uses and tool results.
  - Implements formatted presentation layers (`render_assistant`, `render_tool_result`).
- **CascadeRepl Application Wire-up:** `src/cascade/ui/app.py`
  - Re-introduced the interactive REPL using `prompt_toolkit`.
  - Instantiates and binds `Provider/ModelClient`, `QueryEngine`, `ToolRegistry`, and `PermissionEngine`.
  - Captures streaming tokens and dynamically visualizes the generation live using `rich.live.Live`.
- **Command Update:** `src/cascade/cli/commands/chat.py`
  - Bootstraps the application via `CascadeRepl`.

### Tests
- `tests/test_renderer.py` — 2 tests PASSED 
- **Full suite: 37/37 PASSED**

### Commits
```
a550d04  feat(ui): implement Rich Markdown renderer for Assistant and Tools
87c15dc  feat(ui): wire up CascadeRepl to use QueryEngine and Streaming
```

---

## Phase 7: Tool Execution Loop ✅
- **Completed:** 2026-04-01
- **Branch:** `feat/phase7-tool-loop`

### Changes
- **Core Engine (`src/cascade/engine/query.py`)**
  - Fully implemented the multi-round agentic loop (up to 10 rounds per query).
  - Added `stream_full()` support to handle tool call JSON chunks alongside text tokens.
  - Implemented the `ask_user` callback injection for interactive tool permission prompts.
- **Provider Integrations (`src/cascade/services/api_config.py` & `.env`)**
  - Standardized multi-provider testing for **ZhipuAI (GLM-4/5)**, **DeepSeek (V3/R1)**, and **Qwen**.
  - Enabled dynamic `CASCADE_DEFAULT_MODEL` detection from `.env` inside `chat.py`.
- **UI Enhancements (`src/cascade/ui/app.py` & `spinner.py`)**
  - Safely managed Async Spinner lifecycle, preventing overlapping ANSI escape code leaks on tool completion.
  - Interactive bash confirmation via `prompt_toolkit`.

### Tests
- `tests/test_integration_tool_loop.py` — Added full end-to-end integration test validating the QueryEngine → ToolRegistry → ModelClient cycle.
- **Full suite: 44/44 PASSED**

### Commits
```
a1e64ff  feat(engine): implement agentic tool execution loop
bc18732  feat(engine): wire PermissionEngine into tool loop
b7edbb7  feat(ui): render tool invocations and results in REPL
1fe0483  test: add e2e integration test for tool loop
a13bdab  fix(api): fix litellm provider config for zhipu
4cf986a  fix(cli): make default model respect .env
380950c  chore: add Qwen/DashScope API key placeholder
972cfae  fix(ui): ensure spinner/live stop on API errors
5cae9a7  feat(permission): implement interactive ask_user callback
02ee741  fix(ui): prevent spinner task leaks and rendering overlaps
```

---

## Phase 8.5: Textual TUI Migration & Slash Commands ✅
- **Completed:** 2026-04-03
- **Branch:** `feat/phase8-slash-commands` (merged from `feat/phase8.5-textual-migration`)

### Changes

#### Textual UI Migration
- **`src/cascade/ui/textual_app.py`** — Main `CascadeApp` (Textual `App` subclass)
  - Replaced the legacy `Rich + prompt_toolkit` CascadeRepl with a full Textual alternate-screen TUI
  - Infinite scrollback via `VerticalScroll` container (eliminates old scroll-loss bug)
  - Streaming tokens rendered live into `CopyableTextArea` widgets
  - Non-blocking tool execution via `run_worker` (prevents Textual message pump deadlocks)
  - Permission prompts (`ask_user y/N`) run in background workers to avoid UI freeze
  - `Enter` key routing: single-authority handler in `PromptInput._on_key` dispatches to model palette, command palette, or chat submit (no duplicate handlers)
- **`src/cascade/ui/widgets.py`** — 4 custom widgets:
  - `PromptInput` — Multi-line input with `Enter` to submit, `Shift+Enter` for newline
  - `CopyableTextArea` — Read-only TextArea for assistant/tool output, `c` key copies to clipboard via pyperclip
  - `CopyableStatic` — Compact Rich-markup container for user messages, `c` key copies plain text
  - `SpinnerWidget` — Animated spinner (⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏) for streaming indicator
- **`src/cascade/ui/styles.py`** — `CASCADE_TCSS` stylesheet (Textual CSS)
  - Dark theme with `#0c0c0c` background, `#5fd7ff` accent, `#1a1a2e` input area
  - Scrollbar styling, toast positioning, border colors
- **`src/cascade/ui/banner.py`** — ASCII art banner + VERSION constant

#### Slash Command System
- **`src/cascade/commands/base.py`** — `BaseCommand` abstract class + `CommandContext`
  - `CommandContext` has `engine` (QueryEngine) + `repl` (CascadeApp) fields only (Textual-native, no legacy `console`/`session`)
  - Output via `ctx.output(text)` and `ctx.output_rich(markup)` which route to CascadeApp's message rendering
- **`src/cascade/commands/router.py`** — `CommandRouter` with register/dispatch/category grouping
  - No prompt_toolkit dependencies (legacy `SlashCompleter` and `get_completer()` removed)
- **`src/cascade/ui/command_palette.py`** — `CommandPalette` inline dropdown
  - Keyboard navigable (↑↓ to move, Tab/Enter to select, Esc to dismiss)
  - Filters commands as user types after `/`
- **`src/cascade/ui/model_palette.py`** — `ModelPalette` inline dropdown
  - 3-column layout (Provider, Model, Price) with `ljust()` plain-text alignment
  - 40+ models across 9 providers (DeepSeek, GLM, Anthropic, Gemini, OpenAI, xAI, MiniMax, Kimi, Qwen)
  - `✅` emoji toast notification on model switch

#### 4 Core Commands Implemented
| Command | File | Description |
|---------|------|-------------|
| `/help` (`/?`) | `commands/core/help.py` | Rich-formatted grouped command table via `output_rich()` |
| `/exit` (`/quit`) | `commands/core/exit.py` | Clean `SystemExit(0)` |
| `/clear` | `commands/core/clear.py` | Clear conversation history, keep system prompt |
| `/model` | `commands/model/model.py` | Opens inline `ModelPalette` + direct switch via `/model <provider> <model>` |

#### User Message Formatting
- Blue `❯` prefix (`[#5fd7ff]❯[/]`) on first line only (multi-line prompts show `❯` once)
- `User` border title with `CopyableStatic` container
- Compact border-only layout (no bloat)

#### Legacy Cleanup (commit `00cab15`)
- **Deleted files:**
  - `src/cascade/ui/app.py` — Old `CascadeRepl` (Rich + prompt_toolkit REPL)
  - `src/cascade/ui/spinner.py` — Old async spinner (replaced by `SpinnerWidget`)
  - `src/cascade/ui/renderer.py` — Old Rich panel renderer (rendering now inline in `textual_app.py`)
  - `src/cascade/ui/model_picker.py` — Old `ModelPickerScreen` modal (replaced by `ModelPalette`)
  - `src/cascade/cli/commands/chat.py` — Old CLI command that launched `CascadeRepl` (dead code)
- **Removed code:**
  - `SlashCompleter` class + `prompt_toolkit.completion` imports from `router.py`
  - `console` and `session` fields from `CommandContext` dataclass
  - `ModelPickerScreen` CSS block (30 lines) from `styles.py`
  - Duplicate `Enter` key handler from `CascadeApp.on_key`
  - Stale `from rich.text import Text` import from `textual_app.py`
  - `open_model_picker()` method from `CascadeApp`
- **Net result:** 11 files changed, +256 / -593 lines (net -337)

### File Manifest (post-cleanup)
```
src/cascade/commands/
├── __init__.py
├── base.py              # BaseCommand, CommandContext
├── router.py            # CommandRouter (dispatch + category)
├── core/
│   ├── __init__.py
│   ├── help.py          # /help
│   ├── exit.py          # /exit (/quit)
│   └── clear.py         # /clear
└── model/
    ├── __init__.py
    └── model.py         # /model + PROVIDER_CATALOG

src/cascade/ui/
├── __init__.py
├── banner.py            # ASCII art + VERSION
├── command_palette.py   # CommandPalette (slash dropdown)
├── model_palette.py     # ModelPalette (model dropdown)
├── styles.py            # CASCADE_TCSS
├── textual_app.py       # CascadeApp (main TUI, 580 lines)
└── widgets.py           # PromptInput, CopyableTextArea, CopyableStatic, SpinnerWidget
```

### Key Architectural Decisions
- **Alignment via plain text:** `ModelPalette` uses `ljust()` on plain-text strings *before* applying Rich markup to ensure columns stay aligned regardless of markup length
- **Event routing:** Navigation keys (↑↓/Esc) bubble from `PromptInput` → `App.on_key` for both palettes; `Enter` is intercepted at `PromptInput` level to prevent bubbling
- **Worker pattern:** All blocking operations (API streaming, permission prompts) use `self.run_worker()` to avoid blocking Textual's async message pump

### Known Issues
- Some Gemini models have long pricing strings that may wrap in narrow terminals
- `CopyableStatic` focus management in rapid scroll scenarios needs monitoring
- Test coverage for new TUI components is minimal (manual testing only)

### Commits
```
b9ea831  docs: archive phase8 as completed, create phase9 plan for remaining 33 commands
00cab15  feat(ui): inline model palette + cleanup legacy REPL code
319c455  docs: archive phase 8.5 fix plans + update slash command roadmap
cb316e2  fix(ui): resolve permission prompt freeze + enter key submission
a48763f  feat(ui): tab complete for slash menu and copyable markdown system messages
0a3f965  style(ui): compact toasts and invert slash command dropdown
32376f4  style(ui): popup polish, toast styling, and slash menu light bar
c9b2cb4  style(ui): elevate input prompt with bottom padding
e418140  fix(ui): prevent TextArea scrollbars from breaking borders
515b8d7  refactor(ui): move banner and status into scrollable history
154c389  fix(ui): prevent input section from collapsing on long scroll
15f78c9  fix(ui): move input section outside VerticalScroll — always visible
aee515b  fix(ui): add explicit scrollbar colors for dark theme visibility
c6c33b4  fix(ui): correct message ordering, restore scrollbar, fix model output
dd2d1d5  docs: add Task 9 — Command Parity plan (command palette, interactive model picker, Rich help)
5d1e3e0  feat(ui): Task 7+8 — slash autocomplete, Ctrl+Y/L bindings, footer update, deprecate old files
32f25e2  refactor(commands): adapt all slash commands for Textual TUI output via ctx.output()
a2410fb  feat(cli): switch entry point from CascadeRepl to CascadeApp (Textual)
2102e57  feat(ui): create CascadeApp Textual TUI with streaming and tool rendering
ed10e18  feat(ui): add TCSS stylesheet for Cascade dark theme
69f4fb6  feat(ui): add CopyableTextArea and SpinnerWidget for Textual TUI
a5a5e0c  chore: add textual and pyperclip dependencies for TUI migration
```



## Phase 8.5.3: Input History (⬆️⬇️ Arrow Key Recall + JSONL Persistence) ✅
- **Completed:** 2026-04-03
- **Branch:** `feat/phase8-slash-commands`

### Changes
- **`src/cascade/ui/input_history.py`** — New `InputHistory` class [NEW]
  - In-memory buffer (newest-at-end list) backed by JSONL disk file
  - `add()` — records submissions with consecutive deduplication
  - `navigate_up()` / `navigate_down()` — bidirectional traversal with boundary clamping
  - `stash()` / `stashed_input` — preserves current draft when entering history mode
  - Persistent storage at `~/.cascade/history.jsonl` (Claude-style JSONL format)
  - Each entry: `{"display": "...", "type": "prompt|command", "ts": <unix>}`
  - Hard cap: `MAX_HISTORY = 2000`, auto-truncation when disk file exceeds 2× cap
- **`src/cascade/ui/widgets.py`** — `PromptInput` history wiring
  - Added `__init__()` instantiating `InputHistory` on widget creation
  - Added `add_to_history(text)` public method for external callers
  - Refactored `_on_key()` to intercept ⬆️/⬇️:
    - ⬆️ triggers history recall only when cursor is on **first line** (multiline-safe)
    - ⬇️ triggers only on **last line** or when actively browsing
    - History mode has **priority over palette navigation** — browsing history through a `/` command won't get hijacked by the auto-opening CommandPalette
    - `Enter` resets history navigation state
- **`src/cascade/ui/textual_app.py`** — Submission recording
  - `on_input_submitted()` calls `input_widget.add_to_history(user_text)` before clearing input

### Design (inspired by competitive analysis)
| Feature | Claude Code | Gemini CLI | Codex CLI | **Cascade** |
|---------|-------------|------------|-----------|-------------|
| Storage format | JSONL | Plain text lines | SQLite-like | **JSONL** (Claude) |
| Capacity cap | ∞ (lazy load) | 100 | ∞ | **2000** (Gemini-style) |
| Dedup | ✗ | ✓ | ✓ | **✓** (Codex/Gemini) |
| Cross-session | ✓ | ✓ | ✓ | **✓** |
| Draft stash | ✓ | ✓ | ✓ | **✓** |

### Commits
```
a32e02b  feat(ui): add terminal-style input history with JSONL persistence
```



## Phase 8.5.4: Non-Blocking Message Queue (Input During Generation) ✅
- **Completed:** 2026-04-03
- **Branch:** `feat/phase8-slash-commands`

### Changes

#### Message Queue System (`src/cascade/ui/message_queue.py`) [NEW]
- `QueuedCommand` dataclass with 3-tier priority (`now`/`next`/`later`), UUID, mode, timestamps
- `MessageQueueManager` — priority-sorted FIFO queue with subscription model
  - `enqueue()` / `dequeue()` / `peek()` / `dequeue_all_matching()`
  - `pop_all_editable()` — merges queued commands back into input for editing (ESC Priority 2)
  - Subscriber notification on every mutation (drives `QueuePreview` reactive updates)
  - Static helper `is_slash_command()` for processor routing

#### Query Guard State Machine (`src/cascade/ui/query_guard.py`) [NEW]
- Three-state lifecycle: `idle` → `dispatching` → `running` → `idle`
- `reserve()` / `cancel_reservation()` — closes the async gap between dequeue and execution
- `try_start()` / `end(generation)` — generation-numbered ownership prevents stale cleanup
- `force_end()` — ESC cancel path, increments generation to invalidate in-flight `end()` calls

#### Queue Processor (`src/cascade/ui/queue_processor.py`) [NEW]
- `process_queue_if_ready()` — dequeue strategy mirroring Claude Code's `queueProcessor.ts`
  - Slash commands: process individually (not batched)
  - Non-slash prompts: batch drain all same-mode commands → single API call

#### Textual App Integration (`src/cascade/ui/textual_app.py`)
- **Three-tier submission dispatch** in `on_input_submitted()`:
  1. Immediate commands (`/model`, `/help`, `/config`, `/clear`, `/status`) bypass queue during generation
  2. If generating → `QueuedCommand` enqueued with `priority="next"`
  3. Normal idle path → `reserve()` → `_execute_prompt()` → `cancel_reservation()`
- **Prompt always visible during generation** — `_hide_prompt()` removed entirely
  - New `_set_prompt_generating(bool)` toggles label `❯` ↔ `⏳` as visual feedback
  - Users can type and submit while AI generates — input auto-enqueues
- **ESC layered cancellation** (`action_cancel_or_focus`):
  - Priority 1: Cancel active generation (`force_end()` + remove spinner)
  - Priority 2: Pop queue into input for editing (`pop_all_editable()`)
  - Priority 3: Focus input (fallback)
- **Generation lifecycle** wrapped in `try/finally`:
  - `finally` unconditionally restores `_set_prompt_generating(False)` + focus
  - Guard `force_end()` only fires if still stuck in `running` (crash/cancel safety net)

#### Widgets Sub-Package Migration (`src/cascade/ui/widgets/`) [RESTRUCTURED]
- `widgets.py` → `widgets/_core.py` (resolves package-shadows-module collision)
- `widgets/__init__.py` — full re-export of `PromptInput`, `CopyableTextArea`, `CopyableStatic`, `SpinnerWidget`, `QueuePreview`
- `QueuePreview` widget [NEW]: persistent dim-text preview of queued commands above input

### Design (aligned with Claude Code)
| Feature | Claude Code | **Cascade** |
|---------|-------------|-------------|
| Queue structure | `QueuedCommand` typed struct | `QueuedCommand` dataclass ✅ |
| Priority tiers | `now`/`next`/`later` | `now`/`next`/`later` ✅ |
| State machine | `QueryGuard.ts` (3-state) | `QueryGuard` (3-state) ✅ |
| Batch strategy | Slash individual, prompt batch | Same ✅ |
| Immediate cmds | 11 commands bypass queue | 5 commands bypass queue ✅ |
| ESC cancel | 3-layer priority | 3-layer priority ✅ |
| Queue preview | `PromptInputQueuedCommands` | `QueuePreview` widget ✅ |
| Prompt visibility | Always visible | Always visible ✅ |

### Review History
- **Round 1**: 3 🔴 (ESC clear, reserve gap, finally timing) + 2 🟡 → all fixed
- **Round 2**: 2 🟡 (guard deadlock, double render) → all fixed
- **Round 3**: 3 🔴 (widget shadowing, `_message_queue` collision, prompt restore) → all fixed
- **Round 4**: 1 🔴 (`_hide_prompt` contradicts queue design) → fixed, T1-T4 manual tests PASS

### Commits
```
7a4bce2  feat(ui): add non-blocking message queue system
b9fdf11  chore(docs): move input-queue plan to v0.3.0/phase8.5.4
```


## Phase 9: Slash Command Suite (24 commands) ✅
- **Completed:** 2026-04-16
- **Branch:** `feat/phase8-slash-commands`
- **Reviewed by:** Role 3 (Phases 9.1-9.4.5, total 13 rounds across 6 batches)

### Command Inventory

#### Phase 9.1 (Batch 1): Session Management — 6 commands

| Command | Aliases | Status | File | Notes |
|---------|---------|--------|------|-------|
| `/compact` | — | ⚠️ **Partial** | `commands/core/compact.py` | Message counting + token estimation only. No LLM summarization. |
| `/export` | — | ✅ Full | `commands/core/export_cmd.py` | JSON export with auto-filenames and sanitization |
| `/resume` | `/continue` | 🔴 **Stub** | `commands/core/resume.py` | Outputs "coming in Phase 10" |
| `/rename` | — | 🔴 **Stub** | `commands/core/rename.py` | Outputs "coming in Phase 10" |
| `/branch` | `/fork` | 🔴 **Stub** | `commands/core/branch.py` | Outputs "coming in Phase 10" |
| `/rewind` | `/checkpoint` | 🔴 **Stub** | `commands/core/rewind.py` | Outputs "coming in Phase 10" |

#### Phase 9.2 (Batch 2): Setup & Diagnostics — 5 commands

| Command | Aliases | Status | File | Notes |
|---------|---------|--------|------|-------|
| `/version` | — | ✅ Full | `commands/setup/version.py` | Reads `banner.VERSION` |
| `/config` | `/settings` | ✅ Full | `commands/setup/config.py` | Provider, model, tools, permissions |
| `/doctor` | — | ✅ Full | `commands/setup/doctor.py` | HEP-aware: grid proxy, CMSSW, HTCondor |
| `/init` | — | ✅ Full | `commands/setup/init.py` | Static CASCADE.md template (simplified vs Claude Code's LLM-driven 8-phase init) |
| `/env` | — | ✅ Full | `commands/setup/env.py` | Cascade original — API key redaction, HEP vars, CASCADE_* vars |

#### Phase 9.3 (Batch 3): UI — 3 commands

| Command | Aliases | Status | File | Notes |
|---------|---------|--------|------|-------|
| `/theme` | — | ✅ Full | `commands/ui/theme.py` | Interactive picker, live preview, hot_swap_css(), 3 themes (dark/light/cms) |
| `/btw` | — | ⚠️ **Partial** | `commands/ui/btw.py` | Appends user aside to messages — equivalent to typing normally. Real `/btw` needs mid-stream injection. |
| `/shortcuts` | `/keys`, `/keybindings` | ✅ Full | `commands/ui/shortcuts.py` | Display keyboard shortcuts |

#### Phase 9.3.5 (Batch 3.5): Workflow — 2 commands

| Command | Aliases | Status | File | Notes |
|---------|---------|--------|------|-------|
| `/copy` | — | ✅ Full | `commands/workflow/copy.py` | subprocess pbcopy/xclip, `/copy N`, `/tmp/cascade/` fallback |
| `/status` | `/summary`, `/stats` | ✅ Full | `commands/workflow/status.py` | Version, model, session duration, message counts (user/assistant/system), block-aware token estimation, tool count, theme |

#### Phase 9.4 (Batch 4): Tools — 1 command

| Command | Aliases | Status | File | Notes |
|---------|---------|--------|------|-------|
| `/tools` | — | ✅ Full | `commands/tools/tools_list.py` | Cascade original (inspired by Gemini CLI). Lists name, description for all registered tools sorted alphabetically. |

#### Phase 9.4.5 (Batch 4.5): Auto Mode — 1 command

| Command | Aliases | Status | File | Notes |
|---------|---------|--------|------|-------|
| `/auto` | — | ✅ Full | `commands/tools/auto.py` | Cascade original. Toggles `PermissionEngine.mode` between AUTO (confirm destructive) and BYPASS (auto-approve all). No execution flow changes needed. |

#### Phase 9.6 (Batch 6): Rules, Context & Token Precision — 2 commands + infrastructure

| Command | Aliases | Status | File | Notes |
|---------|---------|--------|------|-------|
| `/rules` | — | ✅ Full | `commands/rules/rules.py` + `editor_screen.py` | Cascade original (renamed from Claude Code `/memory`). Textual OptionList file picker + TextArea inline editor + Ctrl+S hot-reload via `engine.set_system_prompt()`. Surpasses Claude Code's `$EDITOR` approach. |
| `/context` | — | ✅ Full | `commands/rules/context.py` | Real API usage data (3-tier pipeline: `api_client` → `query.py` session accumulators → display). Shows last-call breakdown (in/out), session totals, progress bar. `_CONTEXT_OVERRIDES` for 23 non-LiteLLM models. Falls back to litellm `get_model_info()` for max context window. |

**Token Precision Overhaul (bundled with Batch 6):**

| File | Change |
|------|--------|
| `services/api_client.py` | `StreamResult` +`input_tokens`/`output_tokens`; `stream_options={"include_usage": True}` for LiteLLM path |
| `engine/query.py` | Session-level accumulators (`session_input_tokens`, `session_output_tokens`) + per-call trackers (`last_input_tokens`, `last_output_tokens`). All 3 return paths (end_turn, user_denied, max_rounds) correctly accumulate |
| `utils/tokens.py` | +`precise_token_count()` (LiteLLM tokenizer with rough fallback) + `precise_token_count_by_role()` |
| `commands/workflow/status.py` | Dual-mode: API real values (no `~`) or LiteLLM estimate (`~` prefix) |
| `commands/core/compact.py` | Same dual-mode pattern |

#### Removed by Design

| Command | Reason |
|---------|--------|
| `/brief` | Decided against by Role 1 (Phase 9.3) |
| `/diff` | Superseded by BashTool + `git diff` — AI can see the output; `/diff` would only show it to the user (Phase 9.3.5) |
| `/permissions` | Removed from Batch 4 — wait for Phase 6 (v0.9.0) Advanced Permission System |
| `/hooks` | Removed from Batch 4 — wait for Phase 7 (v0.10.0) Hooks & CASCADE.md Rules |
| `/sandbox` | Removed from Batch 4 — Claude Code depends on closed-source `@anthropic-ai/sandbox-runtime` |
| `/debug-tool-call` | Removed from Batch 4 — Claude Code itself disabled it (`isEnabled: false, isHidden: true`) |

### Infrastructure Added

| Module | File | Purpose |
|--------|------|---------|
| CASCADE.md Loading | `src/cascade/bootstrap/system_prompt.py` | `CASCADE_MD_PATHS` + `get_cascade_md_files()` — discovers CASCADE.md at project/user/global levels and injects into system prompt. Prerequisite for `/rules` hot-reload. |
| Token Estimation | `src/cascade/utils/tokens.py` | Block-aware rough estimation aligned with Claude Code `tokenEstimation.ts` L203-435. UTF-8 byte length for CJK. Handles text, tool_use, tool_result, image (2000), thinking, redacted_thinking blocks. Also contains `precise_token_count()` and `precise_token_count_by_role()` wrappers for LiteLLM tokenizer with rough fallback. |
| Token Pipeline | `api_client.py` → `query.py` → commands | 3-tier real API usage tracking: `StreamResult` extracts `prompt_tokens`/`completion_tokens` from stream chunks → `QueryEngine` accumulates session-level and per-call counters → `/context`, `/status`, `/compact` display with dual-mode (API real vs `~` LiteLLM estimate). |
| Theme System | `src/cascade/ui/styles.py` | Multi-theme (ThemeColors dataclass, `build_tcss()` generator, `hot_swap_css()` for Textual 8.x CssSource API) |
| Theme Palette | `src/cascade/ui/theme_palette.py` | Interactive ↑↓ picker with live preview and Esc rollback |

### Commits
```
e8507e7  feat(commands): Phase 9.1 Batch 1 — add 6 session management commands
63a8383  feat(commands): Phase 9.2 Batch 2 — add 5 setup & diagnostics commands
51eab4e  feat(ui): add /theme /btw /shortcuts commands (Phase 9.3 Batch 3)
c95bd69  feat(workflow): add /copy /status commands + token estimation (Phase 9.3.5)
057fc4c  feat(commands): add /tools command (Phase 9.4 Batch 4)
e86dc14  feat(commands): add /auto command + update walkthrough (Phase 9.4.5)
(pending) feat(commands): add /rules /context commands + CASCADE.md loading (Phase 9.6 Batch 6)
```

### Summary

| Metric | Count |
|--------|-------|
| Total commands | **24** |
| ✅ Full implementation | **17** |
| ⚠️ Partial (functional but incomplete) | **2** (`/compact`, `/btw`) |
| 🔴 Pure stub | **4** (`/resume`, `/rename`, `/branch`, `/rewind`) |
| Removed by design | **6** (`/brief`, `/diff`, `/permissions`, `/hooks`, `/sandbox`, `/debug-tool-call`) |

---

## 🔴 Stub & ⚠️ Partial Commands — Roadmap Cross-Reference

> 对照 [Cascade_long_term_plan_v3.md](file:///Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/Cascade_long_term_plan_v3.md) 检查哪些 stub/partial 命令已有完整实现计划。

### ✅ 计划已覆盖

| Command | 当前状态 | 计划覆盖 | 计划位置 |
|---------|---------|---------|---------|
| `/resume` | 🔴 Stub | ✅ [Phase 8: Session Resume](file:///Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/Cascade_long_term_plan_v3.md#L1536) — Task 20 | L1536-1554: `session_resume.py` + `commands/session/resume.py` |
| `/compact` | ⚠️ Partial | ✅ [Phase 5: Context Compaction](file:///Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/Cascade_long_term_plan_v3.md#L1208) — Task 14 | L1208-1213: `services/compact/compactor.py` + `summarizer.py` |

### ❌ 计划未覆盖 — 列入 Open Questions

| Command | 当前状态 | 说明 |
|---------|---------|------|
| `/rename` | 🔴 Stub | 依赖 Session Storage (Plan Phase 2 Task 8)，但 `/rename` 命令本身未在 long-term plan 中提及 |
| `/branch` (`/fork`) | 🔴 Stub | 会话分叉逻辑未在任何 Task 中规划 |
| `/rewind` (`/checkpoint`) | 🔴 Stub | Checkpoint/snapshot 系统未在任何 Task 中规划 |
| `/btw` | ⚠️ Partial | Mid-stream injection 需要 streaming engine 支持边流边收输入，计划中无此项 |

---


## Open Questions (v0.3.0)

> 以下问题在当前版本周期中被识别但尚未解决，记录于此以防遗忘。

| # | 问题 | 来源 | 状态 |
|---|------|------|------|
| OQ-1 | `Cascade*.md` 开发准则不入仓库，未来由 `CASCADE.md`（类似 `GEMINI.md` / `CLAUDE.md`）全局规则文件取代，用户自定义 | `docs-reorg-discussion` 🟡 Y1 | 📌 设计方向已定，待 v0.3.0 CLI 框架支持 |
| OQ-2 | `cas-texwriter` 学术论文同步能力的归属——当前以 Antigravity skill 形式实现（8 步 Digest-First Patch 工作流），后续需评估是否独立为系统级架构模块（如 `docs/paper/` 管线自动化）还是保留为可插拔 skill | `cas-texwriter-discussion` 圆桌 R1-R2 | 💡 当前 skill 形式满足需求，累积 2-3 次实际论文同步后再评估架构提升必要性 |
| OQ-3 | `cas-roundtable` skill 的独立价值——多 Agent 结构化交互方式，未来可能影响框架级 multi-agent 设计 | 圆桌会议实践总结 | 💡 观察中，积累更多实际使用经验后评估 |
| OQ-4 | **环境隔离策略冲突 (Cascade `.venv` vs `pandoc` vs `lxplus cmsenv`)** <br><br> 当前系统存在三套独立工具链：<br> 1. Cascade CLI 及依赖 (Python 生态，常驻 `.venv`) <br> 2. `pandoc` + `pandoc-crossref` (Haskell 编译独立二进制，无法放入 `.venv`，需放置于 `~/.local/bin`) <br> 3. HEP 领域工具 (如 lxplus 上的 CMSSW + ROOT，必须 source `cmsenv` 注入环境变量)。<br><br> **潜在冲突：** `cmsenv` 会劫持 PYTHONPATH 和 PATH，若与 Cascade 的 `.venv` Python 版本/库不一致，将引发环境崩溃。特别是未来开发 Phase (HEP Tool Wrapper) 时，必须使用 ROOT Python Bindings。<br><br> **评估的三种解决方案：**<br> - **A:** Cascade `.venv` 在 `cmsenv` *之后*激活，通过 `--system-site-packages` 继承 ROOT。缺点：依然难以保证依赖纯净，极易引发版本冲突。<br> - **B:** 使用独立的 `conda env` 管理 Cascade，并通过 `conda install root` 引入 ROOT。缺点：剥离了 CMSSW 的官方依赖树，可能与部分官方宏脚本不兼容。<br> - **C (✨ 推荐): 完全隔离架构** <br> &nbsp;&nbsp;&nbsp;&nbsp;1. Cascade CLI 本体及其 LLM/.venv 保持绝对纯净，通过独立的 bash alias 或 wrapper 运行。<br> &nbsp;&nbsp;&nbsp;&nbsp;2. 排版套件 `pandoc` 使用 CVMFS 共享包或仅存放于 `~/.local/bin` 作为独立二进制调用。<br> &nbsp;&nbsp;&nbsp;&nbsp;3. 任何需要调用 HEP 工具（如 ROOT / CMSSW 脚本）的 Agent Task，必须通过 `subprocess` （`BashTool`）去单独起一个干净的 shell，在里面执行 `source cmsenv && python my_analysis.py`。主进程环境永不污染。<br><br> | `cas-texwriter-discussion` 🟡 Y4 | 💡 当前 `cas-texwriter` 不依赖 `cmsenv`。明确采用 **选项 C** 作为未来 HEP Tool Wrappers 的基础设施设计原则。 |
| OQ-5 | **`/rename` stub — 会话命名系统** <br> 依赖 Session Storage (Plan Phase 2 Task 8) 但 `/rename` 命令和会话命名逻辑本身未在 `Cascade_long_term_plan_v3.md` 的任何 Task 中规划。需要决定：(a) 加入 Phase 8 Session Resume 作为子 Task，或 (b) 独立 Phase 规划 | Phase 9 审查 | 📌 待决定归属 |
| OQ-6 | **`/branch` (`/fork`) stub — 会话分叉** <br> 需要 deep copy messages + 独立 session ID。Claude Code 同名命令存在但与 subagent fork 重叠。需要决定：(a) 实现为轻量 message fork，或 (b) 与将来的 multi-agent 系统合并设计 | Phase 9 审查 | 📌 待决定是否实现 |
| OQ-7 | **`/rewind` (`/checkpoint`) stub — 对话回退** <br> 需要 message snapshot stack。Claude Code 同名命令存在但源码较薄（仅 index.ts 入口）。需要决定：(a) 简单实现为 truncate messages 到指定轮，或 (b) full checkpoint with branching | Phase 9 审查 | 📌 待决定实现深度 |
| OQ-8 | **`/btw` partial — mid-stream 注入** <br> 当前等同于直接发消息。真正的 `/btw` 需要 streaming 引擎支持边流边收输入。三种实现路径：A 打断+重发（中等难度），B side fork（高难度），C 下轮生效（低难度但无核心价值）。`Cascade_long_term_plan_v3.md` 中无此项规划 | Phase 9 审查 | 📌 待决定实现路径 |

---

### Next Steps
→ Phase 9.5 (Batch 5): Git commands — **CANCELLED** (redundant with BashTool)
→ Phase 9.7 (Batch 7): Plugin commands — see `docs/plans/v0.3.0/phase9.7-batch7-plugin-commands.md`

---