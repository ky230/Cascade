# cas-texwriter Native TeX Refactoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor the `cas-texwriter` workflow and `docs/paper` architecture to abandon Markdown+Pandoc in favor of native `.tex` files, producing a simplified v0.0.1 LaTeX skeleton.

**Architecture:** Remove the fragile 8-step Markdown patch workflow. Replace `00-metadata.yaml` with a native `main.tex` structure containing the specified Title, Authors, Abstract, and Image insertion. Separate chapters into pure `.tex` sub-files, managed by a simple `latexmk` build pipeline.

**Tech Stack:** Native LaTeX, latexmk, Agent Workflow definitions.

---

### Task 1: Initialize Gitignore Rules

**Step 1: Write .gitignore for paper build artifacts**

Run:
```bash
cat << 'EOF' > /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/.gitignore
*
!*.tex
!Makefile
!figures/
!figures/*
EOF
```
Expected: `.gitignore` protects everything except source `tex` files, `Makefile`, and `figures`. PDF will be explicitly allowed in the root or main gitignore if requested, but for `docs/paper/` we exclude compilation trash.

**Step 2: Add exception for the final PDF in the main `.gitignore` (if not already present)**

Run:
```bash
echo "!docs/cascade-whitepaper.pdf" >> /Users/ky230/Desktop/Private/Workspace/Git/Cascade/.gitignore
```

### Task 2: Rebuild Native TeX Structure and Content

**Files:**
- Create: `/Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/main.tex`
- Create: `/Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/01-introduction.tex` ... to `07-conclusion.tex`
- Create: `/Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/appendix-changelog.tex`

**Step 1: Scaffold empty chapter `.tex` files**

Create the chapter files with basic sections:
```bash
mkdir -p /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper
echo "\section{Introduction}" > /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/01-introduction.tex
echo "\section{Related Work and Distinctive Positioning}" > /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/02-related-work.tex
echo "\section{System Architecture and Infrastructure}" > /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/03-architecture.tex
echo "\section{Agent Coordination and Tool Constraining}" > /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/04-agent-tools.tex
echo "\section{Proof-of-Concept: A CMS Analysis Workflow}" > /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/05-proof-of-concept.tex
echo "\section{Evolution Roadmap and Developer Changelog}" > /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/06-evolution.tex
echo "\section{Conclusion}" > /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/07-conclusion.tex
```

**Step 2: Create initial changelog file**

```bash
cat << 'EOF' > /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/appendix-changelog.tex
\section*{Appendix A: Changelog}
\addcontentsline{toc}{section}{Appendix A: Changelog}

\subsection*{v0.0.1 (init version)}
Initial LaTeX skeleton refactored from Markdown.
EOF
```

**Step 3: Auto-generate `main.tex`**

Write minimal `main.tex` with requested Title, Abstract, Author metadata, and include the cascade_cli image:
```bash
cat << 'EOF' > /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/main.tex
\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{authblk}

\title{Cascade: A Python-based agentic CLI for HPC clusters}
\author[1,2]{Leyan Li}
\affil[1]{School of Physics and State Key Lab of Nuclear Physics and Technology, Peking University}
\affil[2]{Center for High Energy Physics, Peking University}
\date{\vspace{-5ex}} % Remove date

\begin{document}

\maketitle

\begin{abstract}
A Python-based agentic CLI for HPC clusters, built on modern harness engineering patterns for HEP.
\end{abstract}

% Insert front matter image
\begin{figure}[htbp]
    \centering
    % Ensure this path resolves correctly relative to Makefile execution
    \includegraphics[width=0.8\textwidth]{figures/cascade_cli.jpg}
    \caption{Overview of the Cascade CLI.}
    \label{fig:cascade_cli}
\end{figure}

\input{01-introduction.tex}
\input{02-related-work.tex}
\input{03-architecture.tex}
\input{04-agent-tools.tex}
\input{05-proof-of-concept.tex}
\input{06-evolution.tex}
\input{07-conclusion.tex}

\newpage
\input{appendix-changelog.tex}

\end{document}
EOF
```

### Task 3: Create Native LaTeX Makefile

**Step 1: Generate purely `latexmk`-based `Makefile`**

Run:
```bash
cat << 'EOF' > /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper/Makefile
PAPER_DIR := .
TARGET    := cascade-whitepaper.pdf

.PHONY: all clean wordcount

all: $(TARGET)

$(TARGET): main.tex
	latexmk -pdf -xelatex -interaction=nonstopmode main.tex
	# Copy target to docs root to obey the gitignore exception "!docs/cascade-whitepaper.pdf"
	cp main.pdf ../$(TARGET)

clean:
	latexmk -c
	rm -f main.pdf

wordcount:
	texcount -inc -total main.tex
EOF
```

### Task 4: Refactor `cas-texwriter` Agent Workflow

**Files:**
- Rewrite: `~/.gemini/antigravity/global_workflows/cas-texwriter.md`
- Remove: `~/.gemini/antigravity/global_workflows/cas-texwriter/` reference files

**Step 1: Destroy old complex dependencies**

Run: `rm -rf ~/.gemini/antigravity/global_workflows/cas-texwriter/`
Expected: Folder and old schema/examples files removed.

**Step 2: Rewrite the workflow descriptor**

Write simplified definition to `~/.gemini/antigravity/global_workflows/cas-texwriter.md`:
```markdown
---
description: cas-texwriter — LaTeX Draft Generator & Digest Extractor
---

# cas-texwriter

## 概述

The `cas-texwriter` skill has been radically simplified. It no longer attempts to parse MD anchors, run Pandoc, or automatically inject changes into `.tex` files due to physical rendering instability.

**职责 (Duties):**
1. 读取 `docs/walkthrough.md` 和 `docs/plans/` 的记录。
2. 提炼核心架构变动和执行总结 (Digest).
3. 按照学术语言风格，输出原生的 **LaTeX 代码片段草稿 (Code Snippets)**.
4. （由人类工程师手动复制、贴入 `docs/paper/*.tex` 原文件，并处理精细排版）。

## 规则限制
- **不可自动修改** `docs/paper/*.tex` 源文件。Agent 在无 Git Diff 保护的环境下禁止执行盲写。
- 仅通过控制台输出提纯好的学术描述与 TeX 宏代码。
- 对于 Changelog，只需提取 `walkthrough.md` 的版本日志转换成标准的 `% \subsection*{vX.Y.Z}` 结构交给人类。
```

### Task 5: Compile initial v0.0.1 PDF Skeleton

**Step 1: Run compilation to verify setup**

Run: `cd /Users/ky230/Desktop/Private/Workspace/Git/Cascade/docs/paper && make all`
Expected: `latexmk` runs successfully and copies `main.pdf` to `../cascade-whitepaper.pdf`.
