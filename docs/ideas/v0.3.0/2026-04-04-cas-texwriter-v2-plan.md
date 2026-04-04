# cas-texwriter v2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite `cas-texwriter.md` into a 4-module architecture (Context Ingestion / Write Constraints / Build Pipeline / Output Format), patch `definitions.tex` & `Makefile`, and upgrade `Cascade-workflow.md` with Executor Safety Checklist + `🔴 Requires New Plan` classification.

**Architecture:** The skill file is rewritten from scratch as a single self-contained workflow (~120 lines). No sub-directory reference files needed — all constraints are inline. Paper build pipeline stays at `docs/paper/` with CMS AN `cascade-ANnote.tex` as the main entry. `Cascade-workflow.md` receives two surgical additions (Role 2 checklist, Role 3 new classification).

**Tech Stack:** Markdown (skill definition), LaTeX, Make, YAML (none — `00-metadata.yaml` is now legacy)

**Source Documents:**
- Roundtable Decision: `docs/ideas/v0.3.0/2026-04-04-cas-texwriter-v2-discussion.md`
- Action Items: A1–A10 from Role 1 final ruling

---

## Task 1: Rewrite `cas-texwriter.md` — Full 4-Module Skill File (A1–A4, A6)

**Files:**
- Rewrite: `/Users/ky230/Desktop/Private/.agaobal_workflows/cas-texwriter.md`

**Step 1: Overwrite the skill file with the complete v2 content**

Write the following content verbatim to `/Users/ky230/Desktop/Private/.agaobal_workflows/cas-texwriter.md`:

```markdown
---
description: cas-texwriter — LaTeX Draft Generator & Digest Extractor
---

# cas-texwriter v2

## 概述

将 Cascade 开发文档（walkthrough, plans, ideas, source code）提纯为学术叙事，生成可直接 `\input{}` 到 CMS AN 模板的原生 LaTeX 正文片段。

**两种调用模式：**
- `/cas-texwriter digest` — 从开发日志提取结构化摘要，输出到控制台
- `/cas-texwriter draft <section>` — 针对指定章节，生成 LaTeX 草稿片段供人工审校

---

## 模块 1: 上下文吸收层 (Context Ingestion)

### 上下文源（按优先级）

| 优先级 | 源 | 用途 |
|--------|---|------|
| 1 | `docs/walkthrough.md` | 版本演进主线 |
| 2 | `docs/plans/` | 各 Phase 技术细节 |
| 3 | `docs/ideas/` | 设计讨论与决策记录 |
| 4 | `src/cascade/` 源码结构 | 验证实际实现 |

### 论文结构参考 (FROZEN — 仅圆桌修改)

> ⚠️ Agent 检测到对 FROZEN 段落的写入意图时，必须 ABORT 并提示用户。

| 章节 | 文件 | 标题 |
|------|------|------|
| §1 | `01-introduction.tex` | Introduction |
| §2 | `02-related-work.tex` | Related Work and Distinctive Positioning |
| §3 | `03-architecture.tex` | System Architecture and Infrastructure |
| §4 | `04-agent-tools.tex` | Agent Coordination and Tool Constraining |
| §5 | `05-proof-of-concept.tex` | Proof-of-Concept: A CMS Analysis Workflow |
| §6 | `06-evolution.tex` | Evolution Roadmap and Developer Changelog |
| §7 | `07-conclusion.tex` | Conclusion |

### 核心叙事锚点 (FROZEN — 仅圆桌修改)

1. **HPC-Native** — CERN lxplus / HTCondor 原生支持，环境隔离架构
2. **Combine-ROOT** — CMS Combine + 深度 ROOT 宏集成
3. **Universal-API** — 多模型统一 API 抽象层 (ModelClient)
4. **Inversion** — 基于反转的防幻觉机制

### 竞品对齐清单 (FROZEN — 仅圆桌修改)

| 框架 | 关键差异点 |
|------|-----------|
| LLM4HEP | End-to-end automation; Cascade focuses on harness, not physics |
| HEPTAPOD | MC event generation; Cascade targets real data analysis on HPC |
| AI-Native Whitepaper | Community vision; Cascade is a concrete implementation |
| ColliderAgent | Theory-to-inference pipeline; Cascade is HPC-infra-first |
| JFC (Automate HEP) | Autonomous analysis; Cascade emphasizes human-in-loop control |

---

## 模块 2: 写作执行约束 (Write Constraints)

### 文件权限矩阵

| 操作类型 | 权限 | 触发条件 |
|---------|------|---------|
| 读取 `.tex` 文件分析结构 | ✅ 自动 | 任何 cas-texwriter 调用 |
| 向 `.tex` 文件追加段落内容 | ✅ 需用户指令 | 用户给出明确的章节和内容方向 |
| 修改 `.tex` 文件现有段落 | ⚠️ 需用户指令 + 预览确认 | 用户指定修改范围 |
| 删除 `.tex` 文件内容 | ❌ 永不自动 | 必须输出命令供人工执行 |
| 编译 PDF (`make`) | ✅ 可自动 | 任何写入操作完成后 |
| 编译后清理缓存 | ✅ 自动 | 任何成功编译之后 |

> **追加 vs 修改 判定规则：** 空文件或仅含 `\section{}` / `\subsection{}` 标题（无正文段落）的文件视为"追加"目标。已有正文段落的文件一律视为"修改"目标，需先预览 diff 再确认。

---

## 模块 3: 编译与清理流水线 (Build Pipeline)

编译命令（由 Makefile 管理）：
```
make -C docs/paper all
```

**规则：** 编译成功后 `latexmk -C` 彻底清理所有中间文件（含 `.bbl`），仅保留 `.tex` 源文件和 `.pdf` 产出。

**PDF 视觉验证要求：** 编译成功后，Agent 须在 walkthrough 中描述：
1. Title page: CMS header、标题、作者信息是否正确显示
2. 目录页: 章节列表是否完整
3. 正文: 图片浮动位置是否正常、公式渲染是否正确

---

## 模块 4: 输出格式规范 (Output Format)

Agent 产出的 LaTeX 必须满足：

1. **可直接使用：** 输出内容可直接 `\input{}` 或粘贴入 `\section{}` 正文
2. **引用格式：** 使用 `\cite{bibkey}` 对齐 `cms_unsrt.bst`，引用 `main.bib` 中的条目
3. **模板宏：** 使用 `ptdr-definitions.sty` 提供的原生 CMS 宏（`\pt`, `\GeV`, `\MET` 等），**不得重定义**
4. **Cascade 专有术语：** 仅使用 `definitions.tex` 中定义的宏（`\cascade`, `\cascadecli`, `\lxplus` 等）
5. **写作风格：** 放大技术细节（架构、工具约束），收敛物理演示（物理作为 Payload 放附录）
```

**Step 2: Verify file is readable**

Run: `head -3 /Users/ky230/Desktop/Private/.agaobal_workflows/cas-texwriter.md`
Expected:
```
---
description: cas-texwriter — LaTeX Draft Generator & Digest Extractor
---
```

---

## Task 2: Patch Makefile — Auto-Clean After Build (A5)

**Files:**
- Modify: `/Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/Makefile`

**Step 1: Add `latexmk -C` after successful compilation**

Replace the current build rule (line 8–9):
```makefile
$(TARGET): cascade-ANnote.tex
	latexmk -pdf -interaction=nonstopmode cascade-ANnote.tex
```

With:
```makefile
$(TARGET): cascade-ANnote.tex
	latexmk -pdf -interaction=nonstopmode cascade-ANnote.tex
	latexmk -C
```

**Step 2: Verify Makefile dry-run**

Run: `make -n -f /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/Makefile all 2>&1 | head -5`
Expected: Shows the `latexmk -pdf` command followed by `latexmk -C`

---

## Task 3: Patch `definitions.tex` — Add Warning Header (A7)

**Files:**
- Modify: `/Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/definitions.tex`

**Step 1: Replace the first two comment lines**

Replace (lines 1–2):
```latex
% Cascade-specific macro definitions
% Modeled after Prism/HIG-25-006 definitions.tex structure
```

With:
```latex
% Cascade-specific macro definitions
% Modeled after Prism/HIG-25-006 definitions.tex structure
%
% WARNING: Do NOT redefine macros from ptdr-definitions.sty (e.g. \pt, \GeV, \MET).
% Only add Cascade-specific terms below. See cas-texwriter v2 roundtable ruling Y5.
```

**Step 2: Remove the redundant `\pT` redefinition (lines 15-17)**

The macros `\pT`, `\sqrts`, `\fb` duplicate what `ptdr-definitions.sty` already provides. Replace (lines 14–17):
```latex
% ---- Physics / CMS terms ----
\newcommand{\pT}{\ensuremath{p_{\text{T}}}\xspace}
\newcommand{\sqrts}{\ensuremath{\sqrt{s}}\xspace}
\newcommand{\fb}{\ensuremath{\text{fb}^{-1}}\xspace}
```

With:
```latex
% ---- Physics / CMS terms ----
% \pt, \sqrts, \GeV etc. are provided by ptdr-definitions.sty — do NOT redefine here.
% Only add physics terms NOT in ptdr-definitions.sty below:
```

**Step 3: Verify definitions.tex compiles**

Run: `cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper && latexmk -pdf -interaction=nonstopmode cascade-ANnote.tex 2>&1 | tail -3`
Expected: Compilation succeeds (no undefined control sequence errors for `\pT` — if any chapter uses `\pT`, it needs to be changed to `\pt` from ptdr-definitions).

**Step 4: Check if any `.tex` file references `\pT`**

Run: `grep -rn '\\pT' /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/*.tex`
Expected: If any hits found, replace `\pT` → `\pt` in those files. If no hits, proceed.

---

## Task 4: Patch `Cascade-workflow.md` — Executor Safety Checklist (A8)

**Files:**
- Modify: `/Users/ky230/Desktop/Private/Workspace/ssH-remote-Workspace/2026-04-03/Cascade-workflow.md`

**Step 1: Append Safety Checklist to Role 2 definition**

After line 62 (`* Receives feedback from Role 3. Only commits/pushes when user explicitly commands it.`), insert:

```markdown
* **Executor Safety Checklist (mandatory before handoff):**
  1. Any `rm` command — regardless of target — MUST be output for user manual execution. Never auto-run.
  2. Before modifying files outside Git tracking (e.g. `.gitignore`-excluded dirs), create a timestamped local backup or flag as 🔴 Blocker in walkthrough.
  3. After successful compilation, describe PDF visual layout in walkthrough (title page, TOC, figures).
```

**Step 2: Verify the insertion**

Run: `grep -A5 'Safety Checklist' /Users/ky230/Desktop/Private/Workspace/ssH-remote-Workspace/2026-04-03/Cascade-workflow.md`
Expected: Shows the 3-item checklist

---

## Task 5: Patch `Cascade-workflow.md` — `🔴 Requires New Plan` Classification (A9)

**Files:**
- Modify: `/Users/ky230/Desktop/Private/Workspace/ssH-remote-Workspace/2026-04-03/Cascade-workflow.md`

**Step 1: Add new classification after line 72**

After `  * ✅ **Correct** — Verified` (line 72), insert:

```markdown
  * 🔴 **Requires New Plan** — Issue requires architectural-level changes beyond current plan scope (e.g. template migration, new dependency systems, cross-module refactoring). Reviewer MUST escalate to Decision Maker (Role 1) for a formal supplementary plan. Do NOT issue as Required Fix to Executor.
```

**Step 2: Verify the insertion**

Run: `grep -n 'Requires New Plan' /Users/ky230/Desktop/Private/Workspace/ssH-remote-Workspace/2026-04-03/Cascade-workflow.md`
Expected: Shows the new line with `🔴 **Requires New Plan**`

---

## Task 6: Clean Up Legacy Files (A1 — remove old reference directory)

**Files:**
- Delete: `/Users/ky230/Desktop/Private/.agaobal_workflows/cas-texwriter/` (entire directory, if it exists)

**Step 1: Check if old reference directory exists**

Run: `ls -la /Users/ky230/Desktop/Private/.agaobal_workflows/cas-texwriter/ 2>&1`
Expected: Either lists old files (workflow-steps.md, digest-schema.yaml, etc.) or shows "No such file or directory"

**Step 2: If exists, output rm command for user**

If the directory exists, output to user (do NOT auto-execute):
```bash
# ⚠️ User: please review and run manually:
rm -rf /Users/ky230/Desktop/Private/.agaobal_workflows/cas-texwriter/
```

---

## Task 7: Verification — End-to-End Check

**Step 1: Verify skill file structure (4 modules present)**

Run: `grep -c '## 模块' /Users/ky230/Desktop/Private/.agaobal_workflows/cas-texwriter.md`
Expected: `4`

**Step 2: Verify FROZEN sections**

Run: `grep -c 'FROZEN' /Users/ky230/Desktop/Private/.agaobal_workflows/cas-texwriter.md`
Expected: `3` (论文结构参考, 核心叙事锚点, 竞品对齐清单)

**Step 3: Verify permission matrix has 6 rows**

Run: `grep -c '|.*|.*|.*|' /Users/ky230/Desktop/Private/.agaobal_workflows/cas-texwriter.md | head -1`
Expected: At least 6 data rows in the 权限矩阵 table

**Step 4: Verify Makefile auto-clean**

Run: `grep 'latexmk -C' /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/Makefile`
Expected: Shows the `latexmk -C` line

**Step 5: Verify definitions.tex warning**

Run: `head -5 /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/definitions.tex`
Expected: Shows the WARNING comment about ptdr-definitions.sty

**Step 6: Verify Cascade-workflow.md patches**

Run: `grep -c 'Safety Checklist\|Requires New Plan' /Users/ky230/Desktop/Private/Workspace/ssH-remote-Workspace/2026-04-03/Cascade-workflow.md`
Expected: `2`

**Step 7: Compile PDF to verify nothing broke**

Run: `cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper && make all 2>&1 | tail -5`
Expected: Compilation succeeds, PDF generated, cache cleaned

---

## Execution Notes

- **Do NOT auto-commit** — all changes should be reviewed before committing
- **Do NOT auto-run `rm`** — output the command for user manual execution (Cascade.md §1.2)
- **`00-metadata.yaml` is now legacy** — do not delete it (user may reference it), but it is no longer authoritative
- **`appendix-changelog.tex` is not `\input{}`ed** in the current `cascade-ANnote.tex` — this is a known orphan file to be addressed in a future cleanup
