# cas-texwriter Skill Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create the `/cas-texwriter` skill that synchronizes Cascade development docs into academic paper source files, with an 8-step Digest-First Patch workflow, dual human gates, and structure verification.

**Architecture:** Modular skill split — slim main workflow file (~100 lines) with 4 reference files loaded on-demand. Paper source lives in `docs/paper/*.md` (Markdown), built via pandoc → LaTeX → PDF. Agent writes only content; build system is human-maintained.

**Tech Stack:** Markdown, YAML, pandoc, pandoc-crossref, latexmk, XeLaTeX

**Source Documents:**
- Roundtable: `docs/ideas/v0.3.0/2026-04-04-cas-texwriter-design-discussion.md`
- Implementation Plan: `implementation_plan.md` (approved)

---

## Task 1: Create Main Skill File

**Files:**
- Create: `~/.gemini/antigravity/global_workflows/cas-texwriter.md`

**Step 1: Write the main skill file**

Create `~/.gemini/antigravity/global_workflows/cas-texwriter.md`:

```markdown
---
description: cas-texwriter — 将 Cascade 开发文档同步到学术论文。支持 init（骨架生成）和常规更新（8 步 Digest-First Patch）两种模式。
---

# cas-texwriter

## 概述

将 `docs/walkthrough.md` + `docs/plans/**` 中的工程文档，提纯并同步到 `docs/paper/*.md` 学术论文源文件。

**两种调用模式：**
- `/cas-texwriter init` — 一次性骨架生成（PILLAR 锚点 + heading 占位）
- `/cas-texwriter` — 常规更新（Digest-First Patch 8 步流水线）

## 文件权限矩阵（HARD CONSTRAINT）

| 路径 | 读 | 写 | 规则 |
|------|---|---|------|
| `docs/paper/0[1-7]*.md` | ✅ | ✅ 需 HUMAN_GATE | PILLAR + Heading Registry 保护 |
| `docs/paper/appendix-changelog.md` | ✅ | ✅ append-only | 无需人工审批 |
| `docs/paper/appendix-traces.md` | ✅ | ❌ | 人工维护 |
| `docs/paper/appendix-prompts.md` | ✅ | ❌ | 人工维护 |
| `docs/paper/00-metadata.yaml` | ✅ | ❌ | 人工维护 |
| `docs/paper/_digests/*.yaml` | ✅ | ✅ 仅 DIGEST_GENERATE | status: draft 输出 |
| `docs/paper/_build/**` | ❌ | ❌ | **完全不可见，禁止读写** |
| `docs/walkthrough.md` | ✅ | ❌ | 只读输入源 |
| `docs/plans/**` | ✅ | ❌ | 只读输入源 |

## init 模式

**触发：** 用户调用 `/cas-texwriter init`
**前置检查：** `docs/paper/00-metadata.yaml` 中 `scaffold_created` 不存在或为 false
**动作：**
1. 读取 `00-metadata.yaml` 中的 `chapters` 配置和 `structure_protection` 定义
2. 为每个章节生成 `docs/paper/XX-name.md`，包含：
   - `required_headings` 中定义的所有 heading
   - PILLAR 锚点（`<!-- PILLAR:Name :: BEGIN/END -->`）含占位符
   - `<!-- TODO: 填写核心命题句 -->` 提示
3. 生成 `appendix-changelog.md` 基本结构
4. 输出清单供人工确认
5. **不自动 commit**——人工审校后手动 commit

**完成后提示：** "骨架已生成。请手写四个 PILLAR 核心命题句，然后 commit。"

## 常规更新（8 步 Digest-First Patch）

**触发：** 用户调用 `/cas-texwriter`
**前置检查：** `scaffold_created: true`，否则提示先运行 init

### 工作流概览

```
Step 1:   VERSION_DETECT       — 从 walkthrough 提取版本号
Step 1.5: ROUTE_DECISION       — total_bytes > 60KB → 方案 A; ≤ 60KB → 方案 B
Step 2:   DIGEST_GENERATE      — Plan → YAML digest (draft)
                                 ⮕ 加载参考: cas-texwriter/digest-schema.yaml
                                 ⮕ 加载参考: cas-texwriter/classification-examples.md
Step 2.5: 🧑 DIGEST_REVIEW    — 人工审校 (draft → reviewed)
Step 3:   WALKTHROUGH_EXTRACT  — 三级分类 [A]/[B]/[C]
Step 4:   SELECTIVE_DEEPREAD   — 仅 [A] 类 plan 全文 (≤ 3 files, per_file ≤ 20K tokens)
Step 5:   ACADEMIC_TRANSLATE   — 工程语言 → 学术叙事
                                 ⮕ 加载参考: cas-texwriter/markdown-spec.md
Step 5.5: CONFLICT_DETECT      — Jaccard 0.85 + false_positive_risk
Step 6:   🧑 PATCH_PREVIEW    — diff 预览 (PILLAR ZONE 标注), 人工批准
Step 7:   PATCH_WRITE          — 写入 + backup
Step 8:   STRUCTURE_VERIFY     — V1 锚点 + V2 Heading Registry + V3 命题句基线
```

**方案 B (Changelog-Only Fast Path)：**
当 `total_plan_bytes ≤ 60KB` 时触发。仅从 walkthrough 提取 Phase 列表，格式化为 Changelog bullet list，append 到 `appendix-changelog.md`，跳过正文 patch。

### 每步详细规格

⮕ 加载 `cas-texwriter/workflow-steps.md` 获取每步的 Input/Output/失败处理。

## 四大 PILLAR 生态位

1. **HPC-Native** — CERN lxplus / HTCondor 原生支持
2. **Combine-ROOT** — CMS Combine + 深度 ROOT 宏集成
3. **Universal-API** — 多模型统一 API 抽象层
4. **Inversion** — 基于反转的防幻觉机制

## 三级分类规则

| 分类 | 标签 | 去向 |
|------|------|------|
| [A] Methodology-worthy | `methodology_worthy: true` | 正文 patch |
| [B] Architecture-evidence | `architecture_evidence: true` | 正文脚注 + Changelog |
| [C] Changelog-only | 两项均 false | 仅 Changelog |

⮕ 详细判定规则和 few-shot 示例见 `cas-texwriter/classification-examples.md`
```

**Step 2: Verify file exists and is readable**

Run: `cat ~/.gemini/antigravity/global_workflows/cas-texwriter.md | head -5`
Expected: Shows the YAML frontmatter `---` and description line

**Step 3: Commit**

```bash
# No git commit needed — this is an Antigravity workflow file, not in the Cascade repo
```

---

## Task 2: Create Reference Files

**Files:**
- Create: `~/.gemini/antigravity/global_workflows/cas-texwriter/workflow-steps.md`
- Create: `~/.gemini/antigravity/global_workflows/cas-texwriter/digest-schema.yaml`
- Create: `~/.gemini/antigravity/global_workflows/cas-texwriter/markdown-spec.md`
- Create: `~/.gemini/antigravity/global_workflows/cas-texwriter/classification-examples.md`

### Step 1: Create workflow-steps.md

Contains the full I/O/failure-handling spec for all 8 steps. Content is extracted verbatim from the roundtable discussion document (Role 2, Round 2, 任务 1), lines 626-821.

Key content per step:
- **Step 1 VERSION_DETECT:** Input: `docs/walkthrough.md`. Parse `# [vX.Y.Z]` heading. Fail → ABORT.
- **Step 1.5 ROUTE_DECISION:** `stat *.md` in `docs/plans/{version}/`. >60KB → A, ≤60KB → B. Empty dir → WARN + B.
- **Step 2 DIGEST_GENERATE:** Per-plan LLM extraction. Output `_digests/{version}-digest.yaml` with `status: draft`. Skip if `status: reviewed` exists. Chunk oversized files by `## Phase`.
- **Step 2.5 DIGEST_REVIEW:** Human gate. `confidence: low` top-sorted with ⚠️. abort/approve.
- **Step 3 WALKTHROUGH_EXTRACT:** Combine walkthrough + reviewed digest → [A]/[B]/[C] lists. [B] uses `[^footnote-id]` pandoc syntax.
- **Step 4 SELECTIVE_DEEPREAD:** Load ≤3 plan files for [A] phases. `per_file_token_limit: 20K`. Extract `{why, how, key_concepts, target_sections}`.
- **Step 5 ACADEMIC_TRANSLATE:** Generate PatchSet. Rules: `<!-- [ref: Phase X.Y.Z] -->` provenance tags, PILLAR thesis immutable, `markdown_spec` compliant.
- **Step 5.5 CONFLICT_DETECT:** Jaccard 0.85 threshold, `false_positive_risk` annotation. No external embedding model.
- **Step 6 PATCH_PREVIEW:** `git diff --no-index` format. `[PILLAR ZONE]` prefix for pillar regions. Selective apply: `apply all` / `apply [1,3]` / `abort`. Changelog always writes.
- **Step 7 PATCH_WRITE:** Write approved patches. Backup to `_build/.pre_patch_backup/`. Changelog append-only.
- **Step 8 STRUCTURE_VERIFY:** V1 (PILLAR anchors), V2 (Heading Registry), V3 (`.pillar_baselines` string match). Pass → delete backup. Fail → ROLLBACK.

**Step 2: Create digest-schema.yaml**

Contains the full Digest YAML Schema v1.0 extracted from the roundtable (Role 2, Round 2, 任务 2), lines 797-876. Includes:
- Top-level fields: `version`, `status`, `generated_at`, `reviewed_at`, `reviewed_by`, `digest_schema`
- Phase entry fields: `id`, `name`, `abstract`, `pillars`, `methodology_worthy`, `architecture_evidence`, `confidence`, `source_plan`, `key_files`, `target_sections`
- 7 validation rules (original 5 + reviewer's #6 mutual exclusion + #7 target_sections path check)
- Complete example file (v0.3.0 with 3 phases)

**Step 3: Create markdown-spec.md**

Pandoc-compatible Markdown subset for `docs/paper/*.md`:

| Element | Allowed | Notes |
|---------|---------|-------|
| Headings `#`-`####` | ✅ | `##` and `###` locked by Heading Registry |
| Bold/italic | ✅ | Standard emphasis |
| Code spans `` ` `` | ✅ | Inline only |
| Fenced code blocks | ✅ | For config/code examples |
| Pipe tables | ✅ | pandoc `pipe_tables` extension |
| Footnotes `[^id]` | ✅ | [B] class only, ≤80 chars per footnote |
| Math `$...$` / `$$...$$` | ✅ | HEP essential |
| Cross-references `[@sec:xxx]` | ✅ | pandoc-crossref syntax |
| Citations `[@key]` | ✅ | pandoc-citeproc syntax |
| Images `![](path)` | ✅ | Only `_build/figures/` paths |
| Mermaid | ❌ | Use pre-rendered PNG/SVG |
| Raw HTML | ❌ | Except `<!-- comments -->` |
| HTML tags | ❌ | No `<div>`, `<span>`, etc. |

**Step 4: Create classification-examples.md**

Few-shot examples for Agent classification during DIGEST_GENERATE:

```
[A] Methodology-worthy:
- "Non-Blocking Message Queue with 3-tier priority"
  → pillars: ["HPC-Native"], methodology_worthy: true
  Reasoning: Directly implements pipeline orchestration pattern central to HPC-Native claim.

[B] Architecture-evidence:
- "Textual TUI Migration"
  → pillars: [], architecture_evidence: true
  Reasoning: Does not directly serve any pillar, but demonstrates Layer 6 (UI) separation in 8-Layer Architecture.

[C] Changelog-only:
- "Input History JSONL persistence"
  → pillars: [], methodology_worthy: false, architecture_evidence: false
  Reasoning: Pure UX feature, no architectural significance.
```

**Step 5: Verify all 4 files exist**

Run: `ls -la ~/.gemini/antigravity/global_workflows/cas-texwriter/`
Expected: 4 files listed (workflow-steps.md, digest-schema.yaml, markdown-spec.md, classification-examples.md)

---

## Task 3: Create `docs/paper/00-metadata.yaml` Template

**Files:**
- Create: `/Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/00-metadata.yaml`

**Step 1: Write the metadata template**

```yaml
# ═══════════════════════════════════════════
# Cascade Technical Whitepaper — Metadata
# ═══════════════════════════════════════════

# --- Document Info ---
title: "Cascade: An HPC-Native Multi-Agent Framework for High Energy Physics Analysis Workflows"
subtitle: "A Technical Whitepaper"
author:
  - name: "Author Name"
    affiliation: "Institute"
    email: "email@example.com"
date: 2026
abstract: |
  <!-- TODO: 写完正文后最后填写 -->

# --- Scaffold State ---
scaffold_created: false        # /cas-texwriter init 成功后改为 true

# --- Four Pillars ---
pillars:
  - id: "HPC-Native"
    label: "HPC-Native Architecture"
    description: "CERN lxplus / HTCondor native support"
  - id: "Combine-ROOT"
    label: "Native Combine/ROOT Support"
    description: "CMS Combine + deep ROOT macro integration"
  - id: "Universal-API"
    label: "Universal ModelClient API"
    description: "Multi-model unified API abstraction layer"
  - id: "Inversion"
    label: "Inversion Anti-Hallucination"
    description: "Inversion-based anti-hallucination mechanism"

# --- Chapter Structure ---
chapters:
  - file: "01-introduction.md"
    title: "Introduction"
  - file: "02-related-work.md"
    title: "Related Work and Distinctive Positioning"
  - file: "03-architecture.md"
    title: "System Architecture and Infrastructure"
    pillars: ["HPC-Native", "Universal-API"]
  - file: "04-agent-tools.md"
    title: "Agent Coordination and Tool Constraining"
    pillars: ["Combine-ROOT", "Inversion"]
  - file: "05-proof-of-concept.md"
    title: "Proof-of-Concept: A CMS Analysis Workflow"
  - file: "06-evolution.md"
    title: "Evolution Roadmap and Developer Changelog"
  - file: "07-conclusion.md"
    title: "Conclusion"

# --- Structure Protection (Heading Registry) ---
structure_protection:
  "03-architecture.md":
    required_headings:
      - "## 3. System Architecture and Infrastructure"
      - "### 3.1 The 8-Layer Abstraction Architecture"
      - "### 3.2 Pipeline Orchestration on HPC Clusters"
      - "### 3.3 Universal ModelClient Layer"
    allow_new_subsections: true
  "04-agent-tools.md":
    required_headings:
      - "## 4. Agent Coordination and Tool Constraining"
      - "### 4.1 Schema-Validated Tool Wrappers for HEP"
      - "### 4.2 Multi-Agent Review and Quality Assurance"
      - "### 4.3 The \"Inversion\" Mechanism"
    allow_new_subsections: true

# --- Markdown Subset Spec ---
markdown_spec:
  allowed:
    - headings          # ## through ####
    - emphasis          # **bold**, *italic*
    - code_spans        # `inline code`
    - fenced_code       # ```language ... ```
    - pipe_tables       # | col | col |
    - footnotes         # [^id]
    - math_inline       # $...$
    - math_display      # $$...$$
    - crossref          # [@sec:xxx], [@fig:xxx]
    - citations         # [@bibkey]
    - images            # ![caption](_build/figures/path)
    - html_comments     # <!-- ... --> (for PILLAR anchors, ref tags)
  forbidden:
    - mermaid
    - raw_html          # no <div>, <span>, etc.
    - html_tags
    - internal_links    # no [text](file.md) — use [@sec:xxx]
  constraints:
    footnote_max_length: 80   # characters per footnote text

# --- Classification Examples (for DIGEST_GENERATE) ---
classification_examples:
  - input: "Non-Blocking Message Queue with 3-tier priority"
    output:
      pillars: ["HPC-Native"]
      methodology_worthy: true
      architecture_evidence: false
    reasoning: "Directly implements pipeline orchestration pattern central to HPC-Native claim."
  - input: "Textual TUI Migration"
    output:
      pillars: []
      methodology_worthy: false
      architecture_evidence: true
    reasoning: "Does not directly serve any pillar, but demonstrates Layer 6 (UI) separation."
  - input: "Input History JSONL persistence"
    output:
      pillars: []
      methodology_worthy: false
      architecture_evidence: false
    reasoning: "Pure UX feature, no architectural significance."
```

**Step 2: Verify YAML is valid**

Run: `python3 -c "import yaml; yaml.safe_load(open('/Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/00-metadata.yaml')); print('YAML OK')" `
Expected: `YAML OK`

**Step 3: Create directory structure (no commit yet)**

Run: `mkdir -p /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/_digests /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/_build/templates /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/_build/filters /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/_build/figures`
Expected: Directories created silently

---

## Task 4: Create `_build/` Artifacts (Makefile + Template + Registry)

**Files:**
- Create: `/Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/_build/Makefile`
- Create: `/Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/_build/templates/arxiv-clean.tex`
- Create: `/Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/_build/templates/registry.yaml`
- Create: `/Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/_build/filters/crossref-meta.yaml`
- Create: `/Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/_build/references.bib`
- Create: `/Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/_build/README.md`

### Step 1: Write Makefile

Key points from roundtable (with reviewer F1 fix applied — crossref before citeproc):

```makefile
# Cascade Technical Whitepaper — Build Pipeline
# Usage: make pdf | make draft | make clean | make wordcount

PAPER_DIR  := $(dir $(MAKEFILE_LIST))..
BUILD_DIR  := $(dir $(MAKEFILE_LIST))
OUT_DIR    := $(BUILD_DIR)output
TEMPLATE   := $(BUILD_DIR)templates/arxiv-clean.tex
BIB        := $(BUILD_DIR)references.bib
METADATA   := $(PAPER_DIR)/00-metadata.yaml

SOURCES := $(PAPER_DIR)/01-introduction.md \
           $(PAPER_DIR)/02-related-work.md \
           $(PAPER_DIR)/03-architecture.md \
           $(PAPER_DIR)/04-agent-tools.md \
           $(PAPER_DIR)/05-proof-of-concept.md \
           $(PAPER_DIR)/06-evolution.md \
           $(PAPER_DIR)/07-conclusion.md

APPENDICES := $(PAPER_DIR)/appendix-changelog.md \
              $(PAPER_DIR)/appendix-traces.md \
              $(PAPER_DIR)/appendix-prompts.md

TARGET := $(OUT_DIR)/cascade-whitepaper.pdf
DRAFT  := $(OUT_DIR)/cascade-whitepaper-draft.pdf

PANDOC_BASE := pandoc \
    --from=markdown+smart+footnotes+pipe_tables+inline_code_attributes \
    --to=latex \
    --template=$(TEMPLATE) \
    --metadata-file=$(METADATA) \
    --bibliography=$(BIB) \
    --filter=pandoc-crossref \
    --citeproc \
    -M crossrefYaml=$(BUILD_DIR)filters/crossref-meta.yaml \
    --number-sections \
    --pdf-engine=latexmk \
    --pdf-engine-opt=-xelatex \
    --pdf-engine-opt=-interaction=nonstopmode \
    --resource-path=$(BUILD_DIR)figures

.PHONY: pdf draft clean clean-force wordcount check-deps clean-backup

pdf: check-deps $(TARGET)

$(TARGET): $(SOURCES) $(APPENDICES) $(METADATA) $(TEMPLATE) $(BIB)
	@mkdir -p $(OUT_DIR)
	$(PANDOC_BASE) $(SOURCES) $(APPENDICES) -o $@
	@echo "✅ PDF generated: $@"

draft: check-deps
	@mkdir -p $(OUT_DIR)
	$(PANDOC_BASE) -V draft=true \
	    -V watermark="DRAFT — $(shell date +%Y-%m-%d)" \
	    $(SOURCES) $(APPENDICES) -o $(DRAFT)
	@echo "📝 Draft PDF generated: $(DRAFT)"

wordcount:
	@cat $(SOURCES) | wc -w | xargs -I{} echo "Main body: {} words"
	@cat $(APPENDICES) | wc -w | xargs -I{} echo "Appendices: {} words"

clean:
	@echo "This will remove $(OUT_DIR)/, proceed? [y/N]"
	@read ans && [ "$$ans" = "y" ] && rm -rf $(OUT_DIR) || echo "Cancelled."

clean-force:
	rm -rf $(OUT_DIR)

clean-backup:
	rm -rf $(BUILD_DIR).pre_patch_backup

check-deps:
	@command -v pandoc >/dev/null 2>&1 || { echo "❌ pandoc not found"; exit 1; }
	@command -v pandoc-crossref >/dev/null 2>&1 || { echo "❌ pandoc-crossref not found"; exit 1; }
	@command -v latexmk >/dev/null 2>&1 || { echo "❌ latexmk not found"; exit 1; }
```

### Step 2: Write arxiv-clean.tex template

Standard arXiv preprint template: `article` class, `amsmath`, `hyperref`, `cleveref`, `textcomp`, `upquote`, Computer Modern font, pandoc template variables.

### Step 3: Write registry.yaml

```yaml
# Journal Template Registry
# To switch templates: edit Makefile TEMPLATE variable
templates:
  arxiv-clean:
    status: bundled
    file: arxiv-clean.tex
    description: "Standard arXiv preprint (article class, single column)"
  cpc-elsarticle:
    status: community
    download: "https://www.elsevier.com/researcher/author/policies-and-guidelines/latex-instructions"
    class: "elsarticle"
    bst: "elsarticle-num.bst"
    notes: "Download elsarticle.cls, use \\documentclass[preprint,12pt]{elsarticle}"
  jhep:
    status: community
    download: "https://jhep.sissa.it/"
    class: "article + jheppub.sty"
    bst: "JHEP.bst"
    notes: "Download jheppub.sty from SISSA, single column"
  epjc:
    status: community
    download: "https://www.springer.com/journal/10052/submission-guidelines"
    class: "svjour3"
    bst: "spphys.bst"
    notes: "\\documentclass[epjc3]{svjour3}, needs mathptmx"
  revtex-prl:
    status: community
    download: "https://journals.aps.org/revtex"
    class: "revtex4-2"
    bst: "apsrev4-2.bst"
    notes: "\\documentclass[prl,twocolumn]{revtex4-2}, double column"
  scipost:
    status: community
    download: "https://scipost.org/SciPostPhys/authoring"
    class: "SciPost"
    notes: "Open-source template, clean structure"
```

### Step 4: Write crossref-meta.yaml

```yaml
figureTitle: "Figure"
tableTitle: "Table"
figPrefix: "Fig."
tblPrefix: "Tab."
secPrefix: "Sec."
eqnPrefix: "Eq."
chaptersDepth: 0
numberSections: true
sectionsDepth: 3
autoSectionLabels: true
```

### Step 5: Write references.bib (starter)

```bibtex
% Cascade references — add entries as needed
@misc{cascade2026,
  author = {},
  title = {Cascade: An HPC-Native Multi-Agent Framework for High Energy Physics},
  year = {2026},
  note = {In preparation}
}
```

### Step 6: Write README.md

Build instructions for local Mac and lxplus. Covers:
- `brew install pandoc pandoc-crossref` (Mac)
- `wget` binary download to `~/.local/bin` (lxplus) — **Note: cannot be installed via pip into .venv**
- CVMFS TeXLive path
- `make pdf` / `make draft` / `make wordcount`
- **[Y4] Environment Isolation (lxplus):** Document the 3 potential strategies (A/B/C) with strong recommendation for Option C.
  - Option C: Cascade CLI in `.venv`, independent `pandoc` in `~/.local/bin`, TeXLive from CVMFS. When interacting with CMSSW/ROOT, Cascade isolates it by calling `cmsenv` inside subprocesses.

### Step 7: Verify Makefile syntax

Run: `make -n -f /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/_build/Makefile check-deps 2>&1 | head -5`
Expected: Shows the `command -v pandoc` check commands (dry-run)

---

## Task 5: End-to-End Scaffold Test

**Files:**
- Create (via `/cas-texwriter init` logic): All `docs/paper/0[1-7]*.md` + appendix files

### Step 1: Generate paper skeleton files

For each chapter defined in `00-metadata.yaml`, create the corresponding `.md` file with:
- Chapter heading (from `required_headings` if defined, otherwise from `chapters.title`)
- PILLAR anchors in chapters 03 and 04
- `<!-- TODO: 填写核心命题句 -->` placeholders
- Empty section bodies

Example `03-architecture.md`:
```markdown
## 3. System Architecture and Infrastructure

<!-- PILLAR:HPC-Native :: BEGIN -->
<!-- TODO: 填写核心命题句 — HPC-Native 生态位的一句话命题 -->

<!-- PILLAR:HPC-Native :: END -->

### 3.1 The 8-Layer Abstraction Architecture

### 3.2 Pipeline Orchestration on HPC Clusters

### 3.3 Universal ModelClient Layer

<!-- PILLAR:Universal-API :: BEGIN -->
<!-- TODO: 填写核心命题句 — Universal-API 生态位的一句话命题 -->

<!-- PILLAR:Universal-API :: END -->
```

### Step 2: Generate appendix files

`appendix-changelog.md`:
```markdown
# Appendix A: Changelog

<!-- Managed by /cas-texwriter — append-only -->

## v0.3.0 (2026-04-03)

<!-- Phases will be appended here by cas-texwriter -->
```

`appendix-traces.md`:
```markdown
# Appendix B: Agent Execution Traces

<!-- Human-maintained — cas-texwriter will NOT modify this file -->
```

`appendix-prompts.md`:
```markdown
# Appendix C: Example Prompts and Interactions

<!-- Human-maintained — cas-texwriter will NOT modify this file -->
```

### Step 3: Set scaffold_created flag

Update `00-metadata.yaml`: `scaffold_created: false` → `scaffold_created: true`

### Step 4: Verify all files exist

Run: `find /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper -name "*.md" -o -name "*.yaml" | sort`
Expected: Lists all 11 `.md` files + 1 `.yaml` metadata + `_digests/` dir

### Step 5: Verify PILLAR anchors in chapter 03

Run: `grep -n "PILLAR" /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/03-architecture.md`
Expected: Shows `PILLAR:HPC-Native :: BEGIN`, `PILLAR:HPC-Native :: END`, `PILLAR:Universal-API :: BEGIN`, `PILLAR:Universal-API :: END`

### Step 6: Verify PILLAR anchors in chapter 04

Run: `grep -n "PILLAR" /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/04-agent-tools.md`
Expected: Shows `PILLAR:Combine-ROOT :: BEGIN/END`, `PILLAR:Inversion :: BEGIN/END`

### Step 7: Verify build pipeline (dry-run)

Run: `cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/_build && make -n pdf 2>&1 | head -10`
Expected: Shows the pandoc command with correct flag order (crossref before citeproc)

### Step 8: Commit scaffold

```bash
cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade
git add docs/paper/
git commit -m "feat(paper): initialize docs/paper/ scaffold with PILLAR anchors and build pipeline

- 7 chapter files + 3 appendices with heading structure
- 00-metadata.yaml with structure_protection and markdown_spec
- _build/ with Makefile, arxiv-clean template, and pandoc-crossref config
- 4 PILLAR anchor pairs in chapters 03 (HPC-Native, Universal-API) and 04 (Combine-ROOT, Inversion)
- Heading Registry locked: ## and ### fixed, #### allowed with human approval

Generated by /cas-texwriter init"
```

---

## Execution Notes

- **Do NOT modify any files in `_build/` during normal cas-texwriter operation** — build artifacts are human-maintained
- **Do NOT auto-commit** — all changes in docs/paper/ should be reviewed before committing
- **PILLAR thesis sentences** must be hand-written by the human author after scaffold generation
- **`.pillar_baselines`** will be auto-generated from the `.md` files after the human writes the thesis sentences
