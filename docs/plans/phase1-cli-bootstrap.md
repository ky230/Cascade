# Phase 1: CLI Entry & Bootstrap Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Establish `Click` as the foundational CLI dispatcher to handle scaling subcommands (`chat`, `init`, etc.). Build a bootstrap layer that detects HPC environment specifics (ROOT, CMSSW, HTCondor) to inject into the LLM system prompt.
**Architecture:** `cascade.cli` handles arguments, `cascade.bootstrap` handles environment injection. This ensures the engine layer is decoupled from arguments extraction.
**Tech Stack:** `click`, `os`, `shutil`, `socket`.

---

### Task 1.1: Implement Click CLI Framework

**Files:**
- Create: `src/cascade/cli/main.py`
- Create: `src/cascade/cli/commands/__init__.py`
- Create: `src/cascade/cli/commands/chat.py`
- Modify: `tests/test_cli.py`

**Step 1: Write the failing test**

```python
# Create tests/test_cli.py
from click.testing import CliRunner
from cascade.cli.main import cli

def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'cascade' in result.output.lower()

def test_chat_help():
    runner = CliRunner()
    result = runner.invoke(cli, ['chat', '--help'])
    assert result.exit_code == 0
    assert '--provider' in result.output
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL due to missing Click `cli` instance in `main.py`.

**Step 3: Write minimal implementation**

```python
# src/cascade/cli/main.py
import click
from cascade.cli.commands.chat import chat

@click.group()
@click.version_option(version="0.2.0", prog_name="Cascade")
def cli():
    """Cascade — HEP Agentic Orchestrator"""
    pass

cli.add_command(chat)

def main():
    cli()

if __name__ == "__main__":
    main()
```

```python
# src/cascade/cli/commands/chat.py
import asyncio
import click
from dotenv import load_dotenv

@click.command()
@click.option('--provider', default='glm',
    type=click.Choice(['glm', 'anthropic', 'openai', 'deepseek', 'kimi']))
@click.option('--model', default='glm-4.6v-flash', help='Model identifier')
@click.option('--verbose', is_flag=True, help='Verbose output')
def chat(provider, model, verbose):
    """Start an interactive chat session."""
    load_dotenv()
    # Temporary placeholder until UI is rebuilt
    click.echo(f"Starting chat with {provider} {model}...")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/cascade/cli tests/test_cli.py
git commit -m "feat(cli): implement Click-based subcommands framework"
```

---

### Task 1.2: Environment Detection Bootstrap

**Files:**
- Create: `src/cascade/bootstrap/setup.py`
- Create: `src/cascade/bootstrap/system_prompt.py`
- Create: `tests/test_bootstrap.py`

**Step 1: Write the failing test**

```python
# Create tests/test_bootstrap.py
from cascade.bootstrap.setup import detect_environment
from cascade.bootstrap.system_prompt import build_system_prompt

def test_detect_environment():
    env = detect_environment()
    assert 'python_version' in env
    assert 'platform' in env
    assert 'has_root' in env
    assert isinstance(env['has_root'], bool)

def test_build_system_prompt():
    prompt = build_system_prompt(custom_prompt="Be concise.")
    assert "High-Energy Physics" in prompt
    assert "Be concise." in prompt
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_bootstrap.py -v`
Expected: FAIL due to missing module `cascade.bootstrap.setup`.

**Step 3: Write minimal implementation**

```python
# src/cascade/bootstrap/setup.py
import os
import sys
import shutil
import platform
import socket

def detect_environment() -> dict:
    return {
        'python_version': sys.version.split()[0],
        'platform': platform.system(),
        'cwd': os.getcwd(),
        'has_root': shutil.which('root') is not None,
        'has_cmssw': 'CMSSW_BASE' in os.environ,
        'has_condor': shutil.which('condor_submit') is not None,
        'hostname': socket.gethostname(),
    }
```

```python
# src/cascade/bootstrap/system_prompt.py
from cascade.bootstrap.setup import detect_environment

def build_system_prompt(custom_prompt: str | None = None) -> str:
    env = detect_environment()
    base = f"""You are Cascade, an AI assistant for High-Energy Physics workflows.

Environment:
- Python: {env['python_version']}
- Platform: {env['platform']}
- CWD: {env['cwd']}
- ROOT available: {env['has_root']}
- CMSSW available: {env['has_cmssw']}
- HTCondor available: {env['has_condor']}
- Host: {env['hostname']}

You have access to tools for file operations, shell commands, and HEP-specific tasks.
Always explain what you plan to do before executing tools.
"""
    if custom_prompt:
        base += f"\n\nAdditional Instructions:\n{custom_prompt}"
    return base
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_bootstrap.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/cascade/bootstrap tests/test_bootstrap.py
git commit -m "feat(bootstrap): HEP environment detection and system prompt builder"
```
