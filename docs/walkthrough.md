# Cascade v2 Architecture Rewrite — Walkthrough

> 基于 Claude Code 8 层架构的完全重写。每个 Phase 完成后更新此文档。

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

## Phase 2: Reactive State & API Streaming ⏳
*Pending*

## Phase 3: Core Query Engine ⏳
*Pending*

## Phase 4: Tool System ⏳
*Pending*

## Phase 5: Permission & Security ⏳
*Pending*

## Phase 6: UI Rendering Integration ⏳
*Pending*
