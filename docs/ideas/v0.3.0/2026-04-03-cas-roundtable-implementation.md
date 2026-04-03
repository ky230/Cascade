# Cascade Roundtable Skill & Rules Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create the `cas-roundtable` workflow skill and upgrade the base `Cascade-workflow.md` rules with 14 field-tested optimizations.

**Architecture:** 
This plan implements the consensus reached in `2026-04-03-roundtable-skill-design.md`. 
1. The new skill is created in the global workflows directory so the user can invoke it from anywhere using `/cas-roundtable`. 
2. The `Cascade-workflow.md` file (currently staged in the temporary directory) is upgraded to enforce L1-L4 verification, dependency graphs, enhanced handoff fields (to fix UUID isolation limits), and staging constraints.

**Tech Stack:** Markdown / Antigravity Agent Rules

---

### Task 1: Create `cas-roundtable.md` Skill File

**Files:**
- Create: `/Users/ky230/Desktop/Private/.agents/global_workflows/cas-roundtable.md`

**Step 1: Write the failing test**
(Skipped for pure documentation tasks — test relies on creation)

**Step 2: Run test to verify it fails**
Run: `ls -la /Users/ky230/Desktop/Private/.agents/global_workflows/cas-roundtable.md`
Expected: FAIL with "No such file or directory"

**Step 3: Write minimal implementation**

```markdown
---
description: 🪑 圆桌会议 — 多 Agent 结构化回顾。3 角色（决策者/执行者/审查者）各自自省 + 互评，产出三色分类 discussion 文档。适用于计划重构、流程复盘、开放问题讨论。
---

# 圆桌会议 (Roundtable) Skill

**Slash command:** `/cas-roundtable`
**Output:** `docs/plans/YYYY-MM-DD-<topic>-discussion.md`

## 1. Prerequisites
- 已开好 3 个 Agent 窗口，角色已指定 (1-Decision Maker, 2-Executor, 3-Reviewer)
- 有具体的议题要讨论
- 不依赖任何项目特定的 rules 文件（通用 skill）

## 2. 启动流程
Agent 向用户询问两项信息：
1. 议题类型（计划重构 / Bug 复盘 / 开放问题 / 其他）
2. 圆桌轮数 `N`（默认 1，决策者每次发言=一轮结束）

第一个发言的角色负责创建 discussion 文档，写好自己的 section，并为其他人预建空框架。

## 3. 发言与建议维度规范

### Role 3 (Reviewer) — 审查者发言
- **自省：** 路径准确性、分类准确性、append-only 合规、测试用例质量、上下文压力。
- **对决策者的建议 (via plan.md)：** 验收标准明确度、意图-结果 gap、约束可审计性。
- **对执行者的建议 (via task.md / walkthrough.md / code_review_report.md)：** Handoff prompt 信息完整度、walkthrough 覆盖度、修复响应质量、代码质量。

### Role 2 (Executor) — 执行者发言
- **自省：** Plan 可执行性、Review 可操作性、上下文冷启动、代码质量、**Brain 文件连续性** (跨 round/代理时历史是否完整继承)。
- **对决策者的建议 (via plan.md)：** 粒度、锚点 vs 行号、依赖顺序、验收条件。
- **对审查者的建议 (via code_review_report.md)：** 问题精确度、修复可执行性、分类合理性、handoff 完整度、**正向反馈** (是否标注了做的好的地方)。

### Role 1 (Decision Maker) — 决策者发言
- **自省 + 三色分类总结**
（仅当当前轮=N 时，完成总结：🟢 无异议 / 🟡 开放性 / 🔴 严重分歧）

## 4. 交互媒介原则
每个角色只通过**实际交互过的文件**来评价对方：
- 决策者 → 执行者：`task.md`, `walkthrough.md`
- 执行者 → 决策者：`plan.md`
- 执行者 → 审查者：`code_review_report.md`, **Handoff prompt**
- 审查者 → 决策者：`plan.md`（间接）
- 审查者 → 执行者：`task.md`, `walkthrough.md`, `code_review_report.md`

## 5. Handoff Prompt 模板
第一个角色发言完毕后，输出 handoff prompt（plain code block）给下一个角色：

\`\`\`
圆桌会议进行中 🪑

**Discussion 文档:** {DISCUSSION_MD_PATH}
**议题:** {TOPIC_DESCRIPTION}
**轮次:** Round {n} / {N}

你是 Role {X}（{ROLE_NAME}）。

请阅读 discussion 文档中其他角色的发言（如有），然后填写你的 section：
1. 自省 — 反思自己的表现
2. 对 {交互方A} 的建议 (via {交互文件})
3. 对 {交互方B} 的建议 (via {交互文件})（如适用）

填写完成后，生成下一个角色的 handoff prompt。
如果你是决策者且当前 Round = N，请额外填写三色分类总结。

**补充上下文:**
- (若适用，填写前序发言摘要或其他特殊情况)
\`\`\`
```

**Step 4: Run test to verify it passes**
Run: `ls -la /Users/ky230/Desktop/Private/.agents/global_workflows/cas-roundtable.md`
Expected: PASS with file details

**Step 5: Commit**
(No git repo specifically required for the global workflows dir here, skip commit or do it if tracking)

---

### Task 2: Upgrade `Cascade-workflow.md` Rule Definitions (Part 1 & 2)

**Files:**
- Modify: `/Users/ky230/Desktop/Private/Workspace/ssH-remote-Workspace/2026-04-03/Cascade-workflow.md:32-66`

**Step 1: Write the failing test**
Run: `grep_search /Users/ky230/Desktop/Private/Workspace/ssH-remote-Workspace/2026-04-03/Cascade-workflow.md "L1-L4"`
Expected: FAIL with no results

**Step 2: Write minimal implementation**

Target Content to Replace in `Cascade-workflow.md`:
```markdown
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
```

Replacement Content:
```markdown
### W3. Plan Authoring Rules (for Role 1)
* Plans MUST NOT include `git commit` or `git push` steps. Commit/push is triggered exclusively by the user after the Reviewer confirms ✅.
* **Locators:** Use function names + code snippets as anchors. Line numbers are hints only.
* **Format:** Provide exact markdown `code blocks` for configuration/document generation tasks.
* **Acceptance:** Summaries MUST include an obvious `Acceptance Criteria` column.
* **Dependencies:** Document cross-file dependencies graphically if modifying rule links.
* **Verification:** The plan MUST define L1~L4 checks: L1 (Existence), L2 (Structure), L3 (Content), L4 (Functional Smoke Test).

### W4. Pre-Handoff Verification Gate (for Role 2)
Before generating a Reviewer handoff prompt, the Executor MUST:
1. Ensure all edits target the explicit staging/target constraints established in the plan.
2. Run lint/compile on all modified files (e.g. `python3 -c "import py_compile; py_compile.compile('file.py')"`)
3. Include the verification output in `walkthrough.md`
4. If verification fails, fix before handing off.

---

## Part 2: Role Definitions

### Role 1: Decision Maker (决策者)
* Writes the plan file (`YYYY-MM-DD-short-desc.md`) in `docs/plans/`.
* Keep plans structural — focus on actions, not micro-details.
* Defines the manual CLI Test / Post-Deployment smoke test steps.
* Handoff: output a prompt (per W2) for the Executor with the plan's absolute path.

### Role 2: Executor (执行者)
* Modifies the codebase based on Role 1's plan.
* Writes `task.md` and `walkthrough.md` in its UUID brain folder.
* Handoff: output a prompt (per W2) to the Reviewer using the **Role 2 → Role 3 Template** below. Include `前轮 Brain 文件` map if UUID disconnected.
* Receives feedback from Role 3. Only commits/pushes when user explicitly commands it.

### Role 3: Reviewer (审查者)
* Audits execution against the plan, brain files, and repo code.
* Writes `code_review_report.md` in its UUID brain folder (Append Only).
* When appending a new Round, if replacing a previous verdict, annotate the old one with `> ⚠️ 此 Verdict 已被 {Round N} 取代`.
* Issue classifications:
  * 🔴 **Critical** — Must fix immediately
  * 🟡 **Medium** — Discuss/fix (Use `🟡-High / 🟡-Low` if ≥ 3 Medium issues)
  * 🔵 **Deferred** — User agreed to defer
  * ✅ **Correct** — Verified
* If 🔴/🟡 found: handoff back to Role 2 using **Role 3 → Role 2 Template** below.
* If all ✅/🔵: prompt user for **Manual CLI Test** with specific test cases from the plan.
```

**Step 3: Run test to verify it passes**
Run: `grep_search /Users/ky230/Desktop/Private/Workspace/ssH-remote-Workspace/2026-04-03/Cascade-workflow.md "L1~L4"`
Expected: PASS indicating 1 result

---

### Task 3: Upgrade `Cascade-workflow.md` Handoff Templates & Iteration Loop

**Files:**
- Modify: `/Users/ky230/Desktop/Private/Workspace/ssH-remote-Workspace/2026-04-03/Cascade-workflow.md` (Part 3 and Part 4)

**Step 1: Write the failing test**
Run: `grep_search /Users/ky230/Desktop/Private/Workspace/ssH-remote-Workspace/2026-04-03/Cascade-workflow.md "前轮 Brain 文件"`
Expected: FAIL indicating 0 results

**Step 2: Write minimal implementation**

Target Content to Replace in `Cascade-workflow.md`:
```markdown
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

Replacement Content:
```markdown
### Role 2 → Role 3 (Executor → Reviewer)

```text
加载 /Users/ky230/Desktop/Private/Cascade.md

你是 3审查者

请审查以下执行结果：

**计划文件:** {PLAN_PATH}
**任务追踪:** {TASK_MD_PATH}
**执行日志:** {WALKTHROUGH_MD_PATH}

**前轮 Brain 文件 (如果UUID断裂):**
- task.md: {OLD_TASK_MD_PATH}
- walkthrough.md: {OLD_WALKTHROUGH_MD_PATH}

**修改文件列表:**
{MODIFIED_FILES_LIST}

**关键设计约束（必须验证）:**
{CONSTRAINTS_LIST}

**补充上下文:**
{ADDITIONAL_CONTEXT_OR_ABSTRACT}

请对照计划逐 Task 审查，输出 code_review_report.md 到你的 Antigravity brain。
```

### Role 3 → Role 2 (Reviewer → Executor, fix round)

```text
加载 /Users/ky230/Desktop/Private/Cascade.md

你是 2执行者

审查者发现以下问题需要修复：

**审查报告:** {CODE_REVIEW_REPORT_PATH}
**任务追踪:** {TASK_MD_PATH}
**执行日志:** {WALKTHROUGH_MD_PATH}

**前轮 Brain 文件 (如果UUID断裂):**
- code_review_report.md: {OLD_CODE_REVIEW_REPORT_PATH}

**补充上下文:**
{ADDITIONAL_CONTEXT_OR_ABSTRACT}

修改完成后，更新 task.md 和 walkthrough.md，并生成新的 Reviewer handoff prompt。
```

---

## Part 4: Iteration Loop

| Step | Actor | Action | Next |
|------|-------|--------|------|
| 1 | Decision Maker | Draft plan | → 2 |
| 2 | Executor | Implement + update brain files | → 3 |
| 3 | Reviewer | Audit + write report | → 4 (Pass) or 2 (Fix) |
| 4 | User | Manual CLI test + Post-Deployment Smoke Test | → 2 (bugs) or 5 |
| 5 | Executor | git commit & push (upon user command only) | Done |
```

**Step 3: Run test to verify it passes**
Run: `grep_search /Users/ky230/Desktop/Private/Workspace/ssH-remote-Workspace/2026-04-03/Cascade-workflow.md "前轮 Brain 文件"`
Expected: PASS indicating results found.

---
