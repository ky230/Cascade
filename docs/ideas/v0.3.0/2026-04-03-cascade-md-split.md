# Cascade.md Rules Split & Optimization

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Split the monolithic `Cascade.md` (110 lines, always_on) into 3 files to reduce context tax, eliminate execution errors, and apply 12 field-tested improvements.

**Architecture:** `Cascade.md` retains only universal safety rules (~30 lines, always_on). `Cascade-workflow.md` contains the 3-Agent protocol, handoff templates, and iteration rules (~70 lines, on-demand). `Cascade-references.md` contains Big Three paths (~15 lines, on-demand). All 12 accepted proposals from the Role 2/3 field reports are integrated into the appropriate file.

**⚠️ Staging Strategy:** All 3 files are written to a **staging directory** (`/Users/ky230/Desktop/Private/Workspace/ssH-remote-Workspace/2026-04-03/`) instead of directly to `.agents/rules/`. This prevents the Executor from overwriting `Cascade.md` while it's still loaded via `always_on`. The user will manually move the files into place after review.

**Tech Stack:** Markdown / Antigravity rules system

---

## Summary of All Integrated Proposals

| # | Proposal | Decision | Target File |
|---|----------|----------|-------------|
| 1A | Hardcoded handoff templates | ✅ Accept | `Cascade-workflow.md` |
| 2A | Append-only code_review_report | ✅ Accept | `Cascade-workflow.md` |
| 3A | Conditional + scoped Big Three reference | ✅ Modified | `Cascade-references.md` |
| 4A | File split | ✅ Accept | All 3 files |
| 5A | Smart initialization (no Role 0 block) | ✅ Accept | `Cascade-workflow.md` |
| 6A | ASCII loop → compact table | ✅ Accept | `Cascade-workflow.md` |
| E2A | commit/push explicit split | ✅ Accept | `Cascade-workflow.md` |
| E3A | Anchor patterns in plans | ✅ Modified | `Cascade-workflow.md` |
| E4A | Plans must not include commit steps | ✅ Accept | `Cascade-workflow.md` |
| E5A | Handoff includes file list (no inline diff) | ✅ Modified | `Cascade-workflow.md` |
| E6A | Pre-handoff verification gate | ✅ Accept | `Cascade-workflow.md` |

---

## Task 1: Create new `Cascade.md` (base safety rules only)

**Files:**
- Create: `/Users/ky230/Desktop/Private/Workspace/ssH-remote-Workspace/2026-04-03/Cascade.md`

**Step 1: Replace entire file with base safety rules**

```markdown
---
trigger: always_on
---

# Cascade — Base Safety Rules

> Universal constraints for ALL AI-assisted development sessions in the Cascade project.
> These rules apply regardless of whether the 3-Agent Workflow is active.

---

## 1.1 File Path & Naming Constraints
* **Antigravity Native Files:** `task.md`, `walkthrough.md`, and `code_review_report.md` are reserved Antigravity brain files. Agents must write them to their conversation-specific folder:
  `/Users/ky230/.gemini/antigravity/brain/<conversation-id>/`
* **Plan Files:** Must be named `YYYY-MM-DD-short-desc.md` (e.g., `2026-04-03-input-queue.md`).
  Default location: `/Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/plans/`

## 1.2 File Deletion — Strictly Prohibited
The agent is **never** permitted to execute deletion commands (`rm`, `rm -rf`, `git rm`, etc.). If logically required, output the exact command for the user to review and run manually.

## 1.3 Code Comments — English Only
All source code comments must be in **English**. Chinese comments are strictly forbidden.

## 1.4 Version Control — No Auto-Commit/Push
The agent must **never** auto-commit or auto-push under any circumstances.
* `git commit` and `git push` are **independent operations**. Never chain them.
* `commit`: executes ONLY when user explicitly says "commit"
* `push`: executes ONLY when user explicitly says "push"
* Never assume push follows commit.

## 1.5 3-Agent Workflow Activation
If the user's message explicitly involves the 3-Agent Workflow (e.g., mentions a plan file, assigns a role like "你是 Role 2", requests code review), load the workflow rules:
`.agents/rules/Cascade-workflow.md`

Otherwise, proceed normally without asking "which role am I?"
```

---

## Task 2: Create new `Cascade-workflow.md` (3-Agent protocol)

**Files:**
- Create: `/Users/ky230/Desktop/Private/Workspace/ssH-remote-Workspace/2026-04-03/Cascade-workflow.md`

**Step 1: Write the workflow rules file**

```markdown
---
trigger: manual
---

# Cascade — 3-Agent Workflow Protocol

> Loaded on-demand when the user activates the 3-Agent Workflow.
> Supplements the base safety rules in `Cascade.md`.

---

## Role Initialization
If the user has not specified which role (1-Decision Maker, 2-Executor, 3-Reviewer) the agent is assigned to, ask before proceeding.

---

## Part 1: Workflow-Specific Rules

### W1. Iteration File Protocol (Append-Only)
During multi-round iteration between Role 2 and Role 3, Antigravity brain files must be updated dynamically. **Overwriting or erasing historical records is strictly prohibited:**

* **`walkthrough.md` (Role 2):** Append new fix steps under `### Round N Fixes`. Never delete previous rounds.
* **`task.md` (Role 2):** Add new fix sub-tasks from Reviewer's report. Mark completed items `[x]`.
* **`code_review_report.md` (Role 3, Append-Only):** The Reviewer **MUST NOT modify previous `## Round N` sections**. Instead, append a new `## Round N+1 Review` section. Reference old issue IDs and state whether they are ✅ Resolved or still open. Original 🔴/🟡 markers in earlier rounds remain untouched as historical record.

### W2. Handoff Prompt Format
All handoff prompts MUST be enclosed in a **plain Markdown fenced code block** (triple backticks with NO language tag).
* This triggers Antigravity's copy-to-clipboard button.
* Do NOT use language-tagged code blocks (e.g., ` ```markdown `).
* All file paths in handoff prompts must be **full absolute paths** with actual Conversation UUIDs.

### W3. Plan Authoring Rules (for Role 1)
* Plans MUST NOT include `git commit` or `git push` steps. Commit/push is triggered exclusively by the user after the Reviewer confirms ✅.
* Use **function names + code snippets as primary locators**, not line numbers. Line numbers may appear as hints: `file.py → function_name() (hint: ~L396)`

### W4. Pre-Handoff Verification Gate (for Role 2)
Before generating a Reviewer handoff prompt, the Executor MUST:
1. Run lint/compile on all modified files (e.g. `python3 -c "import py_compile; py_compile.compile('file.py')"`)
2. Include the verification output in `walkthrough.md`
3. If verification fails, fix before handing off.

---

## Part 2: Role Definitions

### Role 1: Decision Maker (决策者)
* Writes the plan file (`YYYY-MM-DD-short-desc.md`) in `docs/plans/`.
* Keep plans structural — focus on actions, not micro-details.
* Handoff: output a prompt (per W2) for the Executor with the plan's absolute path.

### Role 2: Executor (执行者)
* Modifies the codebase based on Role 1's plan.
* Writes `task.md` and `walkthrough.md` in its UUID brain folder.
* Handoff: output a prompt (per W2) to the Reviewer using the **Role 2 → Role 3 Template** below.
* Receives feedback from Role 3. Only commits/pushes when user explicitly commands it.

### Role 3: Reviewer (审查者)
* Audits execution against the plan, brain files, and repo code.
* Writes `code_review_report.md` in its UUID brain folder. Issue classifications:
  * 🔴 **Critical** — Must fix immediately
  * 🟡 **Medium** — Discuss/fix
  * 🔵 **Deferred** — User agreed to defer
  * ✅ **Correct** — Verified
* If 🔴/🟡 found: handoff back to Role 2 using **Role 3 → Role 2 Template** below.
* If all ✅/🔵: prompt user for **manual CLI testing** with specific test cases from the plan.

---

## Part 3: Handoff Templates

### Role 1 → Role 2 (Decision Maker → Executor)

```
加载 /Users/ky230/Desktop/Private/Cascade.md

你是 2执行者

执行计划: {PLAN_PATH}

任务概要:
{TASK_SUMMARY}

关键设计约束:
{CONSTRAINTS_LIST}

修改文件: {TARGET_FILES}

按计划逐步执行，写 task.md 和 walkthrough.md 跟踪进度。不要自动 commit/push。
完成后生成 Reviewer handoff prompt。
```

### Role 2 → Role 3 (Executor → Reviewer)

```
加载 /Users/ky230/Desktop/Private/Cascade.md

你是 3审查者

请审查以下执行结果：

**计划文件:** {PLAN_PATH}
**任务追踪:** {TASK_MD_PATH}
**执行日志:** {WALKTHROUGH_MD_PATH}

**修改文件列表:**
{MODIFIED_FILES_LIST}

**关键设计约束（必须验证）:**
{CONSTRAINTS_LIST}

请对照计划逐 Task 审查，输出 code_review_report.md 到你的 Antigravity brain。
```

### Role 3 → Role 2 (Reviewer → Executor, fix round)

```
加载 /Users/ky230/Desktop/Private/Cascade.md

你是 2执行者

审查者发现以下问题需要修复：

**审查报告:** {CODE_REVIEW_REPORT_PATH}
**任务追踪:** {TASK_MD_PATH}
**执行日志:** {WALKTHROUGH_MD_PATH}

修改完成后，更新 task.md 和 walkthrough.md，并生成新的 Reviewer handoff prompt。
```

---

## Part 4: Iteration Loop

| Step | Actor | Action | Next |
|------|-------|--------|------|
| 1 | Decision Maker | Draft plan | → 2 |
| 2 | Executor | Implement + update brain files | → 3 |
| 3 | Reviewer | Audit + write report | → 4 or 2 |
| 4 | User | Manual CLI test | → 2 (bugs) or 5 |
| 5 | Executor | git commit & push (user command only) | Done |
```

---

## Task 3: Create new `Cascade-references.md` (Big Three paths)

**Files:**
- Create: `/Users/ky230/Desktop/Private/Workspace/ssH-remote-Workspace/2026-04-03/Cascade-references.md`

**Step 1: Write the references file**

```markdown
---
trigger: manual
---

# Cascade — Reference Codebases ("Big Three")

> Load this file ONLY when the plan or user explicitly requires architectural alignment
> with upstream CLI tools. Do NOT load for routine development tasks.

## Usage Rules
* Reference these codebases ONLY when architectural alignment is explicitly required.
* Use `grep_search` to locate specific patterns — **never read entire files**.
* When referencing, state WHY the reference is needed before reading.

## Paths
* **Claude Code:** `/Users/ky230/Desktop/Private/Workspace/Git/claude-code-src-haha`
* **Gemini CLI:** `/Users/ky230/Desktop/Private/Workspace/Git/gemini-cli`
* **Codex CLI:** `/Users/ky230/Desktop/Private/Workspace/Git/codex-cli`
```

---

## Verification Plan

### File Structure Check

```bash
ls -la /Users/ky230/Desktop/Private/Workspace/ssH-remote-Workspace/2026-04-03/
```

Expected:
```
Cascade.md              (~30 lines)
Cascade-workflow.md     (~100 lines)
Cascade-references.md   (~20 lines)
```

### Content Verification

```bash
wc -l /Users/ky230/Desktop/Private/Workspace/ssH-remote-Workspace/2026-04-03/*.md
```

Expected: total ~150 lines across 3 files.

### Manual Deployment (User performs after review)

```bash
cp /Users/ky230/Desktop/Private/Workspace/ssH-remote-Workspace/2026-04-03/Cascade.md /Users/ky230/Desktop/Private/Workspace/Git/Cascade/.agents/rules/Cascade.md
cp /Users/ky230/Desktop/Private/Workspace/ssH-remote-Workspace/2026-04-03/Cascade-workflow.md /Users/ky230/Desktop/Private/Workspace/Git/Cascade/.agents/rules/
cp /Users/ky230/Desktop/Private/Workspace/ssH-remote-Workspace/2026-04-03/Cascade-references.md /Users/ky230/Desktop/Private/Workspace/Git/Cascade/.agents/rules/
```

Note: `/Users/ky230/Desktop/Private/Cascade.md` is a symlink to `.agents/rules/Cascade.md`, so it auto-syncs.
