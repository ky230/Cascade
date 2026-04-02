# Fix Enter Key Submission — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Enter key reliably submit prompts in all states (normal chat, permission y/N, empty input).

**Architecture:** The fix is confined to two files. The root cause is a Textual event propagation conflict between `PromptInput._on_key` (widget level) and `CascadeApp.on_key` (app level). We simplify by making `PromptInput` the **single authority** for Enter handling — it always stops the event and fires `Submitted`. The App level `on_key` should **never** handle Enter for submission.

**Tech Stack:** Python 3.14, Textual 3.x

---

## Root Cause Analysis

### How Textual Key Events Flow

```
Terminal → focused widget._on_key() → [if not stopped] → bubbles to parents → App.on_key()
```

Key facts from Textual source:
- `TextArea._on_key` hard-codes `{"enter": "\n"}` — if we don't intercept first, Enter inserts a newline
- App's `on_key` (public handler) runs **only if** the event was NOT stopped by the widget
- App's `_on_key` (private) checks bindings first, then calls `dispatch_key`

### The Bug

In `PromptInput._on_key` (widgets.py:172-201), **when the palette IS visible**:

```python
if palette.is_visible and event.key in ("enter", ...):
    return  # ← BUG: returns without calling event.stop() or super()
```

This `return` does **neither** `event.stop()` nor `super()._on_key()`. So:
1. Textual's base `TextArea._on_key` never runs (because we returned from the override)
2. But `event.stop()` was never called, so the event **bubbles to App.on_key**
3. At App level (textual_app.py:97), the palette check calls `event.stop()` — **but by this point the event may already be partially processed**

The real problem: **there are TWO places handling palette-Enter** (widgets.py:178 + textual_app.py:121-128), creating a race condition. When the palette is NOT visible, Enter works correctly because `PromptInput._on_key` handles it cleanly (line 184-190).

But the user reports Enter failing even in **normal mode** (no palette). The likely cause: `palette.is_visible` may return `True` when the palette widget exists but has `display: none` set. Let me verify:

- `CommandPalette` default CSS has `display: none` (command_palette.py:33)
- The `is_visible` check uses Textual's built-in property
- Textual's `.is_visible` returns `False` when `display: none` is set — **this should be correct**

**However**, there's another scenario: after a slash command completes, the palette may not be properly hidden (`palette.display = False`), leaving it "visible" for the next Enter keypress.

### Most Likely Bug Vector

After further analysis, the most likely issue is simpler than expected:

**The `PromptInput.Submitted` message NOT BUBBLING.** In Textual, `Message` has `bubble = True` by default. But the `@on(PromptInput.Submitted)` decorator on `CascadeApp.on_input_submitted` requires the message to **arrive at the App**. Since `PromptInput` is nested inside `Horizontal > Vertical > VerticalScroll`, the message must bubble through all parents.

Let's verify: `Message` default `bubble = True` ✓. And `Submitted.__init__` calls `super().__init__()` ✓. So the message **should** bubble. This rules out a message routing issue.

**The real smoking gun:** Check `_generating` flag. If `_generating` is `True` when the user presses Enter (line 253-255), the submission is silently blocked with a notification. If the `_generating` flag got stuck `True` (e.g., from a previous error or timeout), **ALL subsequent Enter presses would be rejected**.

---

## Proposed Changes

### Task 1: Add diagnostic logging to `PromptInput._on_key`

**Files:**
- Modify: `src/cascade/ui/widgets.py:172-201`

**Step 1: Add logging to understand which branch is taken**

```python
async def _on_key(self, event) -> None:
    """Intercept Enter and Ctrl+N before TextArea's default handler."""
    # If the command palette is visible, let navigation keys bubble to App.on_key
    palette_visible = False
    try:
        from cascade.ui.command_palette import CommandPalette
        palette = self.app.query_one("#cmd-palette", CommandPalette)
        palette_visible = palette.is_visible
        if palette_visible and event.key in ("enter", "up", "down", "tab", "escape"):
            # Do NOT consume — let App.on_key handle palette interaction
            self.app.log(f"[PromptInput] key={event.key} → delegating to palette")
            return
    except Exception:
        pass

    if event.key == "enter":
        # Enter = submit the prompt (NOT a newline)
        event.stop()
        event.prevent_default()
        self.app.log(f"[PromptInput] Enter → submit, text='{self.text[:50]}', palette_visible={palette_visible}")
        if self.text.strip():
            self.post_message(self.Submitted(self, self.text))
        return

    if event.key == "ctrl+n":
        # Ctrl+N = insert a real newline character
        event.stop()
        event.prevent_default()
        start, end = self.selection
        self._replace_via_keyboard("\n", start, end)
        return

    # Everything else: delegate to parent TextArea._on_key
    await super()._on_key(event)
```

**Step 2: Add logging to `on_input_submitted`**

In `src/cascade/ui/textual_app.py:235-255`, add log statements:

```python
@on(PromptInput.Submitted)
async def on_input_submitted(self, event: PromptInput.Submitted) -> None:
    """Handle Enter in the input box."""
    user_text = event.value.strip()
    self.log(f"[App] on_input_submitted: text='{user_text[:50]}', _generating={self._generating}, _permission_future={self._permission_future}")
    if not user_text:
        return
    # ... rest unchanged ...
```

**Step 3: Run the app and test Enter key**

Run: `cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade && .venv/bin/python -m cascade`
Expected: Type "hello" + Enter → see log output in Textual console (Ctrl+D to open devtools, or check `textual.log`)

### Task 2: Fix the core issue based on diagnostics

**Files:**
- Modify: `src/cascade/ui/widgets.py:172-201`

Once we identify from logs WHICH branch is firing incorrectly, apply the targeted fix. The most likely fix is:

**Option A (if `_generating` flag stuck):** Add a safety reset in the error handler:

```python
# In textual_app.py _run_generation, the except block (line 356-361)
except Exception as e:
    await self._remove_spinner()
    await self.append_system_message(f"Error: {e}")
    self._generating = False  # ← already there, but verify it runs
    self._show_prompt()
    return
```

**Option B (if palette.is_visible returning True when palette has display:none):** Replace `is_visible` with explicit `display` check:

```python
# In widgets.py, replace:
if palette.is_visible and event.key in (...)
# with:
if palette.display and event.key in (...)
```

**Option C (simplify — eliminate dual handler):** Remove palette-Enter handling from `App.on_key` entirely. Make `PromptInput._on_key` handle everything:

```python
async def _on_key(self, event) -> None:
    palette_visible = False
    try:
        from cascade.ui.command_palette import CommandPalette
        palette = self.app.query_one("#cmd-palette", CommandPalette)
        palette_visible = palette.display  # use .display not .is_visible
    except Exception:
        pass

    # Palette visible: delegate UP/DOWN/TAB/ESCAPE to App, but handle Enter HERE
    if palette_visible and event.key in ("up", "down", "tab", "escape"):
        return  # bubble to App.on_key

    if event.key == "enter":
        event.stop()
        event.prevent_default()
        if palette_visible:
            # Select from palette and submit the command
            try:
                palette = self.app.query_one("#cmd-palette", CommandPalette)
                if palette._matches:
                    trigger = palette._matches[palette._highlight]["trigger"]
                    palette.display = False
                    self.text = trigger
                    self.post_message(self.Submitted(self, trigger))
                    return
            except Exception:
                pass
        # Normal submit
        if self.text.strip():
            self.post_message(self.Submitted(self, self.text))
        return

    if event.key == "ctrl+n":
        event.stop()
        event.prevent_default()
        start, end = self.selection
        self._replace_via_keyboard("\n", start, end)
        return

    await super()._on_key(event)
```

And in `App.on_key`, remove the Enter case entirely (keep up/down/tab/escape for palette).

---

## Execution Order

1. **Task 1** — Add diagnostic logging (non-destructive, just `self.app.log()`)
2. **Manual test** — Run the app, reproduce the bug, check logs
3. **Task 2** — Apply the fix based on findings (most likely Option C)
4. **Manual test** — Verify Enter works in: normal chat, permission y/N, after slash commands, with empty input
5. **User review** — Present diff for approval before commit

## Verification Plan

### Manual Tests (user runs the app)
1. Type "hello" → press Enter → message should submit ✓
2. Type "/help" → palette shows → press Enter → /help executes ✓
3. Type "/" → palette shows → press Escape → type "hello" → Enter → submits ✓
4. During generation, permission prompt appears → type "y" → Enter → approved ✓
5. Press Ctrl+N → newline inserted (no submit) ✓
6. Press Enter with empty input → nothing happens ✓
