# Chinese Text → English — Code Review Fix Plan

**Goal:** Replace all Chinese string literals in source code with English equivalents, per Rule 2 (English-only code comments/strings).

**Scope:** 3 files, 14 occurrences. No comments found — all are string literals (UI text, regex patterns).

---

## Classification

### Category A: UI Notification Strings (10 occurrences)
User-facing toast messages. Replace Chinese with concise English.

### Category B: Textual Binding Descriptions (4 occurrences)
Internal binding labels. These are `show=False` so never displayed, but still violate the rule.

### Category C: Regex Patterns (2 occurrences)
Chinese keywords in path-extraction regex (`到|保存|下载`). These are **functional** — they match Chinese user input.

> ⚠️ **Decision needed:** Category C regex patterns exist to parse Chinese user prompts like "保存到 ~/Desktop". Removing them would break Chinese input support for image generation. **Recommend keeping them** as they are input-matching logic, not comments/labels.

---

## Task 1: `src/cascade/ui/textual_app.py` — Binding descriptions

**Lines 45-48:**

| Line | Current (Chinese) | Replacement (English) |
|------|-------------------|----------------------|
| 45 | `"输入框"` | `"Focus input"` |
| 46 | `"退出"` | `"Quit"` |
| 47 | `"复制上条"` | `"Copy last reply"` |
| 48 | `"清屏"` | `"Clear chat"` |

```python
# Current:
    BINDINGS = [
        Binding("escape", "focus_input", "输入框", show=False),
        Binding("ctrl+c", "quit", "退出", show=False, priority=True),
        Binding("ctrl+y", "copy_last_reply", "复制上条", show=False),
        Binding("ctrl+l", "clear_chat", "清屏", show=False),
    ]

# New:
    BINDINGS = [
        Binding("escape", "focus_input", "Focus input", show=False),
        Binding("ctrl+c", "quit", "Quit", show=False, priority=True),
        Binding("ctrl+y", "copy_last_reply", "Copy last reply", show=False),
        Binding("ctrl+l", "clear_chat", "Clear chat", show=False),
    ]
```

---

## Task 2: `src/cascade/ui/textual_app.py` — Notify messages

**Line 266:**
```python
# Current:
self.notify("⏳ 正在生成中，请稍候...")
# New:
self.notify("⏳ Generating, please wait...")
```

**Line 541:**
```python
# Current:
self.notify("ℹ 没有可复制的内容")
# New:
self.notify("ℹ Nothing to copy")
```

**Line 547:**
```python
# Current:
self.notify(f"✅ 已复制 {len(self._last_reply)} 字符")
# New:
self.notify(f"✅ Copied {len(self._last_reply)} chars")
```

**Line 550:**
```python
# Current:
self.notify("✅ 已复制 (OSC52)")
# New:
self.notify("✅ Copied (OSC52)")
```

---

## Task 3: `src/cascade/ui/widgets.py` — Notify messages

**Line 40:**
```python
# Current:
self.app.notify("📋 已复制文本块", timeout=2.0)
# New:
self.app.notify("📋 Text block copied", timeout=2.0)
```

**Line 43:**
```python
# Current:
self.app.notify(f"❌ 复制失败: {e}", severity="error")
# New:
self.app.notify(f"❌ Copy failed: {e}", severity="error")
```

**Line 100:**
```python
# Current:
self.notify(f"✅ 已复制 {len(text)} 字符")
# New:
self.notify(f"✅ Copied {len(text)} chars")
```

**Line 104:**
```python
# Current:
self.notify(f"✅ 已复制 {len(text)} 字符 (OSC52)")
# New:
self.notify(f"✅ Copied {len(text)} chars (OSC52)")
```

---

## Task 4 (SKIP): `src/cascade/services/api_client.py` — Regex patterns

**Lines 44, 141:** Chinese keywords in regex (`到|保存|下载`).

**Recommendation: Keep as-is.** These match Chinese user input for image save commands. Removing them would break functionality. They are functional matching logic, not labels or comments.

---

## Summary

| Task | File | Changes | Type |
|------|------|---------|------|
| 1 | `textual_app.py` | 4 binding descriptions | Label |
| 2 | `textual_app.py` | 4 notify messages | UI string |
| 3 | `widgets.py` | 4 notify messages | UI string |
| 4 | `api_client.py` | 0 (skip — functional regex) | N/A |

**Total: 12 string replacements across 2 files.**

---

## Verification

```bash
# After edits, verify zero Chinese characters remain (except api_client.py regex):
grep -rn '[一-龥]' src/cascade/ui/
# Expected: 0 results

grep -rn '[一-龥]' src/cascade/services/api_client.py
# Expected: 2 results (lines 44, 141 — intentional regex)
```
