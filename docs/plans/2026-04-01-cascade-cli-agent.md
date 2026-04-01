# Cascade Phase 2: CLI & Agent Core Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the CLI entrypoint (`cascade chat`) and the Core Agent loop that gives the LLM memory and conversational capability, while also establishing `walkthrough.md` as the permanent high-level project ledger.

**Architecture:** We will register a terminal command `cascade` via `pyproject.toml`. The CLI will route to `src/cascade/cli.py` which instantiates an `Agent` (`src/cascade/core/agent.py`). The Agent wraps `ModelClient` and maintains a conversational memory array (List of dicts: role/content) to allow multi-turn dialogue.

**Tech Stack:** Python 3, `pytest`, `argparse`, `asyncio`.

---

### Task 1: Establish High-Level Walkthrough Ledger

**Files:**
- Create: `docs/walkthrough.md`

**Step 1: Write initial walkthrough content**
Since this is documentation, no tests are needed.

```markdown
# Cascade Project Walkthrough

This document serves as the high-level ledger of completed development phases for the Cascade framework. Detailed, granular TDD plans are stored individually in `docs/plans/`.

## Phase 0: Base Infrastructure
- **Completed:** 2026-03-31
- **Achievements:** scaffolded `src/cascade` architecture, established TDD harness with `pytest`, created `BaseTool` abstraction, and secured the repository with standard Git/`.env` patterns.

## Phase 1: Universal LLM Integration
- **Completed:** 2026-04-01
- **Achievements:** Integrated `litellm` as the universal mesh for LLM routing, enabling seamless fallback between OpenAI, Anthropic, Gemini, and localized Chinese models (GLM, Kimi, DeepSeek) via `ModelClient`. Tested with real Google GenAI endpoints.

## Phase 2: Agent Conversation & CLI (In Progress)
- **Goal:** Provide terminal access (`cascade chat`) and give the LLM multi-turn conversation memory (`Agent` core).
```

**Step 2: Commit**
```bash
git add docs/walkthrough.md
git commit -m "docs: establish high-level project walkthrough ledger"
```

---

### Task 2: Core Agent Implementation Matrix

**Files:**
- Create: `src/cascade/core/agent.py`
- Create: `tests/core/test_agent.py`

**Step 1: Write the failing test**

```python
# tests/core/test_agent.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from cascade.core.agent import Agent

@pytest.mark.asyncio
async def test_agent_memory_loop(mocker):
    # Mock litellm acompletion entirely to avoid network
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "I am Cascade."
    
    mock_acompletion = AsyncMock(return_value=mock_response)
    mocker.patch('cascade.api.client.acompletion', new=mock_acompletion)
    
    agent = Agent(provider="openai", model_name="gpt-4o", system_prompt="You are a HEP Assistant.")
    
    # Check initial memory
    assert len(agent.memory) == 1
    assert agent.memory[0]["role"] == "system"
    
    # First turn
    reply1 = await agent.chat("Who are you?")
    assert reply1 == "I am Cascade."
    assert len(agent.memory) == 3 # System -> User -> Assistant
    assert agent.memory[1]["content"] == "Who are you?"
    assert agent.memory[2]["content"] == "I am Cascade."
```

**Step 2: Run test to verify it fails**
Run: `python3 -m pytest tests/core/test_agent.py -v`
Expected: FAIL (ModuleNotFoundError for `cascade.core.agent`)

**Step 3: Write minimal implementation**

```python
# src/cascade/core/agent.py
from typing import List, Dict
from cascade.api.client import ModelClient

class Agent:
    def __init__(self, provider: str, model_name: str, system_prompt: str = "You are a helpful assistant."):
        self.client = ModelClient(provider=provider, model_name=model_name)
        self.memory: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]

    async def chat(self, user_message: str) -> str:
        """Process a single conversational turn with memory."""
        self.memory.append({"role": "user", "content": user_message})
        
        # We need to bypass the client's single-prompt limit or update the client
        # For now, we will just call litellm block natively in Agent, or 
        # modify client.py. To respect encapsulation, we will update client.generate
        # but to keep TDD atomic, we'll patch ModelClient to accept messages list.
        
        # Actually, let's use the ModelClient client.generate() by passing memory directly.
        pass
```
*Wait, `client.generate()` currently only accepts a `prompt: str`.*
Let's update `ModelClient` in the same Task to accept a full message array.

```python
# src/cascade/api/client.py (Update)
from litellm import acompletion
from cascade.api.config import get_litellm_kwargs
from typing import List, Dict

class ModelClient:
    def __init__(self, provider: str, model_name: str):
        self.provider = provider
        self.model_name = model_name

    async def generate(self, messages: List[Dict[str, str]]) -> str:
        """Call universal LLM endpoint asynchronously."""
        kwargs = get_litellm_kwargs(self.provider, self.model_name)
        
        response = await acompletion(
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content
```

```python
# src/cascade/core/agent.py (Revised)
from typing import List, Dict
from cascade.api.client import ModelClient

class Agent:
    def __init__(self, provider: str, model_name: str, system_prompt: str = "You are a helpful Cascade Agent."):
        self.client = ModelClient(provider=provider, model_name=model_name)
        self.memory: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]

    async def chat(self, user_message: str) -> str:
        self.memory.append({"role": "user", "content": user_message})
        response = await self.client.generate(self.memory)
        self.memory.append({"role": "assistant", "content": response})
        return response
```
*(Also adapt existing `test_client.py` to pass `messages=[...]` instead of `prompt="str"` during validation).*

**Step 4: Run test to verify it passes**
Run: `python3 -m pytest tests/ -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/cascade tests/
git commit -m "feat: implement conversational Agent with memory loop"
```

---

### Task 3: CLI Entrypoint Shell

**Files:**
- Create: `src/cascade/cli.py`
- Modify: `pyproject.toml`

**Step 1: Write setup/dependencies**

```toml
# Append to pyproject.toml
[project.scripts]
cascade = "cascade.cli:main"
```

**Step 2: Write minimal implementation**

```python
# src/cascade/cli.py
import argparse
import asyncio
import sys
import os
from dotenv import load_dotenv
from cascade.core.agent import Agent

def main():
    load_dotenv()
    # Read defaults from .env if available, else fallback
    default_provider = os.getenv("CASCADE_DEFAULT_PROVIDER", "openai")
    default_model = os.getenv("CASCADE_DEFAULT_MODEL", "gpt-4o")

    parser = argparse.ArgumentParser(description="Cascade: CLI Agentic Orchestrator for HEP")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    chat_parser = subparsers.add_parser("chat", help="Start an interactive chat session.")
    chat_parser.add_argument("--provider", type=str, default=default_provider)
    chat_parser.add_argument("--model", type=str, default=default_model)

    args = parser.parse_args()

    if args.command == "chat":
        asyncio.run(interactive_chat(args.provider, args.model))

async def interactive_chat(provider: str, model: str):
    print(f"🌀 Welcome to Cascade! (Model: {provider}/{model})")
    print("Type 'exit' or 'quit' to end.\n")
    
    agent = Agent(provider=provider, model_name=model)
    
    while True:
        try:
            user_input = input("You> ")
            if user_input.lower() in ["exit", "quit"]:
                print("Exiting Cascade. Goodbye!")
                break
            if not user_input.strip():
                continue
                
            response = await agent.chat(user_input)
            print(f"\nCascade> {response}\n")
            
        except KeyboardInterrupt:
            print("\nExiting Cascade. Goodbye!")
            break
        except Exception as e:
            print(f"\n[Error] {str(e)}")
```

**Step 3: Run verification**
Run: `pip install -e .`
Run: `cascade --help`
Expected: Outputs argparse help menu.

**Step 4: Commit**
```bash
git add pyproject.toml src/cascade/cli.py
git commit -m "feat: implement CLI entrypoint and interactive chat loop"
```
