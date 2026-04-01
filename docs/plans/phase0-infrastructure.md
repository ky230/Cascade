# Phase 0: Infrastructure & Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Establish the new 8-layer directory foundation for Cascade v2 and aggressively remove old deprecated modules (api/core) without breaking the existing `ui/app` momentarily.
**Architecture:** Basic Python file management and `__init__.py` bootstrapping for absolute top-level module organization.
**Tech Stack:** `os`, `shutil`, `pytest`.

---

### Task 0.1: Standardize New Directory Structure

**Files:**
- Create directories inside `src/cascade/`
- Create `__init__.py` files

**Step 1: Write the failing test**

```python
# Create tests/test_architecture.py
import os
import pytest

def test_package_structure_exists():
    base_dir = "src/cascade"
    required_dirs = [
        "cli/commands", "bootstrap", "engine", "tools/hep",
        "permissions", "services/mcp", "services/memory",
        "services/remote", "state", "types"
    ]
    for d in required_dirs:
        assert os.path.isdir(os.path.join(base_dir, d)), f"Directory {d} is missing"
        
        # Check __init__.py exists in the parent package of the sub-dir
        pkg = d.split('/')[0]
        init_file = os.path.join(base_dir, pkg, "__init__.py")
        assert os.path.isfile(init_file), f"No __init__.py in {pkg}"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_architecture.py -v`
Expected: FAIL with "Directory cli/commands is missing"

**Step 3: Write minimal implementation**

Run:
```bash
cd src/cascade
mkdir -p cli/commands bootstrap engine tools/hep permissions services/{mcp,memory,remote} state types
find . -type d -exec touch {}/__init__.py \;
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_architecture.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/cascade tests/test_architecture.py
git commit -m "chore: scaffold Cascade v2 8-layer directory structure"
```

---

### Task 0.2: Migrate & Delete Deprecated Code

**Files:**
- Delete: `src/cascade/api/`
- Delete: `src/cascade/core/`
- Move: `src/cascade/cli.py` -> `src/cascade/cli/main.py`
- Modify: `pyproject.toml`
- Test: `tests/test_architecture.py`

**Step 1: Write the failing test**

```python
# Append to tests/test_architecture.py

def test_deprecated_dirs_removed():
    base_dir = "src/cascade"
    assert not os.path.exists(os.path.join(base_dir, "api")), "api/ should be deleted"
    assert not os.path.exists(os.path.join(base_dir, "core")), "core/ should be deleted"

def test_cli_moved():
    assert not os.path.exists("src/cascade/cli.py"), "old cli.py should be moved"
    assert os.path.exists("src/cascade/cli/main.py"), "new cli/main.py should exist"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_architecture.py -v`
Expected: FAIL with "api/ should be deleted"

**Step 3: Write minimal implementation**

Run:
```bash
# Move cli.py
mv src/cascade/cli.py src/cascade/cli/main.py

# Remove old directories completely (user authorized)
rm -rf src/cascade/api
rm -rf src/cascade/core
```

Modify `pyproject.toml`:
```toml
# Change entry point
[project.scripts]
cascade = "cascade.cli.main:main"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_architecture.py -v`
Expected: PASS

*(Note: If `src/cascade/ui/app.py` breaks due to missing imports from `core.agent`, comment out the offending lines temporarily in `app.py` to ensure tests pass, as we will rewrite the engine next).*

**Step 5: Commit**

```bash
git add -A
git commit -m "refactor: drop deprecated api/core modules and move CLI entry"
```
