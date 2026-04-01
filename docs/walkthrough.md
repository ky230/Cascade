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
