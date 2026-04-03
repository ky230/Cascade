# Cascade.md Rules Optimization — Discussion Document

> **For Decision Maker (Role 1):** This is a multi-role discussion collecting field experience from
> Roles 2 & 3. Read all sections, then decide which proposals to accept, reject, or modify.

**Goal:** Reduce cognitive load, eliminate execution errors, and simplify context window consumption
for `Cascade.md` — the always-on ruleset governing the 3-Agent Workflow.

**Current file:** `/Users/ky230/Desktop/Private/Workspace/Git/Cascade/.agents/rules/Cascade.md`
**Current size:** 110 lines / ~8.3 KB (loaded into EVERY conversation via `trigger: always_on`)

---

## Role 3 (Reviewer) Field Report

> The following pain points are from the Reviewer's perspective after executing multiple review
> rounds on the `2026-04-03-esc-cancel-fix` plan. Each item includes the root cause, a real
> incident that occurred, and a concrete fix proposal.

---

### Pain Point 1: Handoff Prompts Are Free-Form — High Error Rate

**What happened:** Role 3 generated a handoff prompt back to Role 2 with incorrect file paths
(`/Users/ky230/.gemini/antigravity/brain/task.md.resolved` — missing UUID). The user had to
manually correct three paths before Role 2 could proceed. This wasted an entire round-trip.

**Root cause:** Rule 1.7 says "include full absolute paths" but provides no structural template.
The agent must improvise the prompt text every time, and under long-context pressure, it drops
details or hallucinates paths.

**Proposal 1A — Hardcoded Handoff Templates:**

Add fill-in-the-blank templates directly into `Cascade.md`. Each role gets ONE canonical template.
The agent fills in variables and outputs the result inside a plain fenced code block. No
improvisation allowed.

```text
## Role 2 → Role 3 Handoff Template

你是 Role 3 审查者。

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

```text
## Role 3 → Role 2 Fix Handoff Template

你是 Role 2 执行者。

审查者发现以下问题需要修复。请阅读审查报告中的缺陷描述和修复要求：

**审查报告:** {CODE_REVIEW_REPORT_PATH}
**任务追踪:** {TASK_MD_PATH}
**执行日志:** {WALKTHROUGH_MD_PATH}

修改完成后，更新 task.md 和 walkthrough.md，并生成新的移交 prompt 给审查者。
```

**Benefit:** Eliminates path omission errors entirely. Agent just does variable substitution.

**Tradeoff:** Templates are rigid. If a plan has unusual context (e.g. "also check the database
migration"), the agent must append it as a freeform addendum below the template.

---

### Pain Point 2: Rule 1.6 Asks for In-Place Status Updates — Fragile File Edits

**What happened:** Rule 1.6 says the Reviewer should "update the status of issues from the
previous round (e.g., changing a resolved 🔴 to ✅)." This requires the agent to:
1. Open `code_review_report.md`
2. Locate the exact line containing a specific 🔴 emoji
3. Replace it with ✅ without corrupting surrounding markdown

In practice, this is a high-risk text manipulation. The `replace_file_content` tool requires
an exact string match, and emoji + markdown formatting makes mismatches common. Appending is
100% reliable; in-place edits are ~80% reliable.

**Proposal 2A — Append-Only Audit Log:**

Change Rule 1.6 to enforce strict append-only semantics for `code_review_report.md`:

```text
OLD: "the Reviewer should update the status of issues from the previous round
     (e.g., changing a resolved 🔴 to ✅)"

NEW: "the Reviewer MUST NOT modify previous Round sections. Instead, append a new
     `## Round N Review` section at the bottom. Reference old issue IDs and state
     whether they are now ✅ Resolved or still open. The original 🔴/🟡 markers
     in earlier rounds remain untouched as historical record."
```

**Benefit:** Zero risk of corrupting the review history. Clear chronological audit trail.

**Tradeoff:** The file grows longer across rounds. But in practice, most plans close within
2-3 rounds, so this is negligible.

---

### Pain Point 3: Rule 1.5 "Big Three" Reference — Unbounded Read Scope

**What happened:** During the initial plan drafting phase (by Role 1), the agent read thousands
of lines from `claude-code-src-haha` and `gemini-cli` to "align with upstream patterns." This
consumed a massive chunk of the context window before any actual work began. In some sessions,
this left insufficient room for the implementation itself.

**Root cause:** Rule 1.5 says "proactively read local source files before drafting plans or
writing code" — no scope limit, no trigger condition.

**Proposal 3A — Conditional + Scoped Reference:**

```text
OLD: "When requesting alignment with upstream CLI tools, proactively read local
     source files before drafting plans or writing code."

NEW: "Reference the Big Three codebases ONLY when the plan or user explicitly
     requires architectural alignment. Use `grep_search` to locate specific
     patterns — never read entire files. Maximum: 3 targeted searches per
     codebase per session."
```

**Benefit:** Prevents context window bloat. Forces surgical reads instead of exploratory browsing.

**Tradeoff:** The agent might miss broader context. But in practice, `grep_search` hits are
sufficient for pattern matching.

---

### Pain Point 4: The Entire File Is `always_on` — Unnecessary Context Tax

**What happened:** Every single conversation with the Cascade project loads all 110 lines of
rules, even if the user just wants to ask "what does this function do?" or "format this output."
The role initialization question ("Which of the 3 roles am I?") fires on every conversation,
including exploratory ones.

**Root cause:** `trigger: always_on` in the YAML frontmatter. There's no way to opt out.

**Proposal 4A — Split Into Base + Role-Specific Files:**

```text
.agents/rules/
├── Cascade.md              # Base rules only (1.1-1.4, ~30 lines, always_on)
├── Cascade-workflow.md     # 3-Agent workflow + templates (Part 2 & 3, on-demand)
└── Cascade-references.md   # Big Three paths + Rule 1.5 (on-demand)
```

- `Cascade.md` keeps only universal safety rules (no deletion, English comments, no auto-commit,
  file naming). Always loaded. Small footprint.
- `Cascade-workflow.md` contains the 3-Agent loop, handoff templates, iteration protocol. Only
  loaded when user explicitly assigns a role.
- `Cascade-references.md` contains the Big Three paths. Only loaded when architectural alignment
  is needed.

**Benefit:** A simple "explain this code" question costs ~30 lines of context instead of 110.
The 3-Agent machinery only loads when actually needed.

**Tradeoff:** User must mention "你是 Role X" to trigger the workflow rules. But this is already
the natural flow — the user always specifies the role.

> [!IMPORTANT]
> This proposal requires investigation into whether Antigravity supports conditional rule loading
> (e.g., `trigger: manual` or `trigger: keyword`). If not, this may need to be implemented as
> a slash command (`/cascade-workflow`) instead of a rule file.

---

### Pain Point 5: Role 0 Initialization Blocks Casual Conversations

**What happened:** User opened a new conversation to quickly check `git diff` on
`walkthrough.md`. The agent immediately asked "Which of the 3 roles am I?" before doing anything.
The user had to answer before the agent would proceed with a trivial task.

**Root cause:** Rule 0 is unconditional: "if the user has not explicitly specified a role, the
agent must immediately ask."

**Proposal 5A — Smart Initialization:**

```text
OLD: "Whenever an agent loads these rules, if the user has not explicitly
     specified a role, the agent must immediately ask."

NEW: "If the user's first message explicitly or implicitly involves the 3-Agent
     Workflow (e.g., mentions a plan file, asks for code review, references
     Role 2's output), ask for role confirmation. Otherwise, proceed normally
     and only ask if the conversation later enters multi-agent territory."
```

**Benefit:** Eliminates the annoying "which role?" question for quick tasks.

**Tradeoff:** Risk of the agent accidentally doing Role 2 work without proper initialization.
Mitigated by the fact that Role 2/3 operations (writing task.md, code_review_report.md) are
distinctive enough to trigger a delayed role check.

---

### Pain Point 6: Part 3 (Iteration Loop Map) Is Redundant Prose

**What happened:** The ASCII art loop diagram in Part 3 is 19 lines. It visually duplicates
what Part 2 already describes in prose. As a large language model, I derive zero additional
signal from the ASCII art — it's purely for human readability.

**Proposal 6A — Collapse Into a Compact Table:**

Replace the 19-line ASCII diagram with a 7-line table:

```markdown
| Step | Actor | Action | Next |
|------|-------|--------|------|
| 1 | Decision Maker | Draft plan | → 2 |
| 2 | Executor | Implement + update brain files | → 3 |
| 3 | Reviewer | Audit + write report | → 4 or 2 |
| 4 | User | Manual CLI test | → 2 (bugs) or 5 |
| 5 | Executor | git commit & push (user command) | Done |
```

**Benefit:** Saves 12 lines of context. Equally clear for both humans and LLMs.

**Tradeoff:** Less visually dramatic than ASCII art. But function > form for a rules file.

---

## Summary Table

| # | Pain Point | Severity | Proposal | Context Saved |
|---|-----------|----------|----------|---------------|
| 1 | Free-form handoff prompts | 🔴 High | Hardcoded templates | ~0 (adds lines, but prevents re-work) |
| 2 | In-place 🔴→✅ edits | 🟡 Medium | Append-only audit log | ~0 (policy change, not size change) |
| 3 | Unbounded Big Three reads | 🟡 Medium | Conditional + scoped grep | Saves ~1000s tokens per session |
| 4 | `always_on` loads everything | 🟡 Medium | Split into 3 files | Saves ~80 lines for casual chats |
| 5 | Role 0 blocks casual use | 🟡 Medium | Smart initialization | Saves 1 round-trip |
| 6 | Redundant ASCII loop diagram | 🔵 Low | Compact table | Saves ~12 lines |

---

## Role 2 (Executor) Field Report

> The following pain points are from the Executor's perspective after implementing the
> `2026-04-03-esc-cancel-fix` plan across 2 rounds (initial implementation + Round 2 bug fix).

---

### Pain Point E1: Brain File Paths Are Unresolvable Without `find`

**What happened:** When the user handed me the Reviewer's report path as
`/Users/ky230/.gemini/antigravity/brain/code_review_report.md.resolved`, the file didn't
exist at that path. The Reviewer's brain files live under a UUID-scoped directory
(`c4426592-...`), but the handoff prompt omitted the UUID. I had to run
`find /Users/ky230/.gemini/antigravity/brain -name "*code_review_report*"` to locate it.

**Root cause:** Each agent conversation has its own UUID brain folder. When Role 3 writes
`code_review_report.md`, it ends up at `/brain/<role3-uuid>/code_review_report.md`. But the
handoff prompt to Role 2 must include Role 3's UUID — which Role 3 knows but Role 2 doesn't.
The current rules say "include absolute paths" but don't enforce UUID injection.

**Alignment with Proposal 1A:** This is exactly the problem hardcoded templates would solve.
The template forces `{CODE_REVIEW_REPORT_PATH}` to be filled with the full UUID path.

---

### Pain Point E2: Commit vs Push Boundary Is Ambiguous

**What happened:** After completing all 5 tasks, the user said "commit 一下". I ran
`git add + commit + push` in a single chain. The user had to stop me and explain they only
wanted a local commit — push was planned for later after the entire branch was done.

**Root cause:** The rules say "Only executes `git commit` and `git push` upon the user's
final explicit command." But "commit" and "push" are often bundled by the agent as a single
VCS operation. The distinction between local commit and remote push isn't emphasized.

**Proposal E2A — Explicit Split Rule:**

```text
OLD: "Only executes git commit and git push upon the user's final explicit command."

NEW: "git commit and git push are INDEPENDENT operations. Never chain them.
     - commit: executes ONLY when user says 'commit'
     - push: executes ONLY when user explicitly says 'push'
     Never assume push follows commit. Always ask."
```

---

### Pain Point E3: Plan Line Numbers Drift After Early Edits

**What happened:** The plan referenced exact line numbers (e.g., "Modify L396-397" for Task 2).
But after Task 1 added 2 new lines to `__init__`, every subsequent line number in the plan was
off by +2. I had to mentally adjust all references for Tasks 2-5.

**Root cause:** Plans are authored against a snapshot of the code at drafting time. Each task's
edits shift line numbers for all subsequent tasks. This is inherent to line-number-based plans.

**Proposal E3A — Use Anchor Patterns Instead of Line Numbers:**

```text
OLD: "Modify: src/cascade/ui/textual_app.py:396-397 (_execute_prompt)"

NEW: "Modify: src/cascade/ui/textual_app.py → _execute_prompt() → find
     `self.run_worker(self._run_generation(user_text), exclusive=True)`"
```

Plans should reference function names + unique code snippets as anchors, not absolute line
numbers. Line numbers can be hints but must not be the primary locator.

---

### Pain Point E4: Plans Should Not Include Commit Steps

**What happened:** The plan specified a `git commit` after each of the 5 tasks. But in the
3-Agent workflow, commit only happens AFTER the Reviewer confirms all code is ✅, and ONLY
when the user explicitly commands it. The per-task commits in the plan are incorrect — they
bypass the review cycle entirely.

**Root cause:** The plan was authored with an atomic-commit-per-task philosophy that conflicts
with the 3-Agent iteration loop: Executor → Reviewer → (fix loop) → User test → commit.

**Proposal E4A — Ban Commit Steps from Plans:**

```text
Plans MUST NOT include git commit/push steps. The Executor modifies code only.
Commit/push is triggered exclusively by the user after the Reviewer confirms ✅.
Decision Makers should omit all "Step N: Commit" entries from plans.
```

---

### Pain Point E5: Round 2 Re-Entry Requires Full Context Reload

**What happened:** When the user handed me the Round 2 fix task, I had to:
1. Find the Reviewer's report (Pain Point E1)
2. Re-read the entire `textual_app.py` (770+ lines) to understand current state
3. Re-read `message_queue.py` (238 lines) because the fix required a new method there
4. Cross-reference the Reviewer's specific fix requirements against the current code

This "cold start" cost significant context window tokens just to get back to a working state.

**Root cause:** Each new handoff is a fresh agent invocation with zero memory of the previous
round. The walkthrough.md helps, but it's a summary — not a precise diff of what changed.

**Proposal E5A — Handoff Includes Diff Snapshot:**

The Role 2 → Role 3 and Role 3 → Role 2 handoff prompts should include an inline `git diff`
of the modified files. This gives the receiving agent an exact view of the current state
without needing to re-read entire files.

```text
**Inline Diff (for immediate context):**
\`\`\`diff
{GIT_DIFF_OUTPUT}
\`\`\`
```

---

### Pain Point E6: No Mandatory Verification Before Handoff

**What happened:** I ran `python3 -c py_compile` before handing off to the Reviewer, but this
was my own initiative — not a plan or rules requirement. If I had skipped it and shipped a
syntax error, the Reviewer would have wasted an entire round just discovering it.

**Root cause:** Neither the plan format nor Cascade.md requires the Executor to pass any
verification gate before generating a Reviewer handoff prompt.

**Proposal E6A — Pre-Handoff Verification Gate:**

```text
Before generating a Reviewer handoff prompt, the Executor MUST:
1. Run lint/compile on all modified files (e.g. py_compile, tsc, eslint)
2. Include the verification output in walkthrough.md
3. If verification fails, fix before handing off — never pass broken code to Reviewer
```

---

## Decision Maker Action Required

After both field reports are collected, Role 1 should:

1. Accept/reject/modify each proposal
2. If accepting Proposal 4A (file split), investigate Antigravity trigger mechanisms
3. Draft the updated `Cascade.md` (and any new files)
4. Hand back to Executor for implementation
