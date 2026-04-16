# Fix Permission Prompt y/N Freeze — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the y/N permission prompt freezing — user cannot type input and Ctrl+C cannot force quit during permission requests.

**Architecture:** The fix targets a race condition between `asyncio.ensure_future()` callbacks (tool_start/tool_end) and the synchronous `ask_user` flow. The callbacks schedule spinner/prompt state changes that can override the `ask_user`'s UI state. The fix is to make tool callbacks respect the permission state, and ensure the prompt is always visible and editable during `ask_user`.

**Tech Stack:** Python 3.14, Textual 3.x, asyncio

---

## Root Cause Analysis

### The Race Condition

```
Timeline:
  1. _run_generation() starts → _hide_prompt(), _generating=True
  2. engine.submit() calls LLM → LLM returns tool_calls
  3. permissions.check() called → ask_user injected
  4. ask_user() → _remove_spinner(), show permission message, _show_prompt()
  
  -- User can now see the prompt and type y/N --
  
  BUT MEANWHILE:
  5. on_tool_start callback was scheduled via asyncio.ensure_future()
     → _do() runs: _remove_spinner() + _show_spinner("Executing")
     → This can fire AFTER ask_user showed the prompt, or OVERLAP
  
  RESULT: Spinner overlays the prompt, or _handle_tool_start's
  _show_spinner("Executing") runs in a loop since tool_start fires
  for every tool call the model makes
```

### Specific Bug Vectors

1. **`_handle_tool_start` uses `asyncio.ensure_future()`** (line 382)
   - This schedules a coroutine that runs asynchronously
   - It calls `_show_spinner("Executing")` which may run AFTER `ask_user` has shown the prompt
   - **Fix:** Check `_permission_future` before showing spinner

2. **`_handle_tool_end` also uses `asyncio.ensure_future()`** (line 398) 
   - Same race: after tool ends, it calls `_show_spinner("Generating")` 
   - **Fix:** Same guard

3. **`_generating` flag stays True during permission prompt**
   - `_generating = True` at line 294, never set to False during `ask_user`
   - The `_generating` guard at line 244 is BELOW the `_permission_future` check, so it shouldn't block y/N input
   - BUT: any bug that prevents the `_permission_future` from being set (e.g., race) would cause the `_generating` guard to block ALL input

4. **Query engine's `on_tool_start` fires BEFORE `ask_user`** (line 115 in query.py)
   - Actually in the current code (query.py:111-139), `permissions.check(... ask_user=ask_user)` is called FIRST (line 115), and `on_tool_start` fires AFTER (line 138-139)
   - This causes the `ask_user` UI to appear *before* the tool intent is printed to the screen, confusing the user.

5. **Textual Event Loop Deadlock (The Actual Root Cause of The Freeze)**
   - The user inputs text, triggering `on_input_submitted`.
   - `on_input_submitted` calls `await self.engine.submit(...)`.
   - Because `on_input_submitted` (a message handler) is `await`ing the engine, the entire `CascadeApp`'s event pump blocks.
   - When the engine calls `ask_user`, it awaits a Future, freezing the UI frame.
   - The user's subsequent input to approve the permission is never processed because the app cannot handle new messages while `on_input_submitted` is suspended on the stack!

---

## Proposed Changes

### Task 1: Guard tool callbacks against permission state

**Files:**
- Modify: `src/cascade/ui/textual_app.py:373-398`

**Current code (line 373-391):**
```python
def _handle_tool_start(self, name: str, args: dict) -> None:
    """Sync callback for tool start — schedules async UI update."""
    async def _do():
        await self._remove_spinner()
        args_preview = str(args)
        if len(args_preview) > 200:
            args_preview = args_preview[:200] + "..."
        await self.append_tool_message(f"⚙ {name}", args_preview, css_class="tool-msg")
        await self._show_spinner("Executing")
    asyncio.ensure_future(_do())
```

**Fixed code:**
```python
def _handle_tool_start(self, name: str, args: dict) -> None:
    """Sync callback for tool start — schedules async UI update."""
    async def _do():
        # Don't touch UI if waiting for permission input
        if self._permission_future and not self._permission_future.done():
            return
        await self._remove_spinner()
        args_preview = str(args)
        if len(args_preview) > 200:
            args_preview = args_preview[:200] + "..."
        await self.append_tool_message(f"⚙ {name}", args_preview, css_class="tool-msg")
        await self._show_spinner("Executing")
    asyncio.ensure_future(_do())
```

**Same fix for `_handle_tool_end` (line 393-398):**
```python
def _handle_tool_end(self, name: str, tool_result) -> None:
    """Sync callback for tool end — schedules async UI update."""
    async def _do():
        # Don't touch UI if waiting for permission input
        if self._permission_future and not self._permission_future.done():
            return
        await self._remove_spinner()
        output = tool_result.output if hasattr(tool_result, 'output') else str(tool_result)
        is_error = tool_result.is_error if hasattr(tool_result, 'is_error') else False
        display = output[:500] + "\n..." if len(output) > 500 else output
        label = f"✗ Error: {name}" if is_error else f"✓ Result: {name}"
        css_class = "tool-msg-error" if is_error else "tool-msg"
        await self.append_tool_message(label, display, css_class=css_class)
        if not is_error:
            await self._show_spinner("Generating")
    asyncio.ensure_future(_do())
```

### Task 2: Ensure `ask_user` properly clears `_generating` temporarily

**Files:**
- Modify: `src/cascade/ui/textual_app.py:316-337`

**Current code:**
```python
async def ask_user(prompt_msg: str) -> bool:
    """Show permission prompt and wait for user y/n input."""
    await self._remove_spinner()
    
    loop = asyncio.get_event_loop()
    self._permission_future = loop.create_future()
    await self.append_rich_message(...)
    self._show_prompt()
    try:
        result = await self._permission_future
    finally:
        self._permission_future = None
        self._hide_prompt()
        await self._show_spinner("Generating")
    return result
```

**Fixed code:**
```python
async def ask_user(prompt_msg: str) -> bool:
    """Show permission prompt and wait for user y/n input."""
    await self._remove_spinner()
    
    loop = asyncio.get_event_loop()
    self._permission_future = loop.create_future()
    
    # Temporarily clear _generating so the prompt is fully interactive
    self._generating = False
    
    await self.append_rich_message(
        f"[bold yellow]⚠️ Permission Request[/bold yellow]\n"
        f"[dim]{prompt_msg}[/dim]\n"
        f"[bold]Enter [green]y[/green] to approve, anything else to deny:[/bold]"
    )
    self._show_prompt()
    try:
        result = await self._permission_future
    finally:
        self._permission_future = None
        self._generating = True  # Restore for remaining generation
        self._hide_prompt()
        await self._show_spinner("Generating")
    return result
```

**Key change:** `self._generating = False` before showing the prompt, then `self._generating = True` after. This ensures the `_generating` guard (line 244) doesn't accidentally block input if there's any event ordering issue.

### Task 3: Verify Ctrl+C still works during permission prompt

**Files:**
- Verify: `src/cascade/ui/textual_app.py:45`

The binding `Binding("ctrl+c", "quit", "退出", show=False, priority=True)` should already work because `priority=True` makes it fire before ANY widget key handling. But we should verify `action_quit` cleans up properly:

**Check current `action_quit`:**
If there's no override, Textual's default `action_quit` calls `self.exit()` which should force-close. This should work even during `await self._permission_future`. But if the future is never resolved, the `await` in `ask_user` will be cancelled by the app exit.

**No code change needed** — just verify during manual testing.

### Task 4: Move `_run_generation` into a Background Worker

**Files:**
- Modify: `src/cascade/ui/textual_app.py:280-285`

**Current code:**
```python
        # ── AI generation ──
        await self._run_generation(user_text)
```

**Fixed code:**
```python
        # ── AI generation ──
        # Run generation in a background worker to avoid blocking the message pump.
        # This prevents deadlocks when generating waits for user permission input.
        from textual.worker import Worker
        self.run_worker(self._run_generation(user_text), exclusive=True)
```
**Explanation:** This is the ultimate fix for the UI freeze. Textual will run the generation loop freely and `on_input_submitted` will complete instantly, allowing the app to process `y/n` messages.

### Task 5: Print Tool Command Before Requesting Permission

**Files:**
- Modify: `src/cascade/engine/query.py:110-140`

**Current flow:**
1. `permissions.check` (prints ⚠️ Permission Request)
2. `on_tool_start` (prints tool parameters JSON)

**Fixed flow:**
1. Move `on_tool_start` so it fires *before* `permissions.check()`.
2. This ensures the user sees `[red] bash \n {'command': ...}` *prior* to `Allow bash? [y/N]` so they can make an informed decision.

---

## Verification Plan

### Manual Tests (user runs the app)
1. Send a prompt that triggers a tool (e.g., "list files in the current directory")
2. Permission prompt appears → type "y" → Enter → tool executes ✓
3. Permission prompt appears → type "N" → Enter → denied, returns to normal prompt ✓
4. Permission prompt appears → press Ctrl+C → app exits cleanly ✓
5. After approving a tool → spinner shows "Generating" → next tool prompt appears correctly ✓
6. Multiple tool calls in sequence → each permission prompt is interactive ✓
