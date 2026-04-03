# 实现命令队列 (Message Queue) 功能 — 完全对齐 Claude Code

> **对照源码**：
> - [messageQueueManager.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/utils/messageQueueManager.ts) — 队列核心 (548 行)
> - [handlePromptSubmit.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/utils/handlePromptSubmit.ts) — 提交入口 (611 行)
> - [queueProcessor.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/utils/queueProcessor.ts) — 出队处理器 (96 行)
> - [useQueueProcessor.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/hooks/useQueueProcessor.ts) — 响应式触发 (69 行)
> - [QueryGuard.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/utils/QueryGuard.ts) — 状态机 (122 行)
> - [immediateCommand.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/utils/immediateCommand.ts) — 即时命令标识 (16 行)
> - [useCancelRequest.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/hooks/useCancelRequest.ts) — ESC 分层取消 (277 行)
> - [PromptInputQueuedCommands.tsx](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/components/PromptInput/PromptInputQueuedCommands.tsx) — 队列预览 UI (117 行)

**目标**：完全对齐 Claude Code 的消息队列架构，在 AI 生成过程中允许用户继续输入 prompt。
用户按下 Enter 时不报错，而是将 prompt 入队，生成完毕后按优先级自动出队执行。

---

## 一、架构总览 (对齐 Claude Code)

### 1.1 数据结构：`QueuedCommand` typed struct

Claude Code **不是** `list[str]`，而是带有完整上下文的结构体队列。

```python
@dataclass
class QueuedCommand:
    """A queued user input with full context. Mirrors Claude Code's QueuedCommand type."""
    value: str                              # the user's input text
    mode: str = "prompt"                    # "prompt" | "slash"  (future: "bash")
    priority: str = "next"                  # "now" | "next" | "later"
    uuid: str = field(default_factory=lambda: str(uuid4()))
    skip_slash_commands: bool = False       # for bridge/remote messages
    is_meta: bool = False                   # system-generated, hidden from transcript
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
```

**对应源码**：[textInputTypes.ts:299-358](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/types/textInputTypes.ts#L299-L358)

### 1.2 三级优先级系统

| 优先级 | 语义 | 使用场景 | Cascade 需要? |
|--------|------|----------|---------------|
| `now` | 中断当前工具，立即执行 | 中止+重定向 | ✅ 需要（将来支持 interruptible tools） |
| `next` | 在当前轮结束后、下一轮前执行 | 用户输入（默认） | ✅ 必须 |
| `later` | 等待完整空闲后处理 | 系统通知、定时任务 | ✅ 需要（将来支持 scheduled tasks） |

出队时按 `PRIORITY_ORDER = {"now": 0, "next": 1, "later": 2}` 排序，同优先级内 FIFO。

**对应源码**：[messageQueueManager.ts:151-193](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/utils/messageQueueManager.ts#L151-L193)

### 1.3 三状态状态机 (QueryGuard)

Claude Code 不用简单的 `_generating: bool`，而是三状态状态机：

```
idle → dispatching → running → idle
             ↓
           idle   (cancelReservation, if nothing to process)
```

| 状态 | 含义 | Cascade 等价 |
|------|------|-------------|
| `idle` | 无活跃查询，可以出队 | `_generating = False` |
| `dispatching` | 已出队一条，异步链还没到真正执行 | **新增** |
| `running` | 正在执行 API 调用 | `_generating = True` |

**为什么需要 `dispatching`**：从 `_check_and_run_queue()` 调用到 `_execute_prompt()` 中设置 `_generating = True` 之间存在异步间隙。在这个间隙中，如果用户再次提交，`_generating` 仍然是 `False`，会导致**直接执行而非入队**，产生并发竞态。

**对应源码**：[QueryGuard.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/utils/QueryGuard.ts)

### 1.4 即时命令绕过队列

以下命令在生成过程中**不入队，直接执行**：

Claude Code 中标记为 `immediate: true` 的 11 个命令：
`/rename`, `/exit`, `/hooks`, `/brief`, `/status`, `/mcp`, `/plugin`, `/bridge`, `/color`, `/btw`, `/sandbox-toggle`

> **注意**：`/model` 的即时性在 Claude Code 中是通过 A/B 实验门控的 (`shouldInferenceConfigCommandBeImmediate()`)，并非无条件即时。

**Cascade 需要标记为即时的命令**：
- `/model` — 用户想立刻切换模型，不应等生成结束
- `/help` — 查看帮助不需要等待
- `/config` — 查看/修改配置
- `/clear` — 清屏操作
- `/status` — 查看状态

**对应源码**：[handlePromptSubmit.ts:227-310](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/utils/handlePromptSubmit.ts#L227-L310) + [immediateCommand.ts](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/utils/immediateCommand.ts)

### 1.5 出队策略：斜杠命令单独处理，普通 prompt 批量合并

Claude Code 的出队**不是**简单地一次弹一条：

```
if isSlashCommand(next) or next.mode == "bash":
    # Slash commands and bash: process individually (not batched)
    cmd = dequeue()
    execute([cmd])
else:
    # Non-slash, same-mode commands: batch drain all at once
    commands = dequeue_all_matching(same_mode_and_not_slash)
    execute(commands)  # → becomes multiple user messages in ONE API call
```

**为什么**：多条连续普通 prompt 可以合并成一次 API 调用（每条仍是独立的 user message），减少 API 往返次数。

**对应源码**：[queueProcessor.ts:52-87](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/utils/queueProcessor.ts#L52-L87)

### 1.6 ESC 分层取消行为

ESC 不是简单的"清空队列"，而是**分层优先级**：

| 优先级 | 条件 | 动作 |
|--------|------|------|
| 1 | 有活跃任务在运行 (`abortSignal` 未 abort) | 取消当前任务 (abort) |
| 2 | 队列非空，Claude 空闲 | `popCommandFromQueue()` — 弹出最后一条给用户编辑 |
| 3 | 都不满足 | fallback cancel |

**注意**：`clearCommandQueue()`（清空全部）只在 `chat:killAgents`（两次快捷键杀后台 agent）时调用，不是普通 ESC。

**对应源码**：[useCancelRequest.ts:95-121](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/hooks/useCancelRequest.ts#L95-L121)

### 1.7 ↑ 箭头编辑已排队消息 (popAllEditable)

用户按 ↑ 时，如果队列中有可编辑的命令，会把它们**全部弹出合并到输入框**中供用户编辑：

```python
def pop_all_editable(current_input: str, cursor_offset: int) -> Optional[PopResult]:
    """Pop all editable commands from queue, merge into input for editing."""
    editable = [cmd for cmd in queue if is_editable(cmd)]
    if not editable:
        return None
    queued_texts = [cmd.value for cmd in editable]
    new_input = "\n".join(queued_texts + [current_input])
    # Remove editable items from queue, keep non-editable (e.g. task-notification)
    queue[:] = [cmd for cmd in queue if not is_editable(cmd)]
    return PopResult(text=new_input, cursor_offset=...)
```

**对应源码**：[messageQueueManager.ts:428-484](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/utils/messageQueueManager.ts#L428-L484)

### 1.8 队列预览 UI (持久化显示)

Claude Code 在 prompt 输入框**下方持久展示**排队中的消息（不是临时 toast）：

- 使用 `PromptInputQueuedCommands` 组件
- 通过 `isQueuedCommandVisible()` 过滤出应显示的命令
- task-notification 最多显示 3 条，超出的合并为 "+N more tasks completed"
- 每条命令渲染为一个 dim 灰色的 user message 气泡

**对应源码**：[PromptInputQueuedCommands.tsx](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/components/PromptInput/PromptInputQueuedCommands.tsx)

### 1.9 可中断工具 (interruptBehavior)

如果当前所有正在执行的工具都标记为 `interruptBehavior: 'cancel'`（如 `SleepTool`），用户提交新输入时会**直接中止当前轮**（abort），然后入队：

```typescript
if (params.hasInterruptibleToolInProgress) {
    params.abortController?.abort('interrupt')
}
enqueue({ value: finalInput.trim(), mode, ... })
```

**对应源码**：[handlePromptSubmit.ts:319-332](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/utils/handlePromptSubmit.ts#L319-L332)

### 1.10 队列操作日志

每次 enqueue/dequeue/popAll 操作都记录到 sessionStorage，用于调试：

```python
def _log_queue_operation(self, operation: str, content: Optional[str] = None):
    record = {
        "type": "queue-operation",
        "operation": operation,  # "enqueue" | "dequeue" | "popAll" | "remove"
        "timestamp": datetime.now().isoformat(),
        "session_id": self._session_id,
    }
    if content:
        record["content"] = content
    # write to session log
```

**对应源码**：[messageQueueManager.ts:28-38](file:///Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha/src/utils/messageQueueManager.ts#L28-L38)

---

## 二、原子任务拆解

### [ ] 任务 1：定义 `QueuedCommand` 数据结构和队列管理器

**新增文件**：`src/cascade/ui/message_queue.py`

**细节**：
- 定义 `QueuedCommand` dataclass（见 1.1）
- 实现 `MessageQueueManager` 类，暴露以下方法：

```python
class MessageQueueManager:
    """Module-level message queue, mirrors Claude Code's messageQueueManager.ts"""

    PRIORITY_ORDER = {"now": 0, "next": 1, "later": 2}

    def __init__(self):
        self._queue: list[QueuedCommand] = []
        self._subscribers: list[Callable] = []

    # --- Write operations ---
    def enqueue(self, command: QueuedCommand) -> None: ...
    def dequeue(self, filter_fn: Optional[Callable] = None) -> Optional[QueuedCommand]: ...
    def dequeue_all_matching(self, predicate: Callable) -> list[QueuedCommand]: ...
    def peek(self, filter_fn: Optional[Callable] = None) -> Optional[QueuedCommand]: ...
    def clear(self) -> None: ...

    # --- Editable mode helpers ---
    def pop_all_editable(self, current_input: str, cursor_offset: int) -> Optional[PopAllEditableResult]: ...
    def is_editable(self, cmd: QueuedCommand) -> bool: ...

    # --- Read operations ---
    @property
    def length(self) -> int: ...
    @property
    def has_commands(self) -> bool: ...
    def get_snapshot(self) -> list[QueuedCommand]: ...

    # --- Subscription (for reactive UI updates) ---
    def subscribe(self, callback: Callable) -> Callable:  # returns unsubscribe fn
    def _notify_subscribers(self) -> None: ...

    # --- Logging ---
    def _log_operation(self, operation: str, content: Optional[str] = None) -> None: ...

    # --- Static helpers ---
    @staticmethod
    def is_slash_command(cmd: QueuedCommand) -> bool:
        return isinstance(cmd.value, str) and cmd.value.strip().startswith("/") and not cmd.skip_slash_commands
```

### [ ] 任务 2：实现三状态状态机 `QueryGuard`

**新增文件**：`src/cascade/ui/query_guard.py`

**细节**：

```python
class QueryGuard:
    """Three-state machine for query lifecycle. Mirrors Claude Code's QueryGuard.ts."""

    def __init__(self):
        self._status: Literal["idle", "dispatching", "running"] = "idle"
        self._generation: int = 0
        self._subscribers: list[Callable] = []

    def reserve(self) -> bool:
        """idle → dispatching. Returns False if not idle."""
        if self._status != "idle":
            return False
        self._status = "dispatching"
        self._notify()
        return True

    def cancel_reservation(self) -> None:
        """dispatching → idle. No-op if not dispatching."""
        if self._status != "dispatching":
            return
        self._status = "idle"
        self._notify()

    def try_start(self) -> Optional[int]:
        """idle|dispatching → running. Returns generation number, or None if already running."""
        if self._status == "running":
            return None
        self._status = "running"
        self._generation += 1
        self._notify()
        return self._generation

    def end(self, generation: int) -> bool:
        """running → idle. Returns True if generation matches (caller should cleanup)."""
        if self._generation != generation or self._status != "running":
            return False
        self._status = "idle"
        self._notify()
        return True

    def force_end(self) -> None:
        """Force → idle. Used by ESC cancel."""
        if self._status == "idle":
            return
        self._status = "idle"
        self._generation += 1
        self._notify()

    @property
    def is_active(self) -> bool:
        return self._status != "idle"
```

### [ ] 任务 3：实现队列处理器 `process_queue_if_ready`

**新增文件**：`src/cascade/ui/queue_processor.py`

**细节**：

```python
def process_queue_if_ready(
    queue: MessageQueueManager,
    execute_input: Callable[[list[QueuedCommand]], Awaitable[None]],
) -> bool:
    """Process next command(s) from queue. Mirrors Claude Code's queueProcessor.ts."""

    next_cmd = queue.peek()
    if next_cmd is None:
        return False

    # Slash commands: process individually (not batched)
    if queue.is_slash_command(next_cmd):
        cmd = queue.dequeue()
        if cmd:
            asyncio.create_task(execute_input([cmd]))
        return True

    # Non-slash: drain all same-mode commands at once
    target_mode = next_cmd.mode
    commands = queue.dequeue_all_matching(
        lambda cmd: not queue.is_slash_command(cmd) and cmd.mode == target_mode
    )
    if not commands:
        return False

    asyncio.create_task(execute_input(commands))
    return True
```

### [ ] 任务 4：修改提交拦截逻辑（带即时命令绕过）

**涉及文件**：`src/cascade/ui/textual_app.py`

**细节**：

```python
# In on_input_submitted:

# --- Step 1: Check for immediate commands (bypass queue entirely) ---
IMMEDIATE_COMMANDS = {"/model", "/help", "/config", "/clear", "/status"}
if user_text.strip().startswith("/"):
    cmd_name = user_text.strip().split()[0]
    if cmd_name in IMMEDIATE_COMMANDS and self._query_guard.is_active:
        # Execute immediately even during generation
        input_widget.text = ""
        await self._execute_immediate_command(user_text)
        return

# --- Step 2: If generating, enqueue ---
if self._query_guard.is_active:
    cmd = QueuedCommand(
        value=user_text,
        mode="slash" if user_text.strip().startswith("/") else "prompt",
        priority="next",
    )
    self._message_queue.enqueue(cmd)
    input_widget.add_to_history(user_text)
    input_widget.text = ""
    self._update_queue_preview()  # persistent UI, not toast
    self._log_queue_operation("enqueue", user_text)
    return

# --- Step 3: Normal execution (idle state) ---
self._query_guard.reserve()
try:
    await self._execute_prompt(user_text)
finally:
    self._query_guard.cancel_reservation()  # no-op if try_start() already ran
```

### [ ] 任务 5：实现出队触发（try/finally 强制模式）

**涉及文件**：`src/cascade/ui/textual_app.py`

**细节**：

```python
async def _run_generation(self, user_text: str) -> None:
    """Core generation logic. QueryGuard transitions handled here."""
    generation = self._query_guard.try_start()
    if generation is None:
        return  # Another query already running

    try:
        # ... actual API call / streaming logic ...
        pass
    finally:
        if self._query_guard.end(generation):
            # This generation is still current, safe to cleanup + check queue
            self._show_prompt()
            process_queue_if_ready(
                self._message_queue,
                self._execute_queued_input,
            )
```

### [ ] 任务 6：重构 `on_input_submitted` 剥离执行体

**涉及文件**：`src/cascade/ui/textual_app.py`

**细节**：
- 抽取 `async def _execute_prompt(self, user_text: str)` — 处理单条直接提交
- 抽取 `async def _execute_queued_input(self, commands: list[QueuedCommand])` — 处理出队的批量命令
- 两者共享底层的命令路由逻辑（`/` 前缀检查 → slash 路由，否则 → API 调用）

### [ ] 任务 7：实现 ESC 分层取消

**涉及文件**：`src/cascade/ui/textual_app.py`

**细节**：

```python
def action_cancel(self) -> None:
    """ESC handler with layered priority. Mirrors Claude Code's useCancelRequest."""

    # Priority 1: Cancel active generation
    if self._query_guard.is_active and self._abort_controller and not self._abort_controller.aborted:
        self._abort_controller.abort()
        return

    # Priority 2: Pop queue into input for editing (idle + queue non-empty)
    if self._message_queue.has_commands:
        result = self._message_queue.pop_all_editable(
            self._input_widget.text,
            self._input_widget.cursor_offset,
        )
        if result:
            self._input_widget.text = result.text
            self._input_widget.cursor_offset = result.cursor_offset
            self._update_queue_preview()
            return

    # Priority 3: Fallback (nothing to cancel)
    pass
```

### [ ] 任务 8：实现队列预览 UI（持久化显示）

**涉及文件**：`src/cascade/ui/textual_app.py` (或新增 `src/cascade/ui/widgets/queue_preview.py`)

**细节**：
- 在 prompt 输入框上方添加一个持久化的 `QueuePreview` widget
- 实时订阅 `MessageQueueManager` 的变化
- 每条排队命令显示为 dim 灰色文本行
- 当队列为空时隐藏
- 限制最多展示 5 条可见命令，超出显示 "+N more queued"

```python
class QueuePreview(Static):
    """Persistent preview of queued commands above the input."""

    def on_mount(self) -> None:
        self._unsubscribe = self.app._message_queue.subscribe(self._refresh)

    def _refresh(self) -> None:
        commands = self.app._message_queue.get_snapshot()
        visible = [cmd for cmd in commands if self._is_visible(cmd)]
        if not visible:
            self.display = False
            return
        self.display = True
        lines = []
        for cmd in visible[:5]:
            lines.append(f"[dim]⏳ {cmd.value[:80]}...[/dim]" if len(cmd.value) > 80 else f"[dim]⏳ {cmd.value}[/dim]")
        if len(visible) > 5:
            lines.append(f"[dim]  +{len(visible) - 5} more queued[/dim]")
        self.update("\n".join(lines))
```

### [ ] 任务 9：实现队列操作日志

**涉及文件**：`src/cascade/ui/message_queue.py`

**细节**：
- 每次 enqueue/dequeue/popAll/clear 操作写入 session log
- 格式与 Claude Code 一致：`{type: "queue-operation", operation, timestamp, session_id, content?}`

### [ ] 任务 10：↑ 箭头集成 — 队列编辑

**涉及文件**：`src/cascade/ui/widgets/prompt_input.py`

**细节**：
- 修改 ↑ 箭头处理逻辑：
  - 如果队列中有可编辑命令，先调用 `pop_all_editable()` 把它们合并到输入框
  - 如果队列为空，走原来的历史记录导航

### [ ] 任务 11：运行和验证效果

**测试场景**：

1. **基础入队/出队**：
   - 发送一个长 prompt → 生成过程中输入第二条 → 预期：入队 + 预览显示 + 生成完自动执行

2. **即时命令绕过**：
   - 生成过程中输入 `/model` → 预期：立即弹出模型选择器，不入队

3. **多条排队 + 批量合并**：
   - 生成过程中连续输入 3 条普通 prompt → 预期：3 条入队，生成完后批量出队合并成一次 API 调用

4. **斜杠命令单独处理**：
   - 生成过程中依次输入 "hello"、"/help"、"world" → 预期：出队顺序正确，`/help` 单独执行

5. **ESC 分层**：
   - 生成中按 ESC → 预期：取消当前生成
   - 队列非空 + 空闲时按 ESC → 预期：队列命令弹回输入框供编辑

6. **竞态安全**：
   - 快速连续提交两条 → 预期：不会并发执行两次 API 调用（dispatching 状态防护）

---

## 三、文件清单

| 文件 | 操作 | 对应 Claude Code |
|------|------|------------------|
| `src/cascade/ui/message_queue.py` | **新增** | `messageQueueManager.ts` |
| `src/cascade/ui/query_guard.py` | **新增** | `QueryGuard.ts` |
| `src/cascade/ui/queue_processor.py` | **新增** | `queueProcessor.ts` |
| `src/cascade/ui/textual_app.py` | **修改** | `handlePromptSubmit.ts` + `useQueueProcessor.ts` + `useCancelRequest.ts` |
| `src/cascade/ui/widgets/queue_preview.py` | **新增** | `PromptInputQueuedCommands.tsx` |
| `src/cascade/ui/widgets/prompt_input.py` | **修改** | `PromptInput.tsx` (popAllEditable 集成) |
