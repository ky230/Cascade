# Cascade Infrastructure Rebuild — Implementation Plan (方案 C v3)

> **v3 变更 (2026-04-03):** 在 v2 (26 Tasks) 基础上，整合 Sonnet 审查的 15 条补丁：Pydantic V2 迁移、HEP 领域感知、Streaming Tool Execution、SemanticRouter、Daemon/Client 架构、HEPDataTool 等。总计 **32 Tasks**。

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 Cascade 从 v0.3.0 TUI demo 重构为 production-grade CLI 基础设施，采用方案 C（Foundation + Cherry-Pick），对齐 Claude Code 核心架构并按需选取高价值模块。

**Architecture:** 以 Claude Code 为主参考，Python 栈用 `Pydantic V2` + `pydantic-settings` + `typing.Protocol` 替代 TypeScript Zod + interfaces，Textual 替代 React/Ink。TDD 强制闭环。

**Tech Stack:** Python 3.11+ / Textual / litellm / aiohttp / **Pydantic V2 + pydantic-settings** / pytest

> [!IMPORTANT]
> **Sonnet 补丁 #1 — Tech Stack 变更：** `dataclasses + jsonschema` → `Pydantic V2 + pydantic-settings`。所有 Task 的数据类改为 `BaseModel`，`get_input_schema()` 改为 `model_json_schema()` 自动生成。

> [!WARNING]
> **Pydantic 防坑：** 所有用于解析 LLM Tool Call JSON 的 Input BaseModel **必须** 加 `model_config = {"extra": "ignore"}`。国内小参数模型（DeepSeek/GLM/Kimi/Qwen）经常幻觉出未定义的额外字段，不加这个会触发 `ValidationError` 导致 tool call 全部失败。

---

## Phase 1: Foundation Types & Protocol Layer (v0.4.0)

### 对标 Claude Code 源码

| Claude Code 文件 | 大小 | Cascade 对应 | 做什么 |
|---|---|---|---|
| `src/Tool.ts` | 30K | `src/cascade/tools/base.py` | Tool 抽象协议 — `inputSchema`/`checkPermissions`/`isDestructive`/`maxResultSizeChars` 等 |
| `src/types/message.ts` → `src/types/` | 目录 8 files | `src/cascade/types/message.py` | 强类型消息协议 — `UserMessage`/`AssistantMessage`/`ToolResultMessage` |
| `src/types/permissions.ts` | 13K | `src/cascade/types/permissions.py` | 权限类型定义 |
| `src/state/AppStateStore.ts` | 22K | `src/cascade/state/app_state.py` | 丰富的应用状态 — usage tracking/MCP/permission rules |
| `src/state/store.ts` | 1K | `src/cascade/state/store.py` | 响应式 store 基础 |

---

### Task 1: Message Protocol Types

**Files:**
- Create: `src/cascade/types/__init__.py`
- Create: `src/cascade/types/message.py`
- Test: `tests/test_types_message.py`

**Step 1: Write the failing test**

```python
# tests/test_types_message.py
from cascade.types.message import (
    UserMessage, AssistantMessage, ToolUseBlock,
    ToolResultMessage, SystemMessage,
)

def test_user_message_defaults():
    msg = UserMessage(content="hello")
    assert msg.type == "user"
    assert msg.content == "hello"
    assert msg.uuid  # auto-generated
    assert msg.timestamp > 0

def test_assistant_with_tool_calls():
    tc = ToolUseBlock(id="tc1", name="bash", arguments={"command": "ls"})
    msg = AssistantMessage(content="", tool_calls=[tc])
    assert msg.type == "assistant"
    assert len(msg.tool_calls) == 1
    assert msg.tool_calls[0].name == "bash"

def test_tool_result_message():
    msg = ToolResultMessage(tool_use_id="tc1", content="output", is_error=False)
    assert msg.type == "tool_result"

def test_system_message_subtype():
    msg = SystemMessage(content="compacted", subtype="compact_boundary")
    assert msg.subtype == "compact_boundary"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_types_message.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cascade.types.message'`

**Step 3: Write minimal implementation**

```python
# src/cascade/types/__init__.py
# (empty)

# src/cascade/types/message.py
from __future__ import annotations
from typing import Literal, Any
from uuid import uuid4
import time
from pydantic import BaseModel, Field

class MessageBase(BaseModel):
    uuid: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: float = Field(default_factory=time.time)

class UserMessage(MessageBase):
    type: Literal["user"] = "user"
    content: str = ""
    is_meta: bool = False

class AssistantMessage(MessageBase):
    type: Literal["assistant"] = "assistant"
    content: str = ""
    tool_calls: list[ToolUseBlock] = Field(default_factory=list)
    stop_reason: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0

class ToolUseBlock(BaseModel):
    id: str = ""
    name: str = ""
    arguments: dict[str, Any] = Field(default_factory=dict)

class ToolResultMessage(MessageBase):
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str = ""
    content: str = ""
    is_error: bool = False

# Sonnet Patch #3: SystemMessage 新增 hep_env
class SystemMessage(MessageBase):
    type: Literal["system"] = "system"
    content: str = ""
    subtype: str = ""
    hep_env: dict = Field(default_factory=dict)  # CMSSW_BASE, SCRAM_ARCH, X509 etc.

Message = UserMessage | AssistantMessage | ToolResultMessage | SystemMessage
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_types_message.py -v`
Expected: PASS (4/4)

**Step 5: Commit**

```bash
git add src/cascade/types/ tests/test_types_message.py
git commit -m "feat(types): add Message protocol types — Phase 1 Task 1"
```

---

### Task 2: Rich Tool Protocol

**Files:**
- Modify: `src/cascade/tools/base.py`
- Create: `src/cascade/types/context.py`
- Test: `tests/test_tools_base.py`

**Step 1: Write the failing test**

```python
# tests/test_tools_base.py
from cascade.tools.base import BaseTool, ToolResult, ValidationResult, PermissionCheckResult
from cascade.types.context import ToolUseContext

class MockTool(BaseTool):
    @property
    def name(self): return "mock"
    @property
    def description(self): return "A mock tool"
    async def execute(self, input, context):
        return ToolResult(output="ok")
    def get_input_schema(self):
        return {"type": "object", "properties": {"x": {"type": "string"}}}

import pytest

@pytest.mark.asyncio
async def test_tool_defaults():
    t = MockTool()
    assert t.is_read_only == False
    assert t.is_destructive == False
    assert t.is_concurrency_safe == False
    assert t.max_result_size_chars == 50_000

@pytest.mark.asyncio
async def test_tool_validate_input():
    t = MockTool()
    ctx = ToolUseContext()
    result = await t.validate_input({"x": "hello"}, ctx)
    assert result.valid == True

@pytest.mark.asyncio
async def test_tool_check_permissions():
    t = MockTool()
    ctx = ToolUseContext()
    result = await t.check_permissions({"x": "hello"}, ctx)
    assert result.behavior == "allow"

@pytest.mark.asyncio
async def test_tool_execute():
    t = MockTool()
    ctx = ToolUseContext()
    result = await t.execute({"x": "hello"}, ctx)
    assert result.output == "ok"
    assert result.is_error == False
```

**Step 2: Run test → FAIL**

**Step 3: Write implementation**

```python
# src/cascade/types/context.py
from __future__ import annotations
from typing import Callable, Awaitable, Any, TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from cascade.state.app_state import AppState

class ToolUseContext(BaseModel):
    """Runtime context available to every tool execution."""
    model_config = {"arbitrary_types_allowed": True}
    messages: list = Field(default_factory=list)
    tools: list = Field(default_factory=list)
    debug: bool = False
    verbose: bool = False
    model: str = ""
    is_non_interactive: bool = False
    cwd: str = ""
    get_app_state: Callable[[], "AppState"] | None = None
    set_app_state: Callable[[Callable], None] | None = None
    abort_signal: Any = None
    ask_user: Callable[[str], Awaitable[bool]] | None = None
```

```python
# src/cascade/tools/base.py (rewritten)
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Literal, AsyncGenerator, Union
from pydantic import BaseModel, Field

class ToolResult(BaseModel):
    output: str
    is_error: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

class ValidationResult(BaseModel):
    valid: bool
    message: str = ""

class PermissionCheckResult(BaseModel):
    behavior: str = "allow"  # "allow" | "deny" | "ask"
    reason: str = ""
    updated_input: dict | None = None

class BaseTool(ABC):
    """Rich tool protocol — aligned with Claude Code Tool interface."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    def aliases(self) -> list[str]: return []

    @property
    def is_read_only(self) -> bool: return False

    @property
    def is_destructive(self) -> bool: return False

    @property
    def is_concurrency_safe(self) -> bool: return False

    @property
    def max_result_size_chars(self) -> int: return 50_000

    # Sonnet Patch #2: HEP domain tag
    @property
    def domain(self) -> Literal["general", "hep", "cms", "pheno"]:
        return "general"

    def is_enabled(self) -> bool: return True

    @abstractmethod
    async def execute(
        self, input: dict[str, Any], context: "ToolUseContext"
    ) -> Union[ToolResult, AsyncGenerator[str, None]]:
        """Return ToolResult or yield streaming str chunks."""
        ...

    def get_input_schema(self) -> dict:
        """Override for manual schema, or use model_json_schema() with Pydantic input model."""
        return {}

    async def validate_input(self, input: dict, context: "ToolUseContext") -> ValidationResult:
        return ValidationResult(valid=True)

    async def check_permissions(self, input: dict, context: "ToolUseContext") -> PermissionCheckResult:
        return PermissionCheckResult(behavior="allow")

    def user_facing_name(self, input: dict | None = None) -> str:
        return self.name

    def get_activity_description(self, input: dict | None = None) -> str | None:
        return None
```

**Step 4: Run test → PASS**

**Step 5: Migrate existing tools** — Update `BashTool`, `FileReadTool`, `FileWriteTool`, `GrepTool`, `GlobTool` signatures to accept `(input, context)`.

**Step 6: Commit**

```bash
git commit -m "feat(tools): rich Tool protocol with ToolUseContext — Phase 1 Task 2"
```

---

### Task 3: Enriched AppState

**Files:**
- Modify: `src/cascade/state/app_state.py`
- Test: `tests/test_app_state.py`

**Step 1: Write the failing test**

```python
# tests/test_app_state.py
from cascade.state.app_state import AppState

def test_app_state_new_fields():
    s = AppState()
    assert s.session_id == ""
    assert s.cwd == ""
    assert s.total_cost_usd == 0.0
    assert s.api_duration_ms == 0
    assert s.thinking_enabled == True
    assert s.mcp_clients == ()

# Sonnet Patch #3: HEP context fields
def test_app_state_hep_fields():
    s = AppState()
    assert s.hep_context == {}
    assert s.condor_jobs == []

def test_with_update_preserves_new_fields():
    s = AppState(session_id="s1", total_cost_usd=1.5)
    s2 = s.with_update(input_tokens=100)
    assert s2.session_id == "s1"
    assert s2.total_cost_usd == 1.5
    assert s2.input_tokens == 100
```

**Step 2-5: Implement, test, commit.**

---

### Task 4: Update existing tools to new protocol

**Files:**
- Modify: `src/cascade/tools/bash_tool.py`
- Modify: `src/cascade/tools/file_tools.py`
- Modify: `src/cascade/tools/search_tools.py`
- Modify: `src/cascade/tools/registry.py`
- Modify: `src/cascade/engine/query.py` (pass ToolUseContext)
- Test: `tests/test_tool_migration.py`

**Core change:** All `execute(**kwargs)` → `execute(input: dict, context: ToolUseContext)`. Registry and QueryEngine build and pass the context.

### Task 2.5: HEPDataTool (Sonnet Patch #13)

**Files:**
- Create: `src/cascade/tools/hep/hepdata.py`
- Test: `tests/test_hepdata_tool.py`
- Dependencies: `pip install hepdata-cli`

**Step 1: Write the failing test**

```python
# tests/test_hepdata_tool.py
import pytest
from cascade.tools.hep.hepdata import HEPDataTool

def test_hepdata_tool_metadata():
    t = HEPDataTool()
    assert t.name == "hepdata"
    assert t.domain == "hep"
    assert t.is_read_only is True

def test_hepdata_schema_is_valid_json_schema():
    """model_json_schema() must produce LLM tool-call compatible schema."""
    t = HEPDataTool()
    schema = t.get_input_schema()
    assert schema["type"] == "object"
    assert "action" in schema["properties"]
    assert "query" in schema["properties"]

@pytest.mark.asyncio
async def test_hepdata_find_action():
    from cascade.types.context import ToolUseContext
    t = HEPDataTool()
    ctx = ToolUseContext(cwd="/tmp")
    result = await t.execute(
        {"action": "find", "query": "ttH"},
        ctx,
    )
    # Should return ToolResult (may be empty if no network)
    assert hasattr(result, 'output')
```

**Step 2: Run test → FAIL**

**Step 3: Write implementation**

```python
# src/cascade/tools/hep/hepdata.py
"""HEPDataTool — search and download HEPData records.

Wraps hepdata_cli.api.Client for find/download/fetch_names.
"""
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field
from cascade.tools.base import BaseTool, ToolResult


class HEPDataInput(BaseModel):
    model_config = {"extra": "ignore"}  # LLM may hallucinate extra fields
    action: Literal["find", "download", "fetch_names"] = "find"
    query: str = ""
    record_id: int | None = None
    output_dir: str = "/tmp/hepdata"


class HEPDataTool(BaseTool):
    @property
    def name(self) -> str: return "hepdata"
    @property
    def description(self) -> str: return "Search and download HEPData records"
    @property
    def domain(self) -> Literal["general", "hep", "cms", "pheno"]: return "hep"
    @property
    def is_read_only(self) -> bool: return True

    def get_input_schema(self) -> dict:
        return HEPDataInput.model_json_schema()

    async def execute(self, input: dict[str, Any], context: Any) -> ToolResult:
        try:
            from hepdata_cli.api import Client
        except ImportError:
            return ToolResult(output="hepdata-cli not installed. Run: pip install hepdata-cli", is_error=True)

        parsed = HEPDataInput(**input)
        client = Client()

        if parsed.action == "find":
            results = client.find(parsed.query)
            return ToolResult(output=str(results))
        elif parsed.action == "download":
            if not parsed.record_id:
                return ToolResult(output="record_id required for download", is_error=True)
            client.download(parsed.record_id, parsed.output_dir)
            return ToolResult(output=f"Downloaded record {parsed.record_id} to {parsed.output_dir}")
        elif parsed.action == "fetch_names":
            if not parsed.record_id:
                return ToolResult(output="record_id required for fetch_names", is_error=True)
            names = client.fetch_names(parsed.record_id)
            return ToolResult(output=str(names))
        return ToolResult(output=f"Unknown action: {parsed.action}", is_error=True)
```

**Step 4: Run test → PASS**

**Step 5: Commit**

```bash
git commit -m "feat(tools): add HEPDataTool with Pydantic schema — Phase 1 Task 2.5"
```

---

## Phase 2: QueryEngine v2 — Session-Aware Query Loop (v0.5.0)

### 对标 Claude Code 源码

| Claude Code 文件 | 大小 | Cascade 对应 | 做什么 |
|---|---|---|---|
| `src/QueryEngine.ts` | 47K | `src/cascade/engine/query.py` | 核心 agentic loop — AsyncGenerator event protocol |
| `src/query/` (4 files) | 24K | `src/cascade/engine/events.py` | Stop hooks, token budget, query config |
| `src/cost-tracker.ts` | 11K | `src/cascade/services/cost_tracker.py` | Per-model usage tracking + USD cost |
| `src/utils/sessionStorage.ts` | 181K | `src/cascade/services/session_storage.py` | JSONL transcript recording + resume |
| `src/utils/messages.ts` | 193K | (消息处理逻辑分布在 engine 中) | Message serialization/filtering |

### 🔀 交叉借鉴: Gemini CLI

| Gemini CLI 文件 | 路径 | 大小 | Cascade 对应 | 做什么 |
|---|---|---|---|---|
| `agent-session.ts` | `/Users/ky230/Desktop/Private/Workspace/Git/gemini-cli/packages/core/src/agent/agent-session.ts` | 6K | `src/cascade/engine/query.py` (会话管理部分) | Gemini 将会话管理与事件翻译分离，更干净 |
| `event-translator.ts` | `/Users/ky230/Desktop/Private/Workspace/Git/gemini-cli/packages/core/src/agent/event-translator.ts` | 12K | `src/cascade/engine/event_translator.py` **[NEW]** | 将 API 响应翻译为统一内部事件，解耦 provider 差异 |

---

### Task 5: Engine Event Protocol

**Files:**
- Create: `src/cascade/engine/events.py`
- Test: `tests/test_engine_events.py`

### Task 5.5: EventTranslator — Provider 响应翻译层 🔀

> **借鉴来源:** Gemini CLI `event-translator.ts` (12K)
> **源码路径:** `/Users/ky230/Desktop/Private/Workspace/Git/gemini-cli/packages/core/src/agent/event-translator.ts`
>
> **设计动机:** Claude Code 的 `QueryEngine.ts` 是 47K 的单体巨石，所有 provider 的响应解析逻辑混在一起。Gemini CLI 将其拆分为 `agent-session.ts`（纯会话管理）+ `event-translator.ts`（API 响应 → 标准事件的翻译）。
>
> Cascade 需要支持 9 个 provider（DeepSeek/GLM/Anthropic/Gemini/OpenAI/xAI/MiniMax/Kimi/Qwen），每家的 streaming chunk 格式不同。有了 translator 层，新增 provider 只需写一个新 translator，不用碰核心 engine。

> [!NOTE]
> **Sonnet Patch #6:** EventTranslator 增强 — 集成 Tool Call JSON 纠错逻辑，处理 CN API（如 DeepSeek/GLM/Kimi）的畸形 JSON 输出（截断、多余逗号、缺少括号等）。具体实现：在 `ProviderTranslator.translate_chunk()` 中对 `arguments` 字段做 `json.loads()` 容错，失败时尝试修复常见格式错误。

**Files:**
- Create: `src/cascade/engine/event_translator.py`
- Test: `tests/test_event_translator.py`

**Step 1: Write the failing test**

```python
# tests/test_event_translator.py
import pytest
from cascade.engine.event_translator import EventTranslator, ProviderTranslator
from cascade.engine.events import TextDeltaEvent, ToolCallEvent, DoneEvent

class MockOpenAITranslator(ProviderTranslator):
    """Translates OpenAI-compatible streaming chunks."""
    def translate_chunk(self, chunk: dict) -> list:
        events = []
        for choice in chunk.get("choices", []):
            delta = choice.get("delta", {})
            if "content" in delta and delta["content"]:
                events.append(TextDeltaEvent(text=delta["content"]))
            if "tool_calls" in delta:
                for tc in delta["tool_calls"]:
                    events.append(ToolCallEvent(
                        id=tc.get("id", ""),
                        name=tc.get("function", {}).get("name", ""),
                        arguments_json=tc.get("function", {}).get("arguments", ""),
                    ))
            if choice.get("finish_reason"):
                events.append(DoneEvent(stop_reason=choice["finish_reason"]))
        return events

def test_translator_registry():
    et = EventTranslator()
    et.register("openai", MockOpenAITranslator())
    assert "openai" in et.providers

def test_translate_text_chunk():
    et = EventTranslator()
    et.register("openai", MockOpenAITranslator())
    chunk = {"choices": [{"delta": {"content": "hello"}, "finish_reason": None}]}
    events = et.translate("openai", chunk)
    assert len(events) == 1
    assert isinstance(events[0], TextDeltaEvent)
    assert events[0].text == "hello"

def test_translate_tool_call_chunk():
    et = EventTranslator()
    et.register("openai", MockOpenAITranslator())
    chunk = {"choices": [{"delta": {"tool_calls": [{"id": "tc1", "function": {"name": "bash", "arguments": '{"cmd": "ls"}'}}]}, "finish_reason": None}]}
    events = et.translate("openai", chunk)
    assert len(events) == 1
    assert isinstance(events[0], ToolCallEvent)

def test_translate_unknown_provider_raises():
    et = EventTranslator()
    with pytest.raises(KeyError):
        et.translate("unknown", {})
```

**Step 2: Run test → FAIL**

**Step 3: Write implementation**

```python
# src/cascade/engine/event_translator.py
"""EventTranslator — decouples provider-specific API response formats from the core engine.

Inspired by Gemini CLI's event-translator.ts which separates session management
from response translation. Each provider registers a ProviderTranslator that
converts raw streaming chunks into unified internal events.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from cascade.engine.events import EngineEvent


class ProviderTranslator(ABC):
    """Abstract translator for a specific API provider's streaming format."""

    @abstractmethod
    def translate_chunk(self, chunk: dict[str, Any]) -> list[EngineEvent]:
        """Convert a raw provider chunk into a list of unified EngineEvents."""
        ...


class EventTranslator:
    """Registry of per-provider translators."""

    def __init__(self) -> None:
        self._translators: dict[str, ProviderTranslator] = {}

    @property
    def providers(self) -> dict[str, ProviderTranslator]:
        return self._translators

    def register(self, provider: str, translator: ProviderTranslator) -> None:
        self._translators[provider] = translator

    def translate(self, provider: str, chunk: dict[str, Any]) -> list[EngineEvent]:
        return self._translators[provider].translate_chunk(chunk)
```

**Step 4: Run test → PASS**

**Step 5: Commit**

```bash
git commit -m "feat(engine): add EventTranslator for provider-agnostic chunk translation — Phase 2 Task 5.5"
```

### Task 6: QueryEngine v2 — AsyncGenerator Rewrite

**Files:**
- Modify: `src/cascade/engine/query.py`
- Modify: `src/cascade/ui/textual_app.py` (`_run_generation` → event consumer)
- Test: `tests/test_query_engine_v2.py`

### Task 7: Cost Tracker Service

**Files:**
- Create: `src/cascade/services/cost_tracker.py`
- Test: `tests/test_cost_tracker.py`

### Task 8: Session Persistence (Transcript Recording)

**Files:**
- Create: `src/cascade/services/session_storage.py`
- Test: `tests/test_session_storage.py`

```
~/.cascade/sessions/<session_id>/transcript.jsonl
```

> [!NOTE]
> **Sonnet Patch #4:** Session JSON 新增 `hep_snapshot: dict` 字段。Session resume 时直接读缓存，不重新检测 HEP 环境（避免在非 lxplus 节点 resume 时因缺少 CMSSW 而报错）。

### Task 8.5: SemanticRouter (Sonnet Patch #11)

**Files:**
- Create: `src/cascade/engine/router.py`
- Test: `tests/test_semantic_router.py`

**设计决策：**
- 放在 `_execute_prompt()` 入口，入队后分类，对 input-queue 透明
- 分类：`knowledge` → 跳过 Tool loop，单次 API 调用；`action` → 走完整 Agentic loop
- 实现：轻量规则分类器，后期可升级为小模型

```python
# tests/test_semantic_router.py
import pytest
from cascade.engine.router import SemanticRouter, QueryIntent

def test_knowledge_query():
    router = SemanticRouter()
    intent = router.classify("What is the Higgs boson mass?")
    assert intent == QueryIntent.KNOWLEDGE

def test_action_query():
    router = SemanticRouter()
    intent = router.classify("Create a file called test.py with hello world")
    assert intent == QueryIntent.ACTION

def test_ambiguous_defaults_to_action():
    router = SemanticRouter()
    intent = router.classify("Fix the bug in my code")
    assert intent == QueryIntent.ACTION
```

```python
# src/cascade/engine/router.py
"""SemanticRouter — classifies user input to optimize query execution path.

Knowledge queries skip the tool loop for faster responses.
Action queries go through the full agentic tool loop.
"""
from __future__ import annotations
from enum import Enum
import re


class QueryIntent(str, Enum):
    KNOWLEDGE = "knowledge"
    ACTION = "action"


class SemanticRouter:
    """Lightweight rule-based classifier. Upgradeable to small model later."""

    # Patterns that indicate knowledge-only queries
    KNOWLEDGE_PATTERNS = [
        r"^(what|who|when|where|why|how|explain|describe|define)\b",
        r"\?$",
        r"^(tell me|summarize|list)\b",
    ]

    # Patterns that force action classification
    ACTION_PATTERNS = [
        r"\b(create|write|edit|modify|delete|run|execute|fix|refactor|deploy)\b",
        r"\b(file|directory|folder|script|code|commit|push|build)\b",
    ]

    def classify(self, user_input: str) -> QueryIntent:
        lower = user_input.strip().lower()

        # Action patterns take priority
        for pat in self.ACTION_PATTERNS:
            if re.search(pat, lower):
                return QueryIntent.ACTION

        for pat in self.KNOWLEDGE_PATTERNS:
            if re.search(pat, lower):
                return QueryIntent.KNOWLEDGE

        # Default to action (safer — includes tool access)
        return QueryIntent.ACTION
```

**Commit:**

```bash
git commit -m "feat(engine): add SemanticRouter for query classification — Phase 2 Task 8.5"
```

---

## Phase 3: API Abstraction & Provider Layer (v0.6.0)

### 对标 Claude Code 源码

| Claude Code 文件 | 大小 | Cascade 对应 | 做什么 |
|---|---|---|---|
| `src/services/api/` | 目录 | `src/cascade/services/providers/` | Provider 抽象层 |
| `src/utils/api.ts` | 26K | `src/cascade/services/providers/litellm_provider.py` | API 调用封装 |
| `src/utils/config.ts` | 63K | `src/cascade/config/config.py` | multi-scope 配置系统 |
| `src/utils/claudemd.ts` | 46K | (Phase 7 CASCADE.md) | 项目规则解析 |
| `src/utils/model/` | 目录 | `src/cascade/services/model_config.py` | 模型别名/定价/能力 |

---

### Task 9: Provider Protocol & Refactor

**Files:**
- Create: `src/cascade/services/providers/__init__.py`
- Create: `src/cascade/services/providers/base.py`
- Create: `src/cascade/services/providers/litellm_provider.py`
- Create: `src/cascade/services/providers/direct_providers.py`
- Modify: `src/cascade/services/api_client.py` → thin orchestrator
- Test: `tests/test_providers.py`

### Task 10: Multi-Scope Configuration System

**Files:**
- Create: `src/cascade/config/__init__.py`
- Create: `src/cascade/config/config.py`
- Test: `tests/test_config.py`

```python
# Resolution order: CLI args > env vars > .cascade/config.json > ~/.cascade/config.json > defaults
```

> [!NOTE]
> **Sonnet Patch #5 — Config HEP 块 + API 防御层：**
> - 配置新增 `[hep]` section：`lxplus_host = "lxplus.cern.ch"`, `default_proxy_hours = 192`, `das_limit = 100`, `eos_mount = "/eos/cms"`
> - API 层加 Exponential Backoff（429/503 最大5次指数退避）
> - Engine 层加 Tool Call JSON 纠错防御层（处理 CN API 畸形输出）

### Task 10.5: ModelConfigService — 模型能力元数据 🔀

> **借鉴来源:** Gemini CLI `ModelConfigService` (560 行) + `models.ts` (464 行)
> **源码路径:**
> - `/Users/ky230/Desktop/Private/Workspace/Git/gemini-cli/packages/core/src/services/modelConfigService.ts`
> - `/Users/ky230/Desktop/Private/Workspace/Git/gemini-cli/packages/core/src/config/models.ts`
>
> **设计动机:** Claude Code 的模型信息硬编码分散在代码中。Gemini CLI 有一个完整的 `ModelConfigService`：
> - 每个模型带 `tier` (pro/flash/custom)、`family` (gemini-3)、`features` (thinking/multimodal) 元数据
> - 支持 alias chain（`auto` → `pro` → `gemini-3-pro-preview`）以及层级化 override
> - Cascade 有 40+ 模型 across 9 providers，需要结构化管理模型能力差异

**Files:**
- Create: `src/cascade/services/model_config.py`
- Test: `tests/test_model_config.py`

**Step 1: Write the failing test**

```python
# tests/test_model_config.py
from cascade.services.model_config import ModelConfigService, ModelDefinition

def test_register_and_get_model():
    svc = ModelConfigService()
    svc.register(ModelDefinition(
        id="deepseek-chat",
        display_name="DeepSeek V3",
        provider="deepseek",
        tier="standard",
        features={"thinking": False, "tool_use": True},
        pricing={"input_per_1m": 0.27, "output_per_1m": 1.10},
    ))
    defn = svc.get("deepseek-chat")
    assert defn is not None
    assert defn.display_name == "DeepSeek V3"
    assert defn.features["tool_use"] is True

def test_alias_resolution():
    svc = ModelConfigService()
    svc.register(ModelDefinition(
        id="deepseek-reasoner",
        display_name="DeepSeek R1",
        provider="deepseek",
        tier="reasoning",
    ))
    svc.register_alias("r1", "deepseek-reasoner")
    assert svc.resolve("r1") == "deepseek-reasoner"

def test_list_by_provider():
    svc = ModelConfigService()
    svc.register(ModelDefinition(id="m1", provider="openai"))
    svc.register(ModelDefinition(id="m2", provider="deepseek"))
    svc.register(ModelDefinition(id="m3", provider="openai"))
    openai_models = svc.list_by_provider("openai")
    assert len(openai_models) == 2

def test_unknown_model_returns_none():
    svc = ModelConfigService()
    assert svc.get("nonexistent") is None
```

**Step 2: Run test → FAIL**

**Step 3: Write implementation**

```python
# src/cascade/services/model_config.py
"""ModelConfigService — structured model capability metadata.

Inspired by Gemini CLI's ModelConfigService which provides model definitions,
alias chains, and tier-based resolution. Cascade adapts this for multi-provider
support (9 providers, 40+ models).
"""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class ModelDefinition(BaseModel):
    id: str = ""
    display_name: str = ""
    provider: str = ""
    tier: str = "standard"  # standard / reasoning / flash / lite / custom
    features: dict[str, bool] = Field(default_factory=dict)
    pricing: dict[str, float] = Field(default_factory=dict)


class ModelConfigService:
    def __init__(self) -> None:
        self._models: dict[str, ModelDefinition] = {}
        self._aliases: dict[str, str] = {}

    def register(self, defn: ModelDefinition) -> None:
        self._models[defn.id] = defn

    def register_alias(self, alias: str, model_id: str) -> None:
        self._aliases[alias] = model_id

    def resolve(self, name: str) -> str:
        return self._aliases.get(name, name)

    def get(self, model_id: str) -> ModelDefinition | None:
        resolved = self.resolve(model_id)
        return self._models.get(resolved)

    def list_by_provider(self, provider: str) -> list[ModelDefinition]:
        return [m for m in self._models.values() if m.provider == provider]

    def list_all(self) -> list[ModelDefinition]:
        return list(self._models.values())
```

**Step 4: Run test → PASS**

**Step 5: Commit**

```bash
git commit -m "feat(services): add ModelConfigService with alias resolution — Phase 3 Task 10.5"
```

### Task 10.6: ProjectRegistry — 项目自动发现与短 ID 映射 🔀

> **借鉴来源:** Gemini CLI `ProjectRegistry` (322 行)
> **源码路径:** `/Users/ky230/Desktop/Private/Workspace/Git/gemini-cli/packages/core/src/config/projectRegistry.ts`
>
> **设计动机:** Gemini CLI 维护一个持久化的「项目路径 → 短 ID」映射表（如 `/Users/ky230/.../Cascade` → `cascade`），支持文件锁防并发、跨会话复用。
>
> 对 Cascade 的价值：Session Resume (P8) 需要用短 ID 标识项目（而不是完整绝对路径），方便 `/resume` 列表展示和用户选择。

**Files:**
- Create: `src/cascade/config/project_registry.py`
- Test: `tests/test_project_registry.py`

**Step 1: Write the failing test**

```python
# tests/test_project_registry.py
import tempfile
import os
from cascade.config.project_registry import ProjectRegistry

def test_get_short_id_basic():
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = os.path.join(tmpdir, "registry.json")
        reg = ProjectRegistry(registry_path)
        sid = reg.get_short_id("/Users/ky230/Desktop/Private/Workspace/Git/Cascade")
        assert sid == "cascade"

def test_same_project_returns_same_id():
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = os.path.join(tmpdir, "registry.json")
        reg = ProjectRegistry(registry_path)
        sid1 = reg.get_short_id("/some/path/my-project")
        sid2 = reg.get_short_id("/some/path/my-project")
        assert sid1 == sid2

def test_different_projects_get_different_ids():
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = os.path.join(tmpdir, "registry.json")
        reg = ProjectRegistry(registry_path)
        sid1 = reg.get_short_id("/path/a/project")
        sid2 = reg.get_short_id("/path/b/project")
        # Same basename but different paths → suffixed
        assert sid1 != sid2

def test_persistence_across_instances():
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = os.path.join(tmpdir, "registry.json")
        reg1 = ProjectRegistry(registry_path)
        sid = reg1.get_short_id("/path/to/test-proj")
        # New instance should load from disk
        reg2 = ProjectRegistry(registry_path)
        assert reg2.get_short_id("/path/to/test-proj") == sid
```

**Step 2: Run test → FAIL**

**Step 3: Write implementation**

```python
# src/cascade/config/project_registry.py
"""ProjectRegistry — maps absolute project paths to short, human-readable identifiers.

Inspired by Gemini CLI's ProjectRegistry which maintains a persistent
path→slug mapping with file-lock safety for concurrent access.

Cascade uses this for session resume display and project-scoped config.
"""
from __future__ import annotations
import json
import os
import re


class ProjectRegistry:
    def __init__(self, registry_path: str) -> None:
        self._path = registry_path
        self._data: dict[str, str] = self._load()

    def _load(self) -> dict[str, str]:
        if not os.path.exists(self._path):
            return {}
        try:
            with open(self._path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        tmp = self._path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self._data, f, indent=2)
        os.replace(tmp, self._path)

    def _slugify(self, text: str) -> str:
        slug = re.sub(r"[^a-z0-9]", "-", text.lower())
        slug = re.sub(r"-+", "-", slug).strip("-")
        return slug or "project"

    def get_short_id(self, project_path: str) -> str:
        norm = os.path.normpath(os.path.abspath(project_path))
        if norm in self._data:
            return self._data[norm]

        base = os.path.basename(norm) or "project"
        slug = self._slugify(base)
        existing_ids = set(self._data.values())

        candidate = slug
        counter = 1
        while candidate in existing_ids:
            candidate = f"{slug}-{counter}"
            counter += 1

        self._data[norm] = candidate
        self._save()
        return candidate

    def list_projects(self) -> dict[str, str]:
        return dict(self._data)
```

**Step 4: Run test → PASS**

**Step 5: Commit**

```bash
git commit -m "feat(config): add ProjectRegistry with persistent slug mapping — Phase 3 Task 10.6"
```

---

## Phase 4: MCP Client Integration (v0.7.0)

### 对标 Claude Code 源码

| Claude Code 文件 | 大小 | Cascade 对应 | 做什么 |
|---|---|---|---|
| `src/services/mcp/client.ts` | 119K | `src/cascade/services/mcp/client.py` | MCP 客户端核心 |
| `src/services/mcp/config.ts` | 51K | `src/cascade/services/mcp/config.py` | MCP server 配置 |
| `src/services/mcp/types.ts` | 7K | `src/cascade/services/mcp/types.py` | MCP 类型定义 |
| `src/services/mcp/useManageMCPConnections.ts` | 45K | `src/cascade/services/mcp/manager.py` | 连接生命周期管理 |
| `src/tools/MCPTool/` | 目录 | `src/cascade/services/mcp/tool_bridge.py` | MCP→BaseTool 适配 |

---

### Task 11: MCP Client Core

**Files:**
- Create: `src/cascade/services/mcp/client.py`
- Create: `src/cascade/services/mcp/config.py`
- Create: `src/cascade/services/mcp/types.py`
- Create: `src/cascade/services/mcp/manager.py`
- Test: `tests/test_mcp_client.py`

### Task 12: MCP Tool Bridge

**Files:**
- Create: `src/cascade/services/mcp/tool_bridge.py`
- Test: `tests/test_mcp_tool_bridge.py`

### Task 12.5: MCP Edge Case Test Matrix 🔀

> **借鉴来源:** Gemini CLI MCP 测试套件（测试代码量超过实现代码量）
> **源码路径:**
> - `/Users/ky230/Desktop/Private/Workspace/Git/gemini-cli/packages/core/src/tools/mcp-client.test.ts` (92K)
> - `/Users/ky230/Desktop/Private/Workspace/Git/gemini-cli/packages/core/src/tools/mcp-client-manager.test.ts` (31K)
> - `/Users/ky230/Desktop/Private/Workspace/Git/gemini-cli/packages/core/src/tools/mcp-tool.test.ts` (36K)
>
> **设计动机:** Claude Code 的 MCP 实现分散在 23 个文件中，测试覆盖不够集中。Gemini CLI 的 MCP 测试比实现代码还大（159K test vs 117K impl），覆盖了大量边界场景。
>
> Cascade 直接参考 Gemini 的测试用例来设计 MCP 测试矩阵，不用自己猜边界条件。

**Files:**
- Create: `tests/test_mcp_edge_cases.py`

**Test Matrix (参考 Gemini CLI 测试覆盖):**

```python
# tests/test_mcp_edge_cases.py
"""MCP edge case test matrix — inspired by Gemini CLI's exhaustive MCP test suite.

Covers scenarios from gemini-cli mcp-client.test.ts (92K):
- Connection lifecycle
- Schema validation
- Tool naming conflicts
- Concurrent operations
- Error recovery
"""
import pytest

# --- Connection Lifecycle ---

class TestMCPConnectionLifecycle:
    async def test_connect_timeout(self):
        """MCP server fails to respond within timeout."""
        ...

    async def test_reconnect_after_disconnect(self):
        """Auto-reconnect when server drops connection."""
        ...

    async def test_graceful_shutdown(self):
        """Clean disconnect on session end."""
        ...

    async def test_connect_to_nonexistent_server(self):
        """Server binary doesn't exist → clear error message."""
        ...

# --- Schema Validation ---

class TestMCPSchemaValidation:
    async def test_invalid_tool_schema_from_server(self):
        """Server returns malformed JSON schema → skip tool, log warning."""
        ...

    async def test_empty_tool_list(self):
        """Server has no tools → no crash."""
        ...

    async def test_tool_schema_missing_required_fields(self):
        """Schema lacks 'type' field → validation error."""
        ...

# --- Tool Naming ---

class TestMCPToolNaming:
    async def test_tool_name_conflict_across_servers(self):
        """Two servers expose same tool name → namespaced."""
        ...

    async def test_tool_name_sanitization(self):
        """Special chars in tool names → sanitized."""
        ...

# --- Concurrent Operations ---

class TestMCPConcurrency:
    async def test_parallel_tool_calls_to_same_server(self):
        """Multiple concurrent calls → all complete."""
        ...

    async def test_server_crash_during_tool_call(self):
        """Server crashes mid-execution → error result, not crash."""
        ...

# --- Error Recovery ---

class TestMCPErrorRecovery:
    async def test_server_returns_error_result(self):
        """Server returns isError=True → ToolResult.is_error=True."""
        ...

    async def test_server_returns_oversized_result(self):
        """Result exceeds max_result_size_chars → truncated."""
        ...
```

**Step: Implement stubs → fill as MCP client is built**

**Commit:**

```bash
git commit -m "test(mcp): add edge case test matrix from Gemini CLI patterns — Phase 4 Task 12.5"
```

> [!NOTE]
> **Sonnet Patch #10 — MCP HTCondor 验收条件：**
> - 必须实现 `Mock_HTCondor_MCP_Server`（模拟 condor_q / condor_status 输出）
> - 跑通 Condor 队列查询端到端测试
> - 通不过不算完工

---

## Phase 5: Context Management & Token Budget (v0.8.0)

### 对标 Claude Code 源码

| Claude Code 文件 | 大小 | Cascade 对应 | 做什么 |
|---|---|---|---|
| `src/services/tokenEstimation.ts` | 17K | `src/cascade/services/token_estimation.py` | 快速 token 估算 |
| `src/services/compact/compact.ts` | 61K | `src/cascade/services/compact/compactor.py` | Context compaction 核心逻辑 |
| `src/services/compact/autoCompact.ts` | 13K | `src/cascade/services/compact/compactor.py` | 自动压缩触发 |
| `src/services/compact/prompt.ts` | 16K | `src/cascade/services/compact/summarizer.py` | 压缩使用的 prompt |
| `src/query/tokenBudget.ts` | 2K | `src/cascade/services/token_estimation.py` | Token budget 计算 |
| `src/utils/toolResultStorage.ts` | 38K | `src/cascade/services/tool_result_storage.py` | 大结果保存到磁盘 |
| `src/utils/tokenBudget.ts` | 3K | (合并到 token_estimation) | Token budget 辅助 |

---

### Task 13: Token Estimation Service

**Files:**
- Create: `src/cascade/services/token_estimation.py`
- Test: `tests/test_token_estimation.py`

### Task 14: Context Compaction Service

**Files:**
- Create: `src/cascade/services/compact/__init__.py`
- Create: `src/cascade/services/compact/compactor.py`
- Create: `src/cascade/services/compact/summarizer.py`
- Test: `tests/test_compactor.py`

### Task 15: Tool Result Size Management

**Files:**
- Create: `src/cascade/services/tool_result_storage.py`
- Modify: `src/cascade/tools/base.py` — enforce `max_result_size_chars`
- Test: `tests/test_tool_result_storage.py`

> [!NOTE]
> **Sonnet Patch #9 — HEP 感知压缩策略：**
> `compactor.py` 新增 HEP 感知压缩规则：
> - `.root` error trace → 保留完整错误行
> - HTCondor 队列报错 → 提取关键状态行
> - CMSSW 编译错误 → 保留 error/warning 行

### Task 15.5: Streaming Tool Execution (Sonnet Patch #7)

> **Phase 5.5: v0.8.5**

**Files:**
- Modify: `src/cascade/tools/bash_tool.py` — 改造为 `AsyncGenerator`
- Create: `src/cascade/engine/events.py` — 新增 `ToolOutputDeltaEvent`
- Modify: `src/cascade/engine/query.py` — 处理 AsyncGenerator 返回值
- Test: `tests/test_streaming_tool.py`

**关键设计决策：**
- BashTool.execute() 返回 `AsyncGenerator[str, None]`，实时截获 stdout/stderr
- 新增 `ToolOutputDeltaEvent`，走现有 `EngineEvent` 管道
- ⚠️ 不新建 EventBus，复用现有 AsyncGenerator pipeline
- 测试：10秒 sleep 命令，验证每秒有输出推送

```python
# tests/test_streaming_tool.py
import pytest
import asyncio
from cascade.tools.bash_tool import BashTool
from cascade.types.context import ToolUseContext

@pytest.mark.asyncio
async def test_bash_streaming_output():
    """BashTool should yield output incrementally."""
    tool = BashTool()
    ctx = ToolUseContext(cwd="/tmp")
    result = await tool.execute(
        {"command": "for i in 1 2 3; do echo $i; sleep 0.1; done", "timeout": 5},
        ctx,
    )
    # If AsyncGenerator, collect chunks
    if hasattr(result, '__aiter__'):
        chunks = []
        async for chunk in result:
            chunks.append(chunk)
        assert len(chunks) >= 3
    else:
        # Fallback: still returns ToolResult
        assert "1" in result.output
```

---

## Phase 6: Advanced Permission System (v0.9.0)

### 对标 Claude Code 源码

| Claude Code 文件 | 大小 | Cascade 对应 | 做什么 |
|---|---|---|---|
| `src/types/permissions.ts` | 13K | `src/cascade/permissions/rules.py` | 权限规则类型定义 |
| `src/Tool.ts` L500-516 | — | `src/cascade/permissions/patterns.py` | Pattern matching (`Bash(git *)`) |
| `src/utils/permissions/` | 目录 | `src/cascade/permissions/` | 权限子系统 |
| `src/utils/permissions/denialTracking.ts` | — | `src/cascade/permissions/denial_tracking.py` | Denial 次数追踪 |

---

### Task 16: Rule-Based Permission Engine

**Files:**
- Modify: `src/cascade/permissions/engine.py`
- Create: `src/cascade/permissions/rules.py`
- Create: `src/cascade/permissions/patterns.py`
- Test: `tests/test_permission_rules.py`

> [!WARNING]
> **Sonnet Patch #8 — HEP 专属硬规则：**
> - `voms-proxy-init` → 永远需要用户确认，禁止 Auto Mode
> - `condor_rm` → 永远需要用户确认，禁止 Auto Mode
> - 引入 `bashlex` AST 级别命令分析：对 `/eos/`、`/cvmfs/`、`/afs/` 路径强制二次确认

### Task 16.5: ConfirmationBus — 异步权限事件总线 🔀

> **借鉴来源:** Gemini CLI `confirmation-bus/` (4 files, 23K)
> **源码路径:**
> - `/Users/ky230/Desktop/Private/Workspace/Git/gemini-cli/packages/core/src/confirmation-bus/types.ts` (6K)
> - `/Users/ky230/Desktop/Private/Workspace/Git/gemini-cli/packages/core/src/confirmation-bus/message-bus.ts` (6K)
> - `/Users/ky230/Desktop/Private/Workspace/Git/gemini-cli/packages/core/src/confirmation-bus/message-bus.test.ts` (11K)
>
> **设计动机:** Claude Code 的权限是同步阻塞的 — AI 请求权限 → UI 弹框 → 用户确认 → 继续。这在 Textual 的异步模型中容易造成 UI 冻结（Cascade Phase 8.5 中遇到过 `ask_user` 冻结 bug）。
>
> Gemini CLI 的 ConfirmationBus 完全解耦：engine 发 request 到 bus → UI 监听 bus 展示确认框 → 用户响应写回 bus → engine 从 bus 拿结果。支持 10 种消息类型、`forcedDecision`（强制放行/拒绝）、`UpdatePolicy`（记住用户选择）、rich confirmation details（diff 预览、MCP tool 详情）。
>
> **额外参考:** Codex CLI `execpolicy/` crate 提供了 OS 级沙箱隔离视角
> **Codex 路径:** `/Users/ky230/Desktop/Private/Workspace/Git/codex-cli/codex-rs/execpolicy/`

**Files:**
- Create: `src/cascade/permissions/confirmation_bus.py`
- Test: `tests/test_confirmation_bus.py`

**Step 1: Write the failing test**

```python
# tests/test_confirmation_bus.py
"""ConfirmationBus — async permission event bus.

Inspired by Gemini CLI's message-bus.ts which decouples permission requests
from UI handling via an event bus pattern.
"""
import pytest
import asyncio
from cascade.permissions.confirmation_bus import (
    ConfirmationBus, ConfirmationRequest, ConfirmationResponse,
    BusMessageType,
)

@pytest.mark.asyncio
async def test_request_and_respond():
    bus = ConfirmationBus()
    # Simulate engine sending a request
    req = ConfirmationRequest(
        correlation_id="req-1",
        tool_name="bash",
        tool_args={"command": "rm -rf /tmp/test"},
        details_type="exec",
    )
    # UI listener responds after a short delay
    async def mock_ui():
        await asyncio.sleep(0.01)
        bus.respond(ConfirmationResponse(
            correlation_id="req-1",
            confirmed=True,
        ))

    asyncio.create_task(mock_ui())
    result = await bus.request(req, timeout=1.0)
    assert result.confirmed is True

@pytest.mark.asyncio
async def test_request_timeout():
    bus = ConfirmationBus()
    req = ConfirmationRequest(
        correlation_id="req-timeout",
        tool_name="bash",
        tool_args={},
    )
    # No one responds → timeout
    result = await bus.request(req, timeout=0.05)
    assert result.confirmed is False  # Default deny on timeout

@pytest.mark.asyncio
async def test_forced_decision_bypasses_ui():
    bus = ConfirmationBus()
    req = ConfirmationRequest(
        correlation_id="req-forced",
        tool_name="file_read",
        tool_args={"path": "test.py"},
        forced_decision="allow",
    )
    result = await bus.request(req, timeout=0.05)
    assert result.confirmed is True  # Forced allow, no UI needed

@pytest.mark.asyncio
async def test_update_policy_message():
    bus = ConfirmationBus()
    policies = []
    bus.on_policy_update(lambda p: policies.append(p))
    bus.emit_policy_update(tool_name="bash", args_pattern="git *", persist=True)
    assert len(policies) == 1
    assert policies[0]["tool_name"] == "bash"
```

**Step 2: Run test → FAIL**

**Step 3: Write implementation**

```python
# src/cascade/permissions/confirmation_bus.py
"""ConfirmationBus — async event bus for tool permission requests.

Decouples the engine (which needs permission decisions) from the UI (which
presents confirmation dialogs). Inspired by Gemini CLI's confirmation-bus.

Flow:
  1. Engine calls bus.request(ConfirmationRequest) — non-blocking wait
  2. UI listens for requests and shows confirmation dialog
  3. UI calls bus.respond(ConfirmationResponse)
  4. Engine receives response and proceeds
"""
from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable
from enum import Enum


class BusMessageType(str, Enum):
    TOOL_CONFIRMATION_REQUEST = "tool-confirmation-request"
    TOOL_CONFIRMATION_RESPONSE = "tool-confirmation-response"
    UPDATE_POLICY = "update-policy"


@dataclass
class ConfirmationRequest:
    correlation_id: str
    tool_name: str
    tool_args: dict[str, Any] = field(default_factory=dict)
    details_type: str = ""  # exec / edit / mcp / info
    forced_decision: str | None = None  # allow / deny / None


@dataclass
class ConfirmationResponse:
    correlation_id: str
    confirmed: bool = False


class ConfirmationBus:
    def __init__(self) -> None:
        self._pending: dict[str, asyncio.Future[ConfirmationResponse]] = {}
        self._policy_callbacks: list[Callable] = []

    async def request(
        self, req: ConfirmationRequest, timeout: float = 30.0
    ) -> ConfirmationResponse:
        # Forced decisions bypass the bus entirely
        if req.forced_decision == "allow":
            return ConfirmationResponse(correlation_id=req.correlation_id, confirmed=True)
        if req.forced_decision == "deny":
            return ConfirmationResponse(correlation_id=req.correlation_id, confirmed=False)

        loop = asyncio.get_event_loop()
        future: asyncio.Future[ConfirmationResponse] = loop.create_future()
        self._pending[req.correlation_id] = future

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            return ConfirmationResponse(correlation_id=req.correlation_id, confirmed=False)
        finally:
            self._pending.pop(req.correlation_id, None)

    def respond(self, response: ConfirmationResponse) -> None:
        future = self._pending.get(response.correlation_id)
        if future and not future.done():
            future.set_result(response)

    def on_policy_update(self, callback: Callable) -> None:
        self._policy_callbacks.append(callback)

    def emit_policy_update(self, **kwargs: Any) -> None:
        for cb in self._policy_callbacks:
            cb(kwargs)
```

**Step 4: Run test → PASS**

**Step 5: Commit**

```bash
git commit -m "feat(permissions): add ConfirmationBus async event bus — Phase 6 Task 16.5"
```

### Task 17: Denial Tracking & Fallback

**Files:**
- Create: `src/cascade/permissions/denial_tracking.py`
- Test: `tests/test_denial_tracking.py`

---

## Phase 7: Hooks & CASCADE.md Rules (v0.10.0) — Cherry-Pick

### 对标 Claude Code 源码

| Claude Code 文件 | 大小 | Cascade 对应 | 做什么 |
|---|---|---|---|
| `src/utils/hooks/hookEvents.ts` | 4K | `src/cascade/hooks/events.py` | Hook 事件类型 |
| `src/utils/hooks/hooksSettings.ts` | 9K | `src/cascade/hooks/config.py` | Hook 配置管理 |
| `src/utils/hooks/hooksConfigManager.ts` | 17K | `src/cascade/hooks/manager.py` | Hook 注册+执行 |
| `src/utils/hooks/sessionHooks.ts` | 12K | `src/cascade/hooks/session_hooks.py` | 会话级临时 hooks |
| `src/utils/claudemd.ts` | 46K | `src/cascade/config/cascade_rules.py` | CASCADE.md 规则解析 |
| `src/utils/markdownConfigLoader.ts` | 21K | `src/cascade/config/cascade_rules.py` | Markdown 配置加载器 |
| `src/schemas/hooks.ts` | 8K | `src/cascade/hooks/schema.py` | Hook 配置 schema |

---

### Task 18: Hook Event System

**Files:**
- Create: `src/cascade/hooks/__init__.py`
- Create: `src/cascade/hooks/events.py`
- Create: `src/cascade/hooks/manager.py`
- Create: `src/cascade/hooks/config.py`
- Test: `tests/test_hooks.py`

**Supported events:** `SessionStart`, `PreToolUse`, `PostToolUse`, `PreCompact`
**Hook types:** `command` (run shell), `prompt` (inject to AI)

> [!IMPORTANT]
> **Sonnet Patch #14:** Phase 7 Hooks 按原计划保留，对标 Claude Code 源码，不降级不推迟。

### Task 19: CASCADE.md Rules Engine

**Files:**
- Create: `src/cascade/config/cascade_rules.py`
- Test: `tests/test_cascade_rules.py`

```
# Resolution: .cascade/CASCADE.md → ~/.cascade/CASCADE.md
# Sections: system prompt injection, permission overrides, tool config
```

---

## Phase 8: Session Resume & Loop Detection (v0.11.0) — Cherry-Pick

### 对标 Claude Code 源码

| Claude Code 文件 | 大小 | Cascade 对应 | 做什么 |
|---|---|---|---|
| `src/utils/sessionRestore.ts` | 20K | `src/cascade/services/session_resume.py` | `--resume` 恢复上次对话 |
| `src/commands/resume/` | 目录 | `src/cascade/commands/resume.py` | `/resume` slash command |
| `src/services/loopDetectionService.ts` (Gemini CLI) | 26K | `src/cascade/services/loop_detection.py` | 检测 AI 无限循环 |
| `src/utils/conversationRecovery.ts` | 21K | `src/cascade/services/session_resume.py` | 异常中断恢复 |

---

### Task 20: Session Resume

**Files:**
- Create: `src/cascade/services/session_resume.py`
- Create: `src/cascade/commands/session/resume.py`
- Test: `tests/test_session_resume.py`

### Task 21: Loop Detection Service

**Files:**
- Create: `src/cascade/services/loop_detection.py`
- Test: `tests/test_loop_detection.py`

```python
# Detect: same tool called with same args 3+ times in a row
# Action: inject system message warning, then hard-stop if 5+
```

---

## Phase 9: Daemon/Client 架构 (v0.15.0) — Sonnet Patch #12

> **独立 Phase，不在 v0.4.0-v0.11.0 范围内。** SSH 断开后任务继续的关键基础设施。

### Task 22: Cascade Daemon

**Files:**
- Create: `src/cascade/daemon/__init__.py`
- Create: `src/cascade/daemon/server.py`
- Test: `tests/test_daemon.py`

**设计要点：**
- 后台守护进程，SSH 断开后任务继续
- Unix socket 或本地端口通信
- 对 HEP 场景尤其关键：lxplus 上跑长时间 CRAB/Condor 任务时 SSH 经常断开

```python
# tests/test_daemon.py
import pytest

@pytest.mark.asyncio
async def test_daemon_start_stop():
    """Daemon should start and gracefully stop."""
    from cascade.daemon.server import CascadeDaemon
    daemon = CascadeDaemon(socket_path="/tmp/cascade-test.sock")
    # Start in background, verify socket created, stop
    ...

@pytest.mark.asyncio
async def test_daemon_accepts_prompt():
    """Client sends prompt, daemon processes and returns result."""
    ...
```

### Task 23: cascade attach — 重连命令

**Files:**
- Create: `src/cascade/daemon/client.py`
- Modify: `src/cascade/cli/main.py` — 新增 `cascade attach` 子命令
- Test: `tests/test_daemon_attach.py`

**设计要点：**
- 重连命令，恢复 TUI 到当前任务状态
- 显示断开期间的输出历史

```bash
git commit -m "feat(daemon): add Cascade daemon + attach — Phase 9"
```

---

## ⚙️ 工程备忘录 (Sonnet Patch #15)

> 无需单开 Phase，分散在各相关 Phase 实现。

### A. 异步文件 Logger

- **归属 Phase:** Phase 1
- **必须在 Phase 1 完成时实现**
- 日志输出到 `~/.cascade/debug.log`
- Textual 接管 stdout 后唯一的调试手段

```python
# src/cascade/bootstrap/logger.py
import logging
import os

def setup_debug_logger() -> logging.Logger:
    log_dir = os.path.expanduser("~/.cascade")
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger("cascade")
    handler = logging.FileHandler(os.path.join(log_dir, "debug.log"))
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger
```

### B. CLI `--headless` 参数

- **归属 Phase:** Phase 3 (CLI 入口重构时)
- 绕过 Textual，纯文本输出，支持 `grep`/`awk` 管道
- HEP 批处理脚本场景必需

```python
# src/cascade/cli/main.py 新增
@click.option("--headless", is_flag=True, help="Pure text output, no TUI")
def main(headless: bool = False, **kwargs):
    if headless:
        from cascade.cli.headless import run_headless
        run_headless(**kwargs)
    else:
        from cascade.ui.textual_app import CascadeApp
        app = CascadeApp()
        app.run()
```

### C. 打包策略

- **主推:** `pipx install cascade-hep`
- 文档明确禁止 `pip install` 污染系统环境
- 备选：PyInstaller/Nuitka 单文件二进制

---

## 📊 最终对齐汇总表: Cascade ↔ Claude Code `src/` + 交叉借鉴

### ✅ 已对齐模块 (Phase 1-9 完成后)

| 模块 | 主参考 (Claude Code) | 🔀 交叉借鉴 | Cascade 对应 | Phase |
|---|---|---|---|---|
| **Tool 系统** | `Tool.ts` (30K) | — | `tools/base.py` | P1 |
| **类型系统** | `types/message.ts`, `types/permissions.ts` | — | `types/message.py`, `types/permissions.py` | P1 |
| **状态管理** | `state/AppStateStore.ts` (22K), `state/store.ts` | — | `state/app_state.py`, `state/store.py` | P1 |
| **Query 引擎** | `QueryEngine.ts` (47K), `query/` (4 files) | — | `engine/query.py`, `engine/events.py` | P2 |
| **EventTranslator** | — | 🔀 Gemini `event-translator.ts` (12K) | `engine/event_translator.py` | P2 |
| **费用追踪** | `cost-tracker.ts` (11K) | — | `services/cost_tracker.py` | P2 |
| **会话存储** | `utils/sessionStorage.ts` (181K) | — | `services/session_storage.py` | P2 |
| **API 抽象** | `services/api/`, `utils/api.ts` (26K) | — | `services/providers/` | P3 |
| **配置系统** | `utils/config.ts` (63K), `utils/model/` | — | `config/config.py` | P3 |
| **ModelConfigService** | — | 🔀 Gemini `modelConfigService.ts` (18K) + `models.ts` (14K) | `services/model_config.py` | P3 |
| **ProjectRegistry** | — | 🔀 Gemini `projectRegistry.ts` (10K) | `config/project_registry.py` | P3 |
| **MCP 客户端** | `services/mcp/` (23 files, ~400K) | — | `services/mcp/` | P4 |
| **MCP 工具桥** | `tools/MCPTool/` | — | `services/mcp/tool_bridge.py` | P4 |
| **MCP 测试矩阵** | — | 🔀 Gemini `mcp-client.test.ts` (92K) + 2 test files | `tests/test_mcp_edge_cases.py` | P4 |
| **Token 估算** | `services/tokenEstimation.ts` (17K) | — | `services/token_estimation.py` | P5 |
| **Context 压缩** | `services/compact/` (11 files, ~145K) | — | `services/compact/` | P5 |
| **大结果存储** | `utils/toolResultStorage.ts` (38K) | — | `services/tool_result_storage.py` | P5 |
| **权限系统** | `types/permissions.ts`, `utils/permissions/` | — | `permissions/` | P6 |
| **ConfirmationBus** | — | 🔀 Gemini `confirmation-bus/` (23K) + Codex `execpolicy/` | `permissions/confirmation_bus.py` | P6 |
| **Hooks 系统** | `utils/hooks/` (17 files, ~115K) | — | `hooks/` | P7 |
| **CASCADE.md** | `utils/claudemd.ts` (46K), `utils/markdownConfigLoader.ts` (21K) | — | `config/cascade_rules.py` | P7 |
| **Session Resume** | `utils/sessionRestore.ts` (20K), `commands/resume/` | — | `services/session_resume.py` | P8 |
| **Loop Detection** | — | 🔀 Gemini `loopDetectionService.ts` (26K) | `services/loop_detection.py` | P8 |
| **HEPDataTool** | — | Sonnet Patch #13 | `tools/hep/hepdata.py` | P1 |
| **SemanticRouter** | — | Sonnet Patch #11 | `engine/router.py` | P2 |
| **Streaming Tool** | — | Sonnet Patch #7 | `tools/bash_tool.py` (AsyncGenerator) | P5.5 |
| **Daemon/Client** | — | Sonnet Patch #12 | `daemon/server.py`, `daemon/client.py` | P9 |
| **Commands 框架** | `commands.ts` (25K), `commands/` (router) | — | `commands/` (已有 router) | 已有 |
| **UI/TUI** | `main.tsx`, `components/` (React/Ink) | — | `ui/textual_app.py` (Textual) | 已有 |

### 🔀 交叉借鉴汇总

| Phase | 借鉴来源 | 源文件路径 | Cascade 新增 |
|---|---|---|---|
| **P2** | Gemini CLI | `gemini-cli/packages/core/src/agent/event-translator.ts` (12K) | `engine/event_translator.py` |
| **P3** | Gemini CLI | `gemini-cli/packages/core/src/services/modelConfigService.ts` (18K) | `services/model_config.py` |
| **P3** | Gemini CLI | `gemini-cli/packages/core/src/config/projectRegistry.ts` (10K) | `config/project_registry.py` |
| **P4** | Gemini CLI | `gemini-cli/packages/core/src/tools/mcp-client.test.ts` (92K) | `tests/test_mcp_edge_cases.py` |
| **P6** | Gemini CLI + Codex CLI | `gemini-cli/.../confirmation-bus/` (23K) + `codex-rs/execpolicy/` | `permissions/confirmation_bus.py` |
| **P8** | Gemini CLI | `gemini-cli/.../services/loopDetectionService.ts` (26K) | `services/loop_detection.py` |

---

### 📋 Claude Code `src/` 完整模块分类（按需求优先级排序）

#### 🟢 已纳入计划 (Phase 1-8)

| # | 模块 | 关键文件 | Phase |
|---|---|---|---|
| 1 | Tool 抽象 | `Tool.ts` | P1 |
| 2 | 类型系统 | `types/` (8 files) | P1 |
| 3 | 状态管理 | `state/` (6 files) | P1 |
| 4 | Query 引擎 | `QueryEngine.ts`, `query/` | P2 |
| 5 | 费用追踪 | `cost-tracker.ts` | P2 |
| 6 | 会话存储 | `utils/sessionStorage.ts` | P2 |
| 7 | API 客户端 | `services/api/`, `utils/api.ts` | P3 |
| 8 | 配置系统 | `utils/config.ts` | P3 |
| 9 | MCP 集成 | `services/mcp/` (23 files) | P4 |
| 10 | Token 估算 | `services/tokenEstimation.ts` | P5 |
| 11 | Context 压缩 | `services/compact/` (11 files) | P5 |
| 12 | 大结果存储 | `utils/toolResultStorage.ts` | P5 |
| 13 | 权限系统 | `utils/permissions/`, `types/permissions.ts` | P6 |
| 14 | Hooks 系统 | `utils/hooks/` (17 files) | P7 |
| 15 | CASCADE.md | `utils/claudemd.ts`, `utils/markdownConfigLoader.ts` | P7 |
| 16 | Session Resume | `utils/sessionRestore.ts`, `utils/conversationRecovery.ts` | P8 |

#### 🟡 未来可追加 (v2.0+ 按需)

| # | 模块 | 关键文件 | 为什么推迟 |
|---|---|---|---|
| 17 | Plugin 系统 | `plugins/builtinPlugins.ts`, `utils/plugins/` (目录), `services/plugins/` (目录) | 需要先完成 config + hooks 基础 |
| 18 | Skills 系统 | `skills/loadSkillsDir.ts` (34K), `skills/bundledSkills.ts` (7K), `skills/bundled/` | 需要先完成 hooks + CASCADE.md |
| 19 | Git 集成 | `utils/git.ts` (30K), `utils/gitDiff.ts` (16K), `utils/commitAttribution.ts` (30K) | 功能完整的 Git 工具对 HEP 不急需 |
| 20 | Worktree | `utils/worktree.ts` (50K), `utils/getWorktreePaths.ts` | 需要 Git 集成先完成 |
| 21 | 更多 Tools | `tools/FileEditTool/`, `tools/WebFetchTool/`, `tools/WebSearchTool/`, `tools/NotebookEditTool/`, `tools/GrepTool/`, `tools/GlobTool/`, `tools/LSPTool/` | 按需逐个添加 |
| 22 | Multi-Agent | `coordinator/`, `tasks/`, `Task.ts`, `tools/AgentTool/`, `tools/SendMessageTool/`, `tools/TaskCreateTool/` 等 6 个 task tools | 完整的多 Agent 系统，架构复杂 |
| 23 | 消息处理 | `utils/messages.ts` (193K), `utils/messageQueueManager.ts` (17K) | 可按需提取子功能 |

#### 🔴 不需要移植

| # | 模块 | 关键文件 | 原因 |
|---|---|---|---|
| 24 | React Hooks | `hooks/useTextInput.ts` (17K), `hooks/useTypeahead.tsx` (213K), `hooks/useVirtualScroll.ts` (35K), `hooks/useVoiceIntegration.tsx` (99K), `hooks/useReplBridge.tsx` (116K), `hooks/useCanUseTool.tsx` (40K) ＋ 其余 77 个 `use*.ts` files | React/Ink 框架专用，Textual 完全不适用 |
| 25 | React Components | `components/` 目录全部 | Ink UI 组件，Cascade 有自己的 Textual widgets |
| 26 | React Screens | `screens/` 目录全部 | Ink 页面组件 |
| 27 | Bridge 远程 | `bridge/` 目录全部, `hooks/useReplBridge.tsx`, `utils/teleport.tsx` (176K), `utils/teleport/` 目录 | claude.ai 桥接功能，Cascade 不需要 |
| 28 | Assistant 模式 | `assistant/` 目录全部, `hooks/useRemoteSession.ts` (23K), `remote/` 目录 | 远程守护进程模式 |
| 29 | 伴侣系统 | `buddy/` 目录全部 | 宠物动画功能 |
| 30 | Voice 语音 | `voice/` 目录全部, `hooks/useVoice.ts` (46K), `hooks/useVoiceIntegration.tsx` (99K), `services/voice.ts` (17K), `utils/voiceStreamSTT.ts` (21K) | 语音输入，CLI 不需要 |
| 31 | Vim 模式 | `vim/` 目录全部, `hooks/useVimInput.ts` (10K), `commands/vim/` | Vim 键位模拟，Textual 有自己的输入 |
| 32 | Ink 渲染器 | `ink/` 目录, `ink.ts`, `utils/ink.ts`, `utils/staticRender.tsx` | React Ink 底层，不适用 |
| 33 | OAuth/Auth | `services/oauth/` 目录, `utils/auth.ts` (65K), `utils/authFileDescriptor.ts` (7K) | Anthropic OAuth，Cascade 用 API key |
| 34 | Analytics 遥测 | `services/analytics/` 目录, `utils/telemetry/` 目录, `utils/diagnosticTracking.ts` (12K), `utils/stats.ts` (34K) | 匿名上报，不需要 |
| 35 | A/B 测试 | `moreright/` 目录全部 | 内部实验框架 |
| 36 | Native 绑定 | `native-ts/` 目录全部 | Node.js native addon |
| 37 | 代理服务器 | `upstreamproxy/` 目录全部 | 企业代理 |
| 38 | SDK Server | `server/` 目录全部 | SDK 服务器模式 |
| 39 | 多入口 | `entrypoints/` 目录全部 | CLI/SDK/Server 多入口 |
| 40 | main.tsx | `main.tsx` (804K) | React 入口文件，Cascade 用 `textual_app.py` |
| 41 | Prompt Suggest | `services/PromptSuggestion/` 目录, `hooks/usePromptSuggestion.ts` | 自动建议，锦上添花 |
| 42 | Auto Dream | `services/autoDream/` 目录 | 后台自动思考，实验性 |
| 43 | ANSI 转图片 | `utils/ansiToPng.ts` (215K), `utils/ansiToSvg.ts` (8K) | 终端截图导出 |
| 44 | Computer Use | `utils/computerUse/` 目录全部 | 屏幕操控 (Chicago MCP) |
| 45 | Swarm/Teams | `utils/swarm/` 目录, `utils/teammate.ts` (9K), `utils/teammateMailbox.ts` (33K), `utils/teammateContext.ts` (3K), `state/teammateViewHelpers.ts` (4K) | 多进程 Agent 群 |
| 46 | Cron 系统 | `utils/cron.ts` (9K), `utils/cronScheduler.ts` (21K), `utils/cronTasks.ts` (17K), `tools/ScheduleCronTool/` | 定时任务调度 |
| 47 | Keybindings | `keybindings/` 目录全部 | React 键位系统，Textual 有自己的 |
| 48 | 启动引导 | `bootstrap/state.ts` (56K) | Node.js 启动逻辑，Python 有自己的 |
| 49 | Stickers | `commands/stickers/` | 贴纸系统 |
| 50 | 深度链接 | `utils/deepLink/` 目录, `utils/desktopDeepLink.ts` | 桌面 app 深度链接 |
| 51 | Chrome 扩展 | `utils/claudeInChrome/` 目录, `hooks/useChromeExtensionNotification.tsx`, `commands/chrome/` | Chrome 浏览器扩展交互 |
| 52 | 输出样式 | `outputStyles/` 目录全部 | React 渲染样式 |
| 53 | Ultraplan | `commands/ultraplan.tsx` (67K), `utils/ultraplan/` 目录 | 高级计划执行模式 |
| 54 | 安全/沙箱 | `utils/sandbox/` 目录, `services/policyLimits/` 目录 | Anthropic 企业安全策略 |
| 55 | IDE 集成 | `utils/ide.ts` (47K), `hooks/useIDEIntegration.tsx` (11K), `commands/ide/` | VS Code 集成 |

---

## 📐 Verification Plan

### Automated Tests (每个 Phase)
```bash
pytest tests/ -v --tb=short
mypy src/cascade/ --ignore-missing-imports
```

### Integration Tests
- **Phase 2:** TUI 交互 — streaming + tool execution 不退化
- **Phase 4:** 连接 MCP server（如 filesystem server），验证 tool discovery
- **Phase 5:** 长会话测试 — 50+ 轮对话不爆 context
- **Phase 7:** 配置 PreToolUse hook，验证自动执行
- **Phase 8:** 中断 session → `--resume` → 恢复

---

## User Review Required

> [!IMPORTANT]
> 请确认此 v3 计划（32 Tasks，Phase 1-9）。确认后我会提供执行选项：
> 1. **子代理驱动（当前会话）** — 逐 Task 派发子代理
> 2. **并行会话** — 新会话中批量执行

> [!IMPORTANT]
> **v3 Tech Stack 变更：** `dataclasses + jsonschema` → `Pydantic V2 + pydantic-settings`。所有数据类改为 `BaseModel`，`get_input_schema()` 可用 `model_json_schema()` 自动生成。这是 Sonnet 审查的核心建议。确认？

> [!WARNING]
> **Phase 1 Task 4（迁移现有 tools）有破坏性：** 所有 5 个 tool 的 `execute` 签名从 `(**kwargs)` 变为 `(input: dict, context: ToolUseContext)`，且返回值支持 `Union[ToolResult, AsyncGenerator]`。这会暂时破坏现有测试，需要在同一个 commit 内完成迁移。确认理解？

> [!NOTE]
> **v3 新增 Sonnet 补丁清单（15 条）：**
> | # | 补丁 | Phase |
> |---|---|---|
> | 1 | Pydantic V2 迁移 | 全局 |
> | 2 | BaseTool domain + AsyncGenerator | P1 |
> | 3 | SystemMessage hep_env + AppState HEP 字段 | P1 |
> | 4 | Session hep_snapshot | P2 |
> | 5 | Config [hep] 块 + API Backoff + JSON 纠错 | P3 |
> | 6 | EventTranslator JSON 纠错集成 | P2 |
> | 7 | Streaming Tool Execution | P5.5 |
> | 8 | Permission HEP 硬规则 (bashlex) | P6 |
> | 9 | Context HEP 感知压缩 | P5 |
> | 10 | MCP HTCondor 验收条件 | P4 |
> | 11 | SemanticRouter | P2 |
> | 12 | Daemon/Client 架构 | P9 |
> | 13 | HEPDataTool | P1 |
> | 14 | Phase 7 Hooks 按原计划保留 | P7 |
> | 15 | 工程备忘（Logger/headless/pipx） | 分散 |

