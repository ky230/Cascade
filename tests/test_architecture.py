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

def test_deprecated_dirs_removed():
    base_dir = "src/cascade"
    assert not os.path.exists(os.path.join(base_dir, "api")), "api/ should be deleted"
    assert not os.path.exists(os.path.join(base_dir, "core")), "core/ should be deleted"

def test_cli_moved():
    assert not os.path.exists("src/cascade/cli.py"), "old cli.py should be moved"
    assert os.path.exists("src/cascade/cli/main.py"), "new cli/main.py should exist"
