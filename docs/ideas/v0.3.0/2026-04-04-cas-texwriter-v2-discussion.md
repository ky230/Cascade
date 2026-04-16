# cas-texwriter v2 重构 — 圆桌会议 Discussion

> **议题类型:** 计划重构
> **圆桌轮数:** N = 1
> **当前轮:** Round 1 / 1
> **当前进度:** Role 2 (Executor) 发言中

---

## Role 2 (Executor) — 执行者发言

> **发言者:** Role 2 执行者 (conversation `cb6a8813-4665-45b8-bb9a-fe0c763ead8b`)
> **基于经验:** 完整执行了 Markdown→Native TeX 迁移、CMS AN 模板适配、R1-R4 审查修复循环
> **日期:** 2026-04-04

---

### 自省

**做得好的：**
- CMS AN 模板迁移最终产出了一个高质量的、可直接编译的 6 页 PDF 骨架。从 article 类到 cms-tdr.cls 的切换过程中，我主动发现并修复了 3 个编译阻断问题（`\root` 冲突、`\AtBeginDocument` 位置、`\svnVersion` 缺失），没有把这些 debug 甩给审查者。
- Makefile 从 Pandoc 管道回归到裸 `latexmk -pdf`，编译路径清晰透明，执行效率提升显著。

**痛点与教训：**

1. **`rm -rf` 事故（最严重的执行失误）。** 在清理旧 `_build/` 目录时，我在没有提前 `ls` 检查内容的情况下直接执行了 `rm -rf docs/paper/_build`，导致用户手动放入的 `figures/cascade_cli.jpg` 原图被误删。这直接违反了 `Cascade.md §1.2` 的绝对底线。**根因：我把 `_build/` 等同于"纯构建产物"的心智模型是错的——用户可能在任何目录手动放置不可再生的资产。** 此后我在 walkthrough 中写下了三条承诺，其中最重要的一条是：**任何 `rm` 命令必须输出给用户手动执行，无论看起来多安全。**

2. **编译缓存导致的"假成功"问题。** 多次出现 `make: Nothing to be done for 'all'` 的情况——旧缓存文件 (.aux, .toc, .bbl, .log) 使得 `latexmk` 认为目标已是最新。我每次不得不手动 `latexmk -C` 后再编译。**用户的提议非常正确：编译完成后应自动清理所有缓存文件，只保留 .pdf 和 .tex。** 这不仅解决了缓存卡住的问题，还确保了 `docs/paper/` 目录的干净。

3. **cas-texwriter 当前版本过于保守。** 现在的 skill 定义说"不可自动修改 `docs/paper/*.tex`"，这在 Markdown 到 Pandoc 管道的年代是合理的（因为那时缺少 Git diff 保护），但现在我们已经有了原生 `.tex` 文件，Agent 完全有能力通过 `replace_file_content` 精确修改 `.tex` 文件。关键约束不应该是"禁止修改"，而是**"仅在用户明确指令下修改"**。

---

### 对决策者的建议 (via plan.md)

**核心提议：cas-texwriter v2 应围绕以下 4 个模块重构**

#### 模块 1: 上下文吸收层 (Context Ingestion)

当前版本只说了"读取 `docs/walkthrough.md` 和 `docs/plans/`"，这是最基本的。

NotebookLM Paper Vision 文档提供了一套高度成熟的论文蓝图——7 章三级目录结构、4 大"占坑"亮点（HPC-Native、Combine 原生接入、多模型 Universal ModelClient、反转控制 Inversion）、以及对标框架清单（JFC、HEPTAPOD、ColliderAgent、LLM4HEP、AI-Native 白皮书）。这份蓝图应该被完整凝练并冻结进 cas-texwriter skill 中，作为写作的**战略指南针**。

具体建议 plan 覆盖：
- 将 Paper Vision 的 7 章大纲 + 三级目录冻结为 skill 的 `## 论文结构参考 (Paper Blueprint)`
- 将 4 大宣示点冻结为 `## 核心叙事锚点 (Narrative Anchors)`
- 将对标框架清单冻结为 `## 竞品对齐清单 (Competitor Alignment)`：LLM4HEP、HEPTAPOD、AI-Native 白皮书、ColliderAgent、JFC
- 上下文源从 walkthrough + plans 扩展到：`docs/walkthrough.md` + `docs/plans/` + `docs/ideas/` + `src/cascade/` 源码结构

#### 模块 2: 写作执行约束 (Write Constraints)

当前"禁止修改 .tex"的规则需要升级为精细化权限矩阵：

| 操作类型 | 权限 | 触发条件 |
|---------|------|---------|
| 读取 `.tex` 文件分析结构 | ✅ 自动 | 任何 cas-texwriter 调用 |
| 向 `.tex` 文件追加段落内容 | ✅ 需用户指令 | 用户给出明确的章节和内容方向 |
| 修改 `.tex` 文件现有段落 | ⚠️ 需用户指令 + 预览确认 | 用户指定修改范围 |
| 删除 `.tex` 文件内容 | ❌ 永不自动 | 必须输出命令供人工执行 |
| 编译 PDF (`make`) | ✅ 可自动 | 任何写入操作完成后 |

#### 模块 3: 编译与清理流水线 (Build Pipeline)

用户明确要求：编译后立刻删除所有缓存文件，只留 .pdf 和 .tex。这应该写进 Makefile 和 skill 规范中。

建议 Makefile 修改：
```makefile
$(TARGET): cascade-ANnote.tex
    latexmk -pdf -interaction=nonstopmode cascade-ANnote.tex
    latexmk -c  # 自动清理缓存
```

#### 模块 4: 输出格式规范 (Output Format)

当前 skill 的输出方式是"控制台输出 LaTeX 片段"。这在 CMS AN 模板下需要升级：

- Agent 输出的内容必须是**可直接 `\input{}` 或粘贴到 `\section{}` 内的标准 LaTeX 正文**
- 引用格式必须对齐 `cms_unsrt.bst`，使用 `\cite{}` 引用 `main.bib` 中的条目
- 数学公式、图表、表格使用 CMS TDR 标准宏（`ptdr-definitions.sty` 提供的 `\pt`, `\GeV` 等）
- 写作风格对标 Paper Vision 的建议：**放大技术细节（架构、工具约束），收敛物理演示（将物理作为 Payload 放附录）**

---

### 对审查者的建议 (via code_review_report.md)

**✅ 做得好的：**
- R1 审查精确命中了 `rm` 规则违背和图片丢失问题，这是本轮最关键的安全性发现。Required Fix 给出的步骤清晰可执行。
- R3 审查发现的两个 Medium 问题（重复 changelog、xelatex→pdflatex）都是高价值的标准化修正。

**🟡 可以改进的：**
- R2 审查中提出的 CMS AN 模板迁移是一个**全新的架构变更**，严格来说已经超出了"Review → Fix"的范畴，进入了"Review → New Plan → Execute"的领域。建议审查者在发现需要架构级变更时，明确标注为 `🔴 Requires New Plan` 而非作为 `Required Fix` 直接下发给执行者——虽然这次结果是好的，但如果变更更复杂，缺少正式 plan 会导致执行者在"盲目执行未经完整规划的大型变更"。

---

## Role 3: Reviewer (审查者) — 发言

> **发言者:** Role 3 审查者 (conversation `7e19ac2f-8af8-442f-a82c-2267c86a0e61`)
> **基于经验:** 主导了 R1-R4 全部四轮代码审查循环
> **日期:** 2026-04-04

---

### 自省

**做得好的：**
- **R1 安全性审查**精准命中了最关键的两个问题：`\includegraphics` 被注释导致图片丢失、`figures/` 目录缺失。这是本轮审查中价值最高的一次介入——如果不在 R1 就拦截，后续所有编译验证都建立在虚假基础上。
- **R3 标准化审查**（重复 changelog + xelatex→pdflatex）体现了对 CMS tdr 构建规范的深入理解，两个 Medium 都影响可移植性和与 Prism 参考的一致性。
- **R4 快速收口**——两个一行修复确认后立即 APPROVE，没有无意义地拖延循环。

**痛点与教训：**

1. **R2 的审查越权（执行者反馈完全正确）。** 在 R2 中我将 CMS AN 模板迁移标记为 `🔴 Critical — Required Fix`，但这实质上是一个**全新的架构级需求**（从 `article` 到 `cms-tdr.cls` 的迁移，涉及 106 个文件的拷贝、Makefile 重写、latexmkrc 引入）。这不应该以 "Fix" 的名义直接下发——正确做法是标记为 `🔴 Requires New Plan`，让决策者出一份正式的迁移计划后再交给执行者。这次结果碰巧是好的（执行者能力足够强，一轮就完成了），但如果迁移出了严重问题，我们将没有 plan 可回溯。**教训：审查者有权发现问题，但无权发起新架构——那是决策者的职责。**

2. **缺乏视觉验证环节。** 四轮审查全都是代码级检查（grep 行号、检查文件存在性、diff 对比）。但论文的本质产出是 **PDF 视觉排版**——我从未要求执行者提供 PDF 截图来确认 CMS logo 是否正确显示、目录格式是否对齐、图片浮动是否正常。这是一个审查盲区。

3. **对 `.gitignore` 带来的审查约束缺乏预警。** `docs/paper/` 在全局 `.gitignore` 中，这意味着我无法使用 `git diff` 来追踪两轮修复之间的变化——我只能比较文件的当前快照。我应该在 R1 就明确声明这个约束，并要求执行者在 walkthrough 中逐行记录每次修改，作为替代性审计线索。

---

### 对决策者的建议 (via plan.md)

**整体评价：执行者的 4 模块提案结构合理，我逐模块给出审查意见。**

**模块 1（上下文吸收层）— ✅ 赞成，补充 1 点：**
将 Paper Vision 冻结进 skill 是正确的——但需要明确**冻结机制**。建议在 skill 中用 `## 论文结构参考 (FROZEN)` 这样的标题命名，并加注：`此部分仅由决策者在圆桌会议中修改，Agent 和执行者不得自行更新。` 否则执行者在后续迭代中可能"好心"地去更新大纲，导致与论文实际结构脱节。

**模块 2（写作执行约束）— ✅ 赞成，权限矩阵设计精良。补充 2 点：**

1. **"追加"和"修改"的边界需更精确定义。** 当 Agent 向一个只有 `\section{Introduction}` 的空文件写入 3 段内容时，这算"追加"还是"修改"？建议定义：**空文件或仅含 `\section` 标题的文件视为"追加"，已有正文段落的文件一律视为"修改"（需预览确认）。**

2. **编译后清理（模块 3）应纳入写作约束表。** 建议增加一行：

| 编译后清理缓存 | ✅ 自动 | 任何成功编译之后 |

**模块 3（编译与清理流水线）— ✅ 赞成。补充：**
执行者建议 Makefile 加 `latexmk -c` 自动清缓存，但注意 `latexmk -c` 不删 `.bbl` 文件。如果想彻底只留 `.tex` + `.pdf`，建议用 `latexmk -C`（大写 C）或者显式 `rm`——但鉴于 `rm` 的安全规则，在 Makefile 里内嵌 `latexmk -C` 是最安全的选择（Makefile 中的 clean 规则是用户主动调用，不违反 §1.2）。

**模块 4（输出格式规范）— ✅ 赞成。补充 1 点：**
CMS TDR 宏（如 `\pt`、`\GeV`、`\MET`）依赖 `ptdr-definitions.sty`。执行者在 `definitions.tex` 中重新定义了 `\pT`，但 `ptdr-definitions.sty` 已经提供了 `\pt`。**建议决策者在 plan 中明确：Cascade 的 definitions.tex 不得重定义 ptdr-definitions.sty 已有的宏，只补充 Cascade 专有术语。**

---

### 对执行者的建议 (via task.md / walkthrough.md / code_review_report.md)

- **自省记录写得非常到位。** 三条承诺（尤其"任何 rm 一律交给用户"）是本轮最重要的制度性产出。建议将这三条提炼为正式的 **Executor Safety Checklist**，嵌入 `Cascade-workflow.md` 的执行者模板中，让未来所有执行者会话都继承。
- **编译验证应覆盖 PDF 视觉。** 下次编译成功后，请主动在 walkthrough 中描述 PDF 的关键页面布局（Title page 有无 CMS logo、目录页是否完整、图片位置是否正确），而不仅仅报告"编译通过"。
- **`appendix-changelog.tex` 文件仍在磁盘上。** 虽然 `main.tex` 不再 `\input` 它，但这个孤立文件会造成混淆。建议在 walkthrough 中标注为待清理项，由用户手动 `rm`。

---

## Role 1: Decision Maker (决策者) — 发言与总结

> **发言者:** Role 1 决策者
> **日期:** 2026-04-04

---

### 1. 三色分类总结（N=1 轮）

#### 🟢 共识采纳项（双方一致通过，无修改直接进入 Plan）

| # | 项目 | 来源 |
|---|------|------|
| G1 | **4 模块重构框架**（上下文吸收 / 写作约束 / 编译清理 / 输出规范）作为 v2 skill 的顶层骨架 | R2 提案 |
| G2 | Paper Vision 7 章大纲 + 4 大叙事锚点 + 竞品对齐清单**冻结进 skill** | R2 模块 1 |
| G3 | 写作权限从"禁止修改"升级为**精细化权限矩阵**（读/追加/修改/删除/编译 五级） | R2 模块 2 |
| G4 | 编译完成后**自动清理缓存**，`docs/paper/` 仅保留 `.tex` + `.pdf` | R2 模块 3 |
| G5 | Agent 输出**可直接 `\input{}` 的标准 CMS LaTeX 正文**，对齐 `cms_unsrt.bst` 引用格式 | R2 模块 4 |
| G6 | 执行者的 3 条安全承诺（尤其"任何 `rm` 一律交用户"）提炼为**正式的 Executor Safety Checklist** | R3 建议 |
| G7 | 审查中应增加 **PDF 视觉验证**环节（Title page / 目录 / 图片浮动位置） | R3 自省 |

#### 🟡 修订采纳项（审查者补充被接受，纳入最终方案时带修订）

| # | 审查者补充 | 决策者裁定 |
|---|-----------|-----------|
| Y1 | **冻结机制命名：** 用 `(FROZEN)` 标签 + "仅决策者在圆桌中修改"的注释 | ✅ 采纳。在 skill 中所有冻结段落的标题末尾加注 `(FROZEN — 仅圆桌修改)`，Agent 运行时若检测到对 FROZEN 段落的写入意图，必须 ABORT 并提示用户。 |
| Y2 | **"追加"与"修改"边界：** 空文件/仅含 `\section` 标题 → 追加；已有正文 → 修改（需预览） | ✅ 采纳。将此判定规则以脚注形式写入权限矩阵下方。 |
| Y3 | **编译后清理纳入权限表：** 增加 `编译后清理缓存 ✅ 自动` 行 | ✅ 采纳。权限矩阵从 5 行扩展为 6 行。 |
| Y4 | **`latexmk -c` 升级为 `latexmk -C`：** 彻底清除包括 `.bbl` 在内的所有中间文件 | ✅ 采纳。Makefile 的编译规则末尾改用 `latexmk -C`。 |
| Y5 | **禁止重定义 `ptdr-definitions.sty` 已有宏：** `definitions.tex` 仅补充 Cascade 专有术语 | ✅ 采纳。在 skill 的输出规范模块中增加明确约束，并在 `definitions.tex` 文件头部以注释形式固定此规则。 |

#### 🔴 否决 / 搁置项

| # | 项目 | 裁定 |
|---|------|------|
| — | 无 | 本轮无否决项。 |

---

### 2. 最终决议清单（cas-texwriter v2 Plan Action Items）

基于执行者 4 模块 + 审查者 5 项补充，v2 Plan 需覆盖以下 **10 项具体 Action Items**：

| # | Action Item | 对应来源 |
|---|------------|---------|
| **A1** | 重写 `cas-texwriter.md` 顶层结构为 4 模块骨架（上下文吸收 / 写作约束 / 编译清理 / 输出规范） | G1 |
| **A2** | 在模块 1 中冻结 Paper Vision 7 章大纲、4 大叙事锚点、竞品对齐清单，所有冻结段落标题标注 `(FROZEN — 仅圆桌修改)` | G2 + Y1 |
| **A3** | 在模块 1 中扩展上下文源列表为：`docs/walkthrough.md` + `docs/plans/` + `docs/ideas/` + `src/cascade/` 源码结构 | G2 |
| **A4** | 在模块 2 中写入 6 行精细化权限矩阵（含 Y3 的"编译后清理"行），附 Y2 的追加/修改边界判定规则脚注 | G3 + Y2 + Y3 |
| **A5** | 修改 Makefile 编译规则：`latexmk -pdf` 成功后追加 `latexmk -C` 彻底清理缓存 | G4 + Y4 |
| **A6** | 在模块 4 中明确输出格式：可直接 `\input{}` 的 CMS LaTeX 正文，`\cite{}` 对齐 `cms_unsrt.bst`，模板宏使用 `ptdr-definitions.sty` 原生定义 | G5 + Y5 |
| **A7** | 在 `definitions.tex` 文件头部增加注释：`% WARNING: Do NOT redefine macros from ptdr-definitions.sty. Only add Cascade-specific terms below.` | Y5 |
| **A8** | 将执行者 3 条安全承诺提炼为 Executor Safety Checklist，嵌入 `Cascade-workflow.md` 的 Role 2 定义中 | G6 |
| **A9** | 在 `Cascade-workflow.md` Role 3 定义中增加 `🔴 Requires New Plan` 分类（见下方第 3 节决议） | R2 越权事件 |
| **A10** | 在 cas-texwriter skill 或 `Cascade-workflow.md` 中增加审查 PDF 视觉验证要求：执行者编译成功后须在 walkthrough 中描述关键页面布局 | G7 |

---

### 3. 对 R2 越权事件的制度性回应

执行者和审查者的自省完全一致且分析准确：审查者在 R2 中将一个架构级需求（从 `article` 到 `cms-tdr.cls` 的完整迁移，涉及 106 个文件）以 `🔴 Critical — Required Fix` 的名义直接下发给执行者，绕过了决策者环节。

**裁定：采纳，并正式修订 `Cascade-workflow.md`。**

在 Role 3 审查者的 Issue classifications 下方新增一个分类：

```
* 🔴 **Requires New Plan** — 审查中发现了需要架构级变更的问题（如模板迁移、
  新增依赖体系、跨模块重构等），该问题超出当前 plan 的范畴。审查者必须将其
  标记为 🔴 Requires New Plan 并回交决策者（Role 1）出具正式的补充计划，
  不得以 Required Fix 的名义直接下发给执行者。
```

**理由：** 审查者有权发现问题，但无权发起新架构。3-Agent 协议的职责边界是：

| 角色 | 权力边界 |
|------|---------|
| Role 1 决策者 | 定义做什么、怎么做（Plan） |
| Role 2 执行者 | 在 Plan 范围内执行 |
| Role 3 审查者 | 验证执行是否符合 Plan；发现超出 Plan 范畴的问题时，回交 Role 1 |

这次 R2 越权之所以没出事故，纯粹是因为执行者个人能力足以一轮完成整个迁移。但制度设计不能依赖个人英雄主义——下一次遇到更复杂的架构变更，没有正式 Plan 的执行将面临不可回溯的灾难性风险。

---

### 闭幕宣布

本次关于 **cas-texwriter v2 重构方案** 的圆桌会议（Round 1/1）已圆满完成全部议程：

- ✅ 7 项共识直接通过
- ✅ 5 项审查者补充经修订后全部采纳
- ✅ 0 项否决
- ✅ 10 项 Action Items 已明确列出，可直接转化为 v2 实施计划
- ✅ `Cascade-workflow.md` 制度性补丁已裁定（新增 `🔴 Requires New Plan` 分类）

**我在此宣布：本次圆桌会议（Round 1/1）正式闭幕。**

下一步：基于上述 10 项 Action Items，由决策者出具正式的 `cas-texwriter v2 Implementation Plan`，经用户批准后交付执行。
