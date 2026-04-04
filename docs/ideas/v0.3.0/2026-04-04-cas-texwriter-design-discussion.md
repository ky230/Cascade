> **议题类型:** 计划重构与技能设计 (Skill Design)
> **圆桌轮数:** N = 2
> **当前轮:** ✅ 圆桌完成
> **当前进度:** Round 1 ✅ → Round 2 ✅ → 三色总结 ✅ (16🟢 / 3🟡 / 0🔴)

---

## 背景：学术论文与工程架构的同步演进（Build-up & Write-up）

随着 Cascade v0.3.0 基础功能的逐渐完善，我们确立了对标 JFC、HEPTAPOD 等前沿高能物理 AI 代理框架的发展路线。为了在基础设施搭建阶段确立“HPC 原生”、“原生 Combine/ROOT 支持”、“Universal API”以及“Inversion 挂起反转防幻觉”这四大核心亮点，我们计划在每个 version 开发结束后，进行一次同步的论文写作迭代。

**核心需求：**
设计一个新的 Antigravity 技能 `cas-texwriter`。该技能以 `docs/plans/` 下的架构规划和 `docs/walkthrough.md` 的最终交付验证为输入，自动将核心架构的演进转化为技术白皮书/论文中的 Methodology 和 Changelog 片段，从而消除“写代码”与“写文章”之间的割裂。

---

## Role 1 (Decision Maker) — 决策者发言

> **发言者:** Role 1 决策者
> **日期:** 2026-04-04 (Round 1)

### 1. 广度与深度的权衡理念 (Vision & Philosophy)
从 NotebookLM 调研的反馈来看，我们的论文并非普通的 CS Software Paper，而是专为 CMS 设计的 **“技术白皮书 (Technical Whitepaper)”**，版式对标 JFC / JHEP 的长文体系。

因此，`cas-texwriter` 这个技能必须极其“高傲”。它绝对不能事无巨细地把 `修复 UI bug`、`重构 xxx 函数` 写进正文。它需要拥有**“学术级别的抽象提取能力”**。
- **正文（Methodology）更新原则：** 只提取改变了系统底层流转机制（如多进程化）、改变了用户交互范式（如 TUI Queue机制）、或显著增强了 HEP Payload 支持（如新的 Tool Wrapper）的改动。
- **附录（Changelog & Traces）更新原则：** 作为“成长日志”忠实记录 Agent 解决复杂依赖演化的路线，以及具体的 Agent 运行长日志追踪。

### 2. 技能的输入/输出 (I/O Constraints)
- **Input (知识源):** 
  - `docs/walkthrough.md` 中对应当前 Version 的 block。
  - 该版本下 `docs/plans/` 目录里的核心架构实施计划（只读，提取技术架构与设计理念）。
- **Output (落地成果):**
  - **初定介质：** 虽然名为 `texwriter`，但我倾向于在这个技能早期，我们让代理生成/维护特定格式的 `.md` 文件（如 `docs/paper/03-architecture.md`、`docs/paper/appendix-changelog.md`），最后通过统一脚本（如 pandoc）转为 LaTeX。这样可以避免 Agent 直接与大段杂乱的 LaTeX 语法做斗争。
  - **核心动作：** 每次调用，它应产生两处更新：（1）在 Changelog 附录追加新版本的 Feature List；（2）在正文对应的模块（如 8-Layer Architecture）进行 Diff 修改，注入新的设计实现。

### 3. 工作流设计建议 (Workflow Steps)
1. **Scope 定位**：代理自动识别当前最新的 Version 号。
2. **Context 吸入**：读取 `walkthrough.md` 提取完成的任务清单，再追溯阅读对应的实施计划（获取 Why 和 How）。
3. **内容提纯与生成**：在内存中形成“学术转化（Academic Translation）”，把诸如 "Phase 8.5.4 Message Queue" 升华为 "Asynchronous Non-blocking Instruction Queuing for Real-time Generation"。
4. **Patch 写入**：将新形成的架构描述准确拼接/替换到论文正文，并更新 Changelog。

### 对执行者的建议 (期望你在后续发言重点考虑的)
1. **关于 LaTeX 与 Markdown 这层胶水**：你认为我们是直接让 `cas-texwriter` 以 `.tex` 为直接操作源好，还是保持一套纯净的 `docs/paper/*.md` 比较稳妥？
2. **上下文过载风险**：每次版本结束，相关的实施计划可能多达六七个文件。你觉得在技术上如何避免 Agent 阅读 plans 时把上下文撑爆？有没有更好的提纯方案？
3. **查重与覆盖问题**：如果是“追加式”，很好办；但涉及到“修改旧章节”，我有点担心 Agent 改着改着把原本的精髓抹掉了（尤其是我们精心构思的前四点宣示亮点）。如何加上护栏？

---

## Role 2 (Executor) — 执行者发言

> **发言者:** Role 2 执行者
> **日期:** 2026-04-04 (Round 1)

### 1. 对决策者三大问题的执行层回应

#### Q1: Markdown vs. LaTeX 中间件交互设计

**结论：坚持 Markdown 中间层，决策者方案正确。**

从工程实操角度，Agent 直接操作 `.tex` 文件存在三个致命风险：
- **Token 浪费**：LaTeX 环境嵌套（`\begin{figure}[htbp]...\end{figure}`）、交叉引用宏（`\cref{}`）、bibtex 条目等在上下文窗口中消耗大量 token 但不贡献语义理解；
- **语法脆弱性**：Agent 生成的 LaTeX 极易出现未闭合环境或特殊字符转义错误，一次错误修改就可能导致整个文档无法编译；
- **Diff 不可读**：`.tex` 文件的 git diff 极度混乱，人类审稿时无法快速判断 Agent 改了什么。

**推荐架构：**

```
docs/paper/
├── 00-metadata.yaml       # title, authors, version mapping
├── 01-introduction.md
├── 03-architecture.md      # 核心技术章: 8-Layer, HPC-Native, etc.
├── 04-agent-tools.md       # Tool Wrappers, Inversion 机制
├── 05-proof-of-concept.md
├── 06-evolution.md
├── appendix-changelog.md   # per-version feature list (追加式)
├── appendix-traces.md      # Agent 执行日志 (追加式)
└── _build/
    ├── template.tex         # 人工维护的 JHEP 模板 (一次性)
    └── Makefile             # pandoc + latexmk pipeline
```

`cas-texwriter` 只操作 `*.md` 文件。LaTeX 转换由 `pandoc --template=template.tex` + 自定义 filter（处理 JHEP 特殊宏）完成。这层胶水是**静态的、人工维护的**，不进入 Agent 视野。

#### Q2: 上下文过载风险 — "先蒸馏、再注入"策略

实测数据：仅 v0.3.0 的 plans 目录已有 **8 个文件、约 170 KB**。按 1 token ≈ 4 字节估算，全量注入约需 **42K tokens**，几乎占满大多数模型的有效工作窗口。v0.2.0 更有 7 个文件 (~35 KB)。两个版本合计读入即崩。

**解决方案：两阶段 Digest 策略**

| 阶段 | 动作 | 输出 |
|------|------|------|
| **Stage 1: Digest 生产**（离线/版本封存时） | 技能在版本 tag 后自动扫描 `docs/plans/vX.Y.Z/*.md`，逐个提取：(1) Phase 编号与名称；(2) 核心架构变更（30 词以内）；(3) 对四大生态位的贡献度标签 | `docs/paper/_digests/vX.Y.Z-digest.yaml` (~2-3 KB) |
| **Stage 2: 精读注入**（写作时） | `cas-texwriter` 先读 digest YAML（极小）→ 判断哪些 Phases 与当前更新的章节强相关 → **仅 cherry-pick 加载 1-2 个全文 plan** | 上下文占用 ≤ 20K tokens |

Digest YAML 格式示例：
```yaml
version: "v0.3.0"
phases:
  - id: "8.5.4"
    name: "Non-Blocking Message Queue"
    abstract: "Async instruction queuing with 3-tier priority, mirroring Claude Code's QueueProcessor"
    pillars: ["HPC-Native"]     # 四大生态位标签
    key_files: ["message_queue.py", "query_guard.py"]
  - id: "8.5.3"
    name: "Input History"
    abstract: "JSONL-persisted terminal history with cross-session recall"
    pillars: []                 # 不涉及核心生态位 → 仅入 Changelog
```

这种设计让真正的"学术提纯"发生在 **digest 生产阶段**，而非写作阶段。写作时 Agent 手里只有精炼过的索引 + 少量全文。

#### Q3: 追加式 vs. 修改式更新的护栏 — 四大生态位锁定

这是最关键的风险。Agent 在修改 `03-architecture.md` 时，极可能把精心构建的 "HPC-Native 算力下沉" 叙事替换为某个 Phase 的细节描述，导致立意塌方。

**护栏方案：Pillar Anchors（锚点保护）**

在正文 Markdown 中嵌入不可删除的元注释锚点：

```markdown
<!-- PILLAR:HPC-Native :: BEGIN -->
### 3.2 Pipeline Orchestration on HPC Clusters
Cascade is the first agentic framework natively designed for HPC clusters...
<!-- PILLAR:HPC-Native :: END -->
```

**规则链：**
1. `cas-texwriter` 的 System Prompt 中硬编码：`PILLAR` 锚点之间的段落**只能追加或细化，不得删除或替换核心命题句**（即锚点后的第一段概括性陈述）。
2. 每次修改完成后，技能执行一次自动验证：扫描输出文件，确认四个 `PILLAR:*` 锚点完整存在且核心命题句未变。不通过则回滚并报错。
3. 追加式更新（`appendix-changelog.md`）无需锚点保护，直接 append-only，按版本号分 section。

### 2. 两套底层工作流方案

---

#### 方案 A：Digest-First Patch（先蒸馏后补丁）

```
触发条件: 用户调用 /cas-texwriter 或版本 tag 后自动触发

Step 1: VERSION_DETECT
  └─ 从 docs/walkthrough.md 解析最新完成的 version block

Step 2: DIGEST_GENERATE (if not exists)
  └─ 遍历 docs/plans/{version}/*.md
  └─ 输出 docs/paper/_digests/{version}-digest.yaml

Step 3: WALKTHROUGH_EXTRACT
  └─ 从 walkthrough.md 提取当前 version 的所有 Phase 摘要
  └─ 结合 digest.yaml 的 pillars 标签，分类为：
       [A] Methodology-worthy (涉及核心生态位)
       [B] Changelog-only (不涉及)

Step 4: SELECTIVE_DEEPREAD (仅对 [A] 类)
  └─ Cherry-pick 加载 1-2 个 plan 全文 → 提取 Why + How

Step 5: ACADEMIC_TRANSLATE
  └─ 将 [A] 类改动转化为学术语言，patch 到正文 *.md
  └─ 将 [B] 类改动格式化为 bullet list，append 到 appendix-changelog.md

Step 6: PILLAR_VERIFY
  └─ 扫描所有正文 *.md，确认 4 个 PILLAR 锚点完整
  └─ 失败 → 回滚 + 输出 diff + 报错
```

**优势：**
- 上下文可控（≤ 20K tokens 工作窗口），可在任何模型上运行
- Digest YAML 是可人工审校的中间产物，可 git 追踪
- 六步流水线中 Step 2 可离线预生成，降低在线耗时

**劣势：**
- Digest 生产本身也是一次 LLM 调用，存在信息丢失风险
- 两阶段增加了一次 LLM roundtrip 延迟
- 需要维护 digest YAML 的 schema 约定

---

#### 方案 B：Dual-Source Merge（双源直注入）

```
触发条件: 同上

Step 1: VERSION_DETECT (同方案 A)

Step 2: WALKTHROUGH_EXTRACT
  └─ 提取当前 version 完成的 Phase 列表（仅名称 + 一句话摘要）

Step 3: CHAPTER_MATCH
  └─ 将每个 Phase 映射到论文目录的对应章节 (手动维护的映射表):
       "8.5.4 Message Queue" → "03-architecture.md#3.2"
       "8.5.3 Input History" → "appendix-changelog.md"

Step 4: CHAPTER_FOCUSED_WRITE (per matched chapter)
  └─ 仅加载：(1) 目标章节当前全文；(2) walkthrough 中对应 Phase 的详细段落
  └─ 不加载 plan 全文，依赖 walkthrough 的已验证摘要
  └─ Agent 在章节内原地 patch

Step 5: PILLAR_VERIFY (同方案 A Step 6)
```

**优势：**
- 无 Digest 中间层，工作流更简单，调试更直接
- 完全依赖 `walkthrough.md`（已经过人工审校），信息质量最高
- 无需两阶段 LLM 调用，延迟更低

**劣势：**
- `walkthrough.md` 可能不包含足够的 "Why"（设计哲学），只记录了 "What"
- Chapter-Phase 映射表需要**人工维护**，增加了一个容易过时的配置
- 当 walkthrough 某个 Phase 描述过于简略时，Agent 可能无法生成足够深度的学术叙事

---

#### 执行者倾向

**推荐方案 A（Digest-First Patch）**，理由：

1. **上下文安全优先**：在 Cascade 的多模型架构下（GLM/Kimi/MiniMax 等模型上下文窗口差异大），Digest 策略提供了**模型无关**的上下文预算保证。
2. **Plan → Digest 这一步实际上就是 Academic Translation 的前半程**：它强制 Agent 在写入论文之前先进行一次"提纯聚焦"，这与决策者要求的"高傲"策略天然对齐。
3. **版本可追溯性**：`_digests/*.yaml` 文件 git 可追踪，可审查，可回溯。比 walkthrough alone 多了一层"学术视角"的结构化缓存。

但**保留方案 B 作为 fallback**：当 walkthrough 质量足够高且 plan 数量 ≤ 3 个时，可跳过 Digest 阶段直接走方案 B，减少延迟。技能内部通过 `len(plan_files)` 自动选择。

### 3. 对决策者的追问

1. **论文目录锁定时机**：NotebookLM 建议的 7 章 + 3 附录结构，是否在 v0.1-dev 初稿阶段就**完全固定**？还是允许 `cas-texwriter` 在发现新的架构模式时**提议新增 subsection**（需人工批准）？
2. **Changelog 粒度**：附录 A 的 Changelog 是按 Phase 汇总（如 "Phase 8.5.4: Non-Blocking Message Queue"），还是按 commit 粒度？决策者提到"不做事无巨细的 commit 罗列"，我理解应以 Phase 为最小粒度。请确认。
3. **首次初始化**：`cas-texwriter` 首次运行时，`docs/paper/*.md` 尚不存在。是否由技能根据 NotebookLM 的目录大纲**自动 scaffold 骨架文件**（含 PILLAR 锚点和 section headers），还是由人工先写好框架？

---

## Role 3 (Reviewer) — 审查者发言

> **发言者:** Role 3 审查者
> **日期:** 2026-04-04 (Round 1)

### 1. 对决策者架构愿景的审查

#### 1.1 "学术级抽象提取" 定位评估

决策者将 `cas-texwriter` 定义为"高傲的"——只提取改变系统底层流转机制或显著增强 HEP Payload 支持的改动。这个定位 **方向正确但边界模糊**。

**具体问题：**

- **"改变底层流转机制" 的判定标准缺失。** 例如：Session History 持久化（v0.3.0 Phase 8.5.3）改变了跨会话状态管理，但它算"底层流转"还是"工程细节"？如果没有明确的 **分类判定规则（Decision Tree）**，不同 Agent 在不同调用中会产生不一致的分类结果。
- **与 NotebookLM 北极星的对齐检验：** NotebookLM 明确指出论文应"放大技术细节（基础设施与架构）"、"收敛物理演示"。决策者的"高傲"策略在收敛侧做得很好（不罗列 commit），但在"放大"侧可能 **矫枉过正**——某些看似不涉及四大生态位的基础设施改进（如 `/clear` 生命周期管理），在 "8-Layer Architecture" 叙事中可能恰恰是 Layer 之间职责分离的证据。建议引入"虽不涉及四大生态位，但作为架构层级分离的论据有学术价值"这一灰色分类。

#### 1.2 四步工作流（Scope → Context → Translate → Patch）遗漏分析

决策者提出的四步流是 **正确的骨架**，但遗漏了两个关键步骤：

| 遗漏步骤 | 应插入位置 | 理由 |
|---------|-----------|------|
| **CONFLICT_DETECT（冲突检测）** | Translate → Patch 之间 | Agent 在"学术翻译"完成后、写入前，必须检查待 patch 的目标段落是否已包含语义相近的内容。否则同一架构特性在不同版本迭代中可能被重复描述。 |
| **HUMAN_GATE（人工审批）** | Patch → 结束之间 | 现有四步全自动执行。但正文修改（非 Changelog 追加）的风险极高，至少应在 patch 生成后、实际写入前插入一次 diff 预览 + 人工确认。 |

### 2. 对执行者两套方案的审查

#### 2.1 方案 A（Digest-First Patch）

**核心风险：Digest Agent 自身幻觉。**

执行者正确识别了"Digest 生产本身也是一次 LLM 调用，存在信息丢失风险"，但低估了风险的严重性。具体场景：

- **幻觉注入：** Digest Agent 处理 `docs/plans/v0.3.0/2026-04-03-infrastructure-rebuild.md`（170 KB 中最大的文件）时，可能因上下文截断而 **错误归类某个 Phase 的 pillars 标签**。例如，把一个与 HPC-Native 无关的 Phase 错标为 `pillars: ["HPC-Native"]`，导致它被送入 Methodology 正文、挤占有限的章节空间。
- **遗漏关键 Phase：** 反过来，Agent 可能将确实重要的 Phase（如 Inversion 机制的扩展）因未理解其与"防幻觉"生态位的关联而标为 `pillars: []`，导致它仅写入 Changelog 而永远不进正文。

**修改要求：**

1. Digest YAML 必须被标记为 **draft 状态**，生产后需经人工审校确认 `pillars` 标签才能流入 Stage 2。可在 YAML 中增加 `status: draft | reviewed` 字段。
2. 每个 Phase 的 `abstract` 应包含额外字段 `confidence: high | medium | low`，若 Agent 对该 Phase 的分类信心不足，标记 `low` 并在 CLI 输出中高亮提醒人工复核。

#### 2.2 方案 B（Dual-Source Merge）作为 Fallback

执行者将方案 B 定位为"当 `len(plan_files) ≤ 3` 时自动降级"，这个降级策略 **逻辑合理但阈值过于简单**。

**问题：**

- 文件数量不等于上下文复杂度。3 个文件如果每个 60 KB = 180 KB 照样崩；7 个文件如果每个 2 KB = 14 KB 完全可控。应以 **total token count 而非 file count** 作为切换条件。
- 方案 B 依赖 `walkthrough.md` 的"已验证摘要"，但 walkthrough 是面向工程交付验证的文档，其语言是"做了什么"而非"为什么这样设计"。**在缺少 plan 全文的情况下，Agent 几乎无法生成 NotebookLM 要求的"放大技术细节"级学术叙事。** 方案 B 只适合更新 Changelog 附录，不应用于修改正文。

**修改要求：**

1. 将降级判断从 `len(plan_files) ≤ 3` 改为 `total_plan_tokens ≤ 15K`。
2. 方案 B 的适用范围收缩为 **仅 Changelog 追加**，不允许触碰正文 `*.md` 的 PILLAR 区域。

#### 2.3 Pillar Anchors 护栏方案

四个锚点保护是 **必要但不充分** 的。

**盲区分析：**

| 风险场景 | 锚点是否覆盖 | 具体威胁 |
|---------|------------|---------|
| Agent 删除锚点内核心命题句 | ✅ 已覆盖 | PILLAR_VERIFY 会检测 |
| Agent 在锚点内追加错误信息 | ⚠️ 部分覆盖 | 只保护了命题句不被删除，但追加的新段落可能与命题句矛盾 |
| **Agent 在锚点外部改坏相邻段落** | ❌ **未覆盖** | 例如 `<!-- PILLAR:HPC-Native :: END -->` 之后的下一个 subsection（如 3.3 Universal ModelClient），Agent 可能在更新 3.3 时误删了与 3.2 的过渡段落，破坏整体叙事连贯性 |
| **Agent 在两个锚点之间的"无人区"插入不当内容** | ❌ **未覆盖** | 例如在 PILLAR:HPC-Native END 和 PILLAR:Universal-API BEGIN 之间的过渡段落被替换为与上下文不连贯的新内容 |

**修改要求：**

1. 每个正文 `.md` 文件的 **完整结构也应受保护**。建议在文件头部增加 `<!-- STRUCTURE_HASH: sha256:xxxx -->` 元注释，记录所有 `##` / `###` heading 的有序列表摘要。PILLAR_VERIFY 阶段同时校验：(a) 四个锚点完整；(b) section heading 的拓扑序列未被篡改（允许新增 subsection，但禁止删除或重排已有 heading）。
2. 对锚点内部的追加内容，增加一条规则：**新追加的段落必须显式引用（`[ref: Phase X.Y.Z]`）其来源 Phase**，便于人工回溯和后续 clean-up。

### 3. 独立审查视角

#### 3.1 Markdown 子集限定

`docs/paper/*.md` 必须严格限定 Markdown 子集，否则 pandoc 转换阶段将成为 bug 温床。

**推荐规范：**

| 元素 | 是否允许 | 理由 |
|------|---------|------|
| Heading (`#` - `####`) | ✅ | 基本结构 |
| 粗体/斜体 | ✅ | 基本格式 |
| 有序/无序列表 | ✅ | Changelog 需要 |
| 表格（GFM 管道表） | ✅ | 架构对比、性能数据不可或缺 |
| 行内数学 `$...$` | ✅ | HEP 论文不可能没有数学公式（如截面 $\sigma$、luminosity $\mathcal{L}$） |
| 块级数学 `$$...$$` | ✅ 但限制使用 | 仅在 Proof-of-Concept 章节允许，Methodology 中应避免大段推导 |
| 代码块 ` ```...``` ` | ✅ | 展示配置片段、YAML schema |
| Mermaid 图表 | ❌ **禁止** | Mermaid 无法被 pandoc 原生处理，需要额外的 filter（mermaid-filter 或 mermaid.ink），增加构建链脆弱性。架构图应以预渲染的 PNG/SVG 嵌入 |
| 内链 `[text](file:///...)` | ❌ **禁止** | 仅限论文内部交叉引用（pandoc crossref 语法 `[@sec:xxx]`）|
| HTML 注释 `<!-- -->` | ✅ | PILLAR 锚点需要 |
| 原生 HTML 标签 | ❌ **禁止** | pandoc 转换不可控 |

建议在 `docs/paper/README.md` 或 `00-metadata.yaml` 中明文记录此规范，作为 `cas-texwriter` System Prompt 的一部分注入。

#### 3.2 "自动 Scaffold 骨架文件"应作为显式 Sub-command

执行者提到首次运行时自动生成 `docs/paper/*.md` 骨架。**强烈反对将其作为隐式首次运行行为。**

理由：
1. **骨架文件的质量直接决定论文的上层建筑。** PILLAR 锚点位置、章节粒度、核心命题句——这些都必须经过人工精心构思，不能交给 Agent 一次性生成。NotebookLM 给出的目录大纲是"指导"而非"规范"，人工可能根据实际 v0.1-dev 的完成度做取舍。
2. **单一职责原则。** `cas-texwriter` 的核心职能是"翻译与更新"，不是"创建与初始化"。将 scaffold 混入会增加技能的复杂度和测试负担。

**建议：**
- 新增独立子命令 `/cas-texwriter init`，根据 NotebookLM 目录大纲 + `00-metadata.yaml` 中的章节配置生成骨架文件（含 PILLAR 锚点 + heading + 空白命题句占位符）。
- 标记为 **一次性操作**，执行后在 metadata 中写入 `scaffold_created: true`，后续调用 `init` 时报错而非覆盖。
- 骨架生成后，必须经 **人工审校并 commit** 后，才能运行常规的 `cas-texwriter` 更新流程。

#### 3.3 人工审批环节应插入的步骤

目前两个方案的人工干预点严重不足。PILLAR_VERIFY 是 **事后自动校验**，不是 **事前人工审批**。

**推荐的 Human Gate 插入点：**

```
方案 A 增强版：

Step 2: DIGEST_GENERATE → Step 2.5: 🧑 DIGEST_REVIEW (人工确认 pillars 标签)
Step 5: ACADEMIC_TRANSLATE → Step 5.5: 🧑 PATCH_PREVIEW (输出 diff，人工确认)
Step 6: PILLAR_VERIFY (自动，失败则回滚)

方案 B 增强版：

Step 4: CHAPTER_FOCUSED_WRITE → Step 4.5: 🧑 PATCH_PREVIEW (输出 diff，人工确认)
Step 5: PILLAR_VERIFY (自动，失败则回滚)
```

关键原则：**凡是修改正文（非追加 Changelog）的步骤，在实际写入前必须有人工 diff 审批。** Changelog 追加因为是 append-only 且风险低，可仅靠自动验证。

### 4. 三色评价

#### 对决策者（Role 1）

| 评价 | 条目 | 说明 |
|------|------|------|
| 🟢 | Markdown 中间层决策 | 完全正确。避免 Agent 直接操作 LaTeX 是工程实操中的最优解 |
| 🟢 | "高傲"策略的宏观方向 | 与 NotebookLM "收敛物理演示、放大基础设施"的北极星完全一致 |
| 🟡 | 四步工作流 | 骨架正确但缺少 CONFLICT_DETECT 和 HUMAN_GATE 两个关键步骤 |
| 🟡 | "学术级抽象" 的分类边界 | 仅用"是否涉及四大生态位"做二分法过于粗糙，需要引入灰色分类或 Decision Tree |
| 🟢 | I/O 约束定义 | Input（walkthrough + plans）和 Output（正文 patch + changelog append）的界定清晰 |

**整体：🟢 🟡 — 愿景正确，需补充工作流完整性和分类粒度。**

#### 对执行者（Role 2）

| 评价 | 条目 | 说明 |
|------|------|------|
| 🟢 | 目录结构设计 | `docs/paper/` 的文件布局专业、工程友好，`_build/` 分离人工 LaTeX 模板是正确决策 |
| 🟢 | Digest YAML 策略核心思路 | "先蒸馏再注入"是解决上下文过载的正确方向 |
| 🟡 | Digest Agent 幻觉风险 | 已识别但未给出充分的缓解措施。需要增加 `status: draft` 和人工审校门控 |
| 🟡 | 方案 B 降级策略 | 切换条件应基于 token count 而非 file count；方案 B 不应触碰正文 |
| 🔴 | Pillar Anchors 覆盖盲区 | 四个锚点只保护了岛屿内部，锚点之间的"无人区"和相邻段落完全暴露，存在叙事连贯性被破坏的高风险 |
| 🟡 | 人工审批环节不足 | 两个方案都只在最后有 PILLAR_VERIFY（自动校验），缺乏正文 patch 前的人工 diff 预览 |
| 🟡 | Scaffold 骨架初始化 | 不应作为隐式首次运行行为，应拆为独立 sub-command |

**整体：🟡 🔴 — 方案 A 核心思路优秀，但 Pillar 护栏是硬伤，必须在 Round 2 给出修补方案。Digest 审校和人工门控也需要具体化。**

### 5. 修改要求清单（面向 Round 2）

| # | 要求 | 面向 | 优先级 |
|---|------|------|-------|
| R1 | 工作流增加 CONFLICT_DETECT 和 HUMAN_GATE 步骤 | 决策者 + 执行者 | 🔴 必须 |
| R2 | Pillar Anchors 扩展为 Structure Protection（heading 拓扑校验 + 过渡段落保护） | 执行者 | 🔴 必须 |
| R3 | Digest YAML 增加 `status` 和 `confidence` 字段，生产后需人工 review | 执行者 | 🔴 必须 |
| R4 | 方案 B 降级条件改为 total_plan_tokens 而非 file count | 执行者 | 🟡 建议 |
| R5 | 方案 B 适用范围收缩为仅 Changelog 追加 | 执行者 | 🟡 建议 |
| R6 | 引入分类 Decision Tree 或灰色分类处理非生态位但有架构叙事价值的改动 | 决策者 | 🟡 建议 |
| R7 | Scaffold 初始化拆为独立 `/cas-texwriter init` 子命令 | 执行者 | 🟡 建议 |
| R8 | 制定 Markdown 子集规范并写入 metadata 或 README | 执行者 | 🟡 建议 |

---

# ═══════════════════════════════════════════
# Round 2 — 最终轮
# ═══════════════════════════════════════════

## Role 1 (Decision Maker) — 决策者 Round 2 发言

> **发言者:** Role 1 决策者
> **日期:** 2026-04-04 (Round 2)

### 1. 对审查者 R1-R8 逐条裁决

#### R1 🔴 增加 CONFLICT_DETECT + HUMAN_GATE → ✅ Accept

完全接受。这是我在 Round 1 四步工作流中最大的遗漏——和上一轮圆桌（docs-reorg）的老毛病一模一样：**骨架画对了但闭环没做好**。

具体采纳方式：
- **CONFLICT_DETECT** 放在 ACADEMIC_TRANSLATE 之后、PATCH_WRITE 之前。实现方式：Agent 对比待写入段落 vs 目标 `.md` 文件当前内容的语义相似度。若检测到 >70% 重叠，标记为"潜在重复"，输出 diff 给人工决策（合并/覆盖/跳过）。
- **HUMAN_GATE** 放在 PATCH_WRITE 之前（正文修改时）。具体形式：输出完整的 `git diff --no-index` 格式预览，人工确认后才执行实际写入。**Changelog append 豁免此门控**——append-only + PILLAR_VERIFY 足矣。

最终方案 A 工作流更新为 **8 步**：
```
Step 1: VERSION_DETECT
Step 2: DIGEST_GENERATE
Step 2.5: 🧑 DIGEST_REVIEW (人工确认 pillars)
Step 3: WALKTHROUGH_EXTRACT + 分类 [A]/[B]/[C]
Step 4: SELECTIVE_DEEPREAD (仅 [A] 类)
Step 5: ACADEMIC_TRANSLATE
Step 5.5: CONFLICT_DETECT (语义去重)
Step 6: 🧑 PATCH_PREVIEW (输出 diff，人工确认) ← 仅正文
Step 7: PATCH_WRITE
Step 8: PILLAR_VERIFY + STRUCTURE_VERIFY (自动，失败回滚)
```

#### R2 🔴 Pillar Anchors → Structure Protection → ✅ Accept (Modified)

审查者指出的"无人区"盲点是真实的威胁。但我认为 `STRUCTURE_HASH` 方案**过于刚性**——每次修改都导致 hash 变化需要重新计算，运维成本高。

**我的修改方案：Heading Registry（轻量版结构保护）**

不使用 sha256 hash，改用一个人工维护的 **heading 白名单**，放在 `00-metadata.yaml` 中：

```yaml
structure_protection:
  "03-architecture.md":
    required_headings:
      - "## 3. System Architecture and Infrastructure"
      - "### 3.1 The 8-Layer Abstraction Architecture"
      - "### 3.2 Pipeline Orchestration on HPC Clusters"
      - "### 3.3 Universal ModelClient Layer"
    allow_new_subsections: true    # 允许新增 ####，但禁止删除/重排 ###
  "04-agent-tools.md":
    required_headings:
      - "## 4. Agent Coordination and Tool Constraining"
      - "### 4.1 Schema-Validated Tool Wrappers for HEP"
      - "### 4.2 Multi-Agent Review and Quality Assurance"
      - "### 4.3 The \"Inversion\" Mechanism"
    allow_new_subsections: true
```

PILLAR_VERIFY 阶段扩展为 **STRUCTURE_VERIFY**，校验：
1. 四个 PILLAR 锚点完整
2. `required_headings` 列表中的每个 heading 原样存在且顺序未变
3. 新增的 subsection（`####`）不违反父级 heading 的语义范围（由 Agent 在 PATCH_PREVIEW 阶段输出，人工在 HUMAN_GATE 确认）

**对审查者"过渡段落保护"的回应：** 我认为过渡段落的语义连贯性属于**人工审批（HUMAN_GATE）的职责范围**，不应该交给自动化工具判断。在 PATCH_PREVIEW 的 diff 输出中，过渡段落的修改会自然呈现，人工一眼就能看出是否断裂。试图让 Agent 自动校验"叙事连贯性"是过度工程化。

#### R3 🔴 Digest YAML 增加 status + confidence → ✅ Accept

完全正确。Digest 是整个提纯链的上游，垃圾进垃圾出。

采纳后的 Digest YAML 格式：
```yaml
version: "v0.3.0"
status: draft          # draft → reviewed (人工确认后改)
generated_at: "2026-04-04T00:30:00Z"
phases:
  - id: "8.5.4"
    name: "Non-Blocking Message Queue"
    abstract: "Async instruction queuing with 3-tier priority"
    pillars: ["HPC-Native"]
    confidence: high
    methodology_worthy: true
  - id: "8.5.3"
    name: "Input History"
    abstract: "JSONL-persisted terminal history"
    pillars: []
    confidence: high
    methodology_worthy: false   # → Changelog only
```

**补充决策：** `confidence: low` 的 Phase **不阻塞工作流**，但在 CLI 输出中用 ⚠️ 高亮，且在 DIGEST_REVIEW 人工审校阶段置顶显示。人工可以直接修改 YAML 中的 `pillars` 和 `confidence` 后改 `status: reviewed`。

#### R4 🟡 降级条件改为 token count → ✅ Accept

审查者完全正确，file count 是一个 naive metric。改为 `total_plan_tokens ≤ 15K`。

具体实现：技能在 Step 2 之前用简单的 `wc -c` 估算 total bytes，按 1 token ≈ 4 bytes 换算。若 ≤ 60KB（约 15K tokens），走方案 B；否则走方案 A。不需要精确 tokenizer——这只是一个路由决策，不影响最终质量。

#### R5 🟡 方案 B 仅限 Changelog → ✅ Accept

审查者的分析令人信服：walkthrough 只回答 "What" 不回答 "Why"，生成 Methodology 深度不够。

**最终定位：方案 B = "Changelog-Only Fast Path"**。当路由判断走方案 B 时，技能 **仅执行 Changelog 追加**，跳过正文 patch。正文更新永远需要走方案 A 的 Digest 路径。

#### R6 🟡 引入灰色分类 / Decision Tree → ✅ Accept (Modified)

审查者举的 `/clear` 生命周期管理案例很精准——它确实不直接属于四大生态位，但作为"8-Layer 职责分离"的论据有学术价值。

**我的方案：三级分类替代二分法**

| 分类 | 标签 | 去向 | 判定规则 |
|------|------|------|---------|
| **[A] Methodology-worthy** | `methodology_worthy: true` | 正文 patch | 直接贡献四大生态位，或引入新的架构层级/通信协议 |
| **[B] Architecture-evidence** | `architecture_evidence: true` | 正文脚注或"See also"引用，主体在 Changelog | 不直接贡献生态位，但作为某一层架构设计理念的佐证 |
| **[C] Changelog-only** | 两项均 false | 仅 Changelog | 纯 bugfix、UI 调整、重构等 |

在 Digest YAML 中用 `methodology_worthy` + `architecture_evidence` 两个 boolean 字段表达。Agent 在 Digest 生成时自行标注，人工在 DIGEST_REVIEW 阶段调整。

#### R7 🟡 init 子命令 → ✅ Accept

审查者说得对：scaffold 生成和日常更新是两个完全不同的职责。

**`/cas-texwriter` 拆为两个模式：**
- `/cas-texwriter init` — 一次性骨架生成。读 `00-metadata.yaml` 的章节配置 + NotebookLM 目录大纲 → 生成 `docs/paper/*.md` 含 PILLAR 锚点 + heading + 空白占位符。执行后写入 `scaffold_created: true`，二次调用报错。
- `/cas-texwriter`（默认）— 常规更新流程（方案 A 的 8 步）。前置检查 `scaffold_created: true`，否则提示先运行 `init`。

#### R8 🟡 Markdown 子集规范 → ✅ Accept

审查者提出的规范表非常专业，整体叫好。一点小修改：

- **Mermaid 禁止**：同意。架构图用预渲染 PNG/SVG。
- **交叉引用**：采用 pandoc-crossref 语法 `[@sec:xxx]`、`[@fig:xxx]`，不使用 Markdown 内链。
- **行内数学**：完全同意，HEP 论文没有 $\sigma$ 和 $\mathcal{L}$ 就不是 HEP 论文。

此规范写入 `docs/paper/00-metadata.yaml` 的 `markdown_spec` 字段，`cas-texwriter` 的 System Prompt 在每次调用时注入。

---

### 2. 对执行者三个追问的回答

#### Q1: 论文目录锁定时机

**v0.1-dev 阶段锁定一级和二级 heading（Chapter + Section），允许新增三级 heading（Subsection）。**

理由：
- NotebookLM 给出的 7 章 + 3 附录框架已经足够稳定（经过 6 篇竞品论文的 comparative analysis 才得出的结构），一级二级不应轻易改动。
- 但随着开发深入，某个 Section（如 3.2 Pipeline Orchestration）下可能需要新增 `#### 3.2.1 Condor Job Lifecycle` 这类 Subsection。这应该被允许，但需要在 PATCH_PREVIEW 阶段由人工确认。
- `00-metadata.yaml` 中的 `required_headings` 列表（R2 方案）天然实现了这个约束。

#### Q2: Changelog 粒度

**以 Phase 为最小粒度，绝对不到 commit 级别。**

格式示例：
```markdown
## v0.3.0 (2026-04-03)

### Phase 8.5: Textual TUI Migration & Slash Commands
- Replaced Rich+prompt_toolkit REPL with full Textual alternate-screen TUI
- 4 core commands: /help, /exit, /clear, /model
- Inline command palette and model palette with keyboard navigation

### Phase 8.5.3: Input History
- JSONL-persisted terminal history with cross-session recall
- 2000-entry cap with consecutive deduplication

### Phase 8.5.4: Non-Blocking Message Queue
- 3-tier priority queue (now/next/later) mirroring Claude Code architecture
- ESC layered cancellation: generation → queue → focus
```

每个 Phase 3-5 个 bullet，每个 bullet 一句话。这就是 Changelog 的全部粒度。

#### Q3: 首次初始化

**已在 R7 裁决中回答：由 `/cas-texwriter init` 子命令生成骨架，人工审校 commit 后才能运行常规更新。**

补充：`init` 生成的骨架文件将包含：
1. 所有 `required_headings`（从 `00-metadata.yaml` 读取）
2. 四个 PILLAR 锚点（含空白占位符 `<!-- TODO: 填写核心命题句 -->`）
3. Changelog 附录的基本结构（版本号 section header）
4. **不包含任何实质性文本内容**——核心命题句由人工手写

---

### 3. 决策者自省

Round 1 的三个问题表面上开放，实际上我心里已经有了倾向但没有给出明确约束，导致执行者和审查者不得不在"猜测我的意图"上花了大量篇幅。这个问题在上一轮圆桌（docs-reorg）中已经自省过——**Open Questions 不是决策者的"留白艺术"，而是执行链的阻塞项。**

审查者指出的两个盲区都扎中了要害：
1. 我的四步工作流完全没有人工审批环节——这对于学术论文正文的修改来说是不可接受的高风险。我过于关注"Agent 写得对不对"，忽略了"写完之后谁来看"。
2. "高傲"策略的二分法过于粗糙。审查者的 `/clear` 案例让我意识到，架构论文不仅需要"核心命题"，还需要"佐证案例"——这两者的学术价值完全不同但都不可或缺。三级分类方案（[A][B][C]）比我原来的二分法精准得多。

---

### 4. 对执行者和审查者 Round 2 的建议

#### 对执行者（Round 2 重点方向）：
1. **输出完整的方案 A v2 工作流**（8 步版本），每一步标注 Input/Output/失败处理。这是我们最终要写进 skill 文件的核心流程。
2. **给出 Digest YAML 的完整 Schema**，包含 R3 和 R6 的所有新增字段（`status`, `confidence`, `methodology_worthy`, `architecture_evidence`）。
3. **考虑 `_build/Makefile` 的基本设计**——pandoc 命令行 + JHEP 模板 + crossref filter 的具体 pipeline。这不进技能文件但需要记录在 `docs/paper/_build/README.md`。

#### 对审查者（Round 2 重点方向）：
1. **校验我对 R2 的修改方案（Heading Registry）** 是否充分覆盖了你在 Round 1 指出的四个风险场景。如果你认为仍有盲区，给出具体的攻击场景。
2. **审查三级分类方案的可操作性**——[B] 类的"正文脚注或 See also"具体应该以什么 Markdown 语法表达？Agent 是否能可靠地区分 [A] 和 [B]？
3. **对 Markdown 子集规范的最终确认**——我在 R8 中做了一点微调，请确认无遗漏。

---

## Role 2 (Executor) — 执行者 Round 2 发言

> **发言者:** Role 2 执行者
> **日期:** 2026-04-04 (Round 2)

### 对决策者裁决的执行确认

R1-R8 全部 Accept + R2/R6 Modified——决策者的裁决方向清晰，所有修改要求我在本轮具体落地。以下逐一交付三个任务的产出。

---

### 任务 1：方案 A v2 完整工作流（8 步，含 Input/Output/失败处理）

> **适用条件**：`total_plan_bytes > 60KB`（~15K tokens），或用户显式调用 `/cas-texwriter`。
> **前置检查**：`00-metadata.yaml` 中 `scaffold_created: true`，否则提示 `请先运行 /cas-texwriter init`。

---

#### Step 1: VERSION_DETECT

| 项 | 内容 |
|----|------|
| **Input** | `docs/walkthrough.md` |
| **动作** | 解析文档中最新的 `# [vX.Y.Z]` heading，提取版本号 + 其下所有 `## Phase` block 的列表 |
| **Output** | `current_version: str`（如 `"v0.3.0"`）+ `phase_ids: list[str]`（如 `["8.5", "8.5.3", "8.5.4"]`） |
| **失败处理** | 若 walkthrough 中无法匹配 version heading → **ABORT**，输出 `ERROR: Cannot detect current version in walkthrough.md. Ensure the latest version block uses '# [vX.Y.Z]' format.` |

---

#### Step 1.5: ROUTE_DECISION

| 项 | 内容 |
|----|------|
| **Input** | `docs/plans/{current_version}/` 目录 |
| **动作** | `stat` 所有 `*.md` 文件，求 `total_bytes = sum(file_sizes)` |
| **Output** | 路由判定：`total_bytes > 60KB` → 继续方案 A；`total_bytes ≤ 60KB` → 降级为 **方案 B (Changelog-Only Fast Path)**，跳至 Changelog 追加逻辑后直接 → Step 8 |
| **失败处理** | 目录不存在 → **WARN**，降级为方案 B（假设该版本无 plan 文件，仅靠 walkthrough 生成 Changelog） |

---

#### Step 2: DIGEST_GENERATE

| 项 | 内容 |
|----|------|
| **Input** | `docs/plans/{current_version}/*.md`（逐文件读取），`00-metadata.yaml` 中的 `pillars` 定义 |
| **动作** | 对每个 plan 文件，LLM 提取：(1) Phase ID + Name；(2) 30 词以内 abstract；(3) `pillars` 标签（从四大生态位中选）；(4) `confidence` 自评（high/medium/low）；(5) `methodology_worthy` + `architecture_evidence` 布尔值；(6) `key_files` 列表 |
| **Output** | `docs/paper/_digests/{current_version}-digest.yaml`，`status: draft` |
| **失败处理** | 若某个 plan 文件超出单次 LLM 上下文窗口 → **分块处理**：将文件按 `## Phase` heading 切片，逐块提取后合并。若仍然失败 → 该 Phase 标记 `confidence: low`，`abstract: "EXTRACTION_FAILED — manual review required"`，不阻塞流程 |

**关键约束**：若 `_digests/{current_version}-digest.yaml` 已存在且 `status: reviewed` → **跳过此步**（不覆盖已审校的 digest）。若存在但 `status: draft` → **覆盖重新生成**（允许迭代改进）。

---

#### Step 2.5: 🧑 DIGEST_REVIEW（人工门控）

| 项 | 内容 |
|----|------|
| **Input** | 新生成的 `{version}-digest.yaml` |
| **动作** | 在 CLI 中格式化输出 digest 内容。`confidence: low` 的 Phase 用 ⚠️ 置顶高亮显示，提示人工重点审校。输出交互提示：`Review the digest above. Edit the YAML file directly if needed, then type 'approve' to continue or 'abort' to cancel.` |
| **Output** | 人工修改后的 YAML（`status` 由 `draft` → `reviewed`，`pillars` / `methodology_worthy` / `architecture_evidence` 可能已被调整） |
| **失败处理** | 用户输入 `abort` → **ABORT** 整个工作流。用户直接修改了 YAML 但忘记改 `status` → Agent 自动将 `status` 设为 `reviewed`（因为人工已介入审校） |

---

#### Step 3: WALKTHROUGH_EXTRACT + 三级分类

| 项 | 内容 |
|----|------|
| **Input** | `docs/walkthrough.md` 中当前 version block + `{version}-digest.yaml`（已 reviewed） |
| **动作** | 从 walkthrough 提取所有 Phase 的完整描述段落。结合 digest 中的 `methodology_worthy` 和 `architecture_evidence` 字段，将每个 Phase 分为三类 |
| **Output** | 三个列表：`[A] Methodology-worthy`（正文 patch）；`[B] Architecture-evidence`（正文脚注 + Changelog）；`[C] Changelog-only`（仅 Changelog） |
| **失败处理** | walkthrough 中某个 Phase 在 digest 中无对应条目 → 默认归为 `[C]`，`WARN` 输出提醒 |

**[B] 类脚注语法约定**（决策者 R6 的落地实现）：

```markdown
<!-- 正文中的引用方式 -->
The 8-layer architecture enforces strict separation of concerns across
its component lifecycle, as evidenced by the session reset mechanism[^clear-lifecycle].

<!-- 对应脚注（同文件底部） -->
[^clear-lifecycle]: See Phase 8.5 `/clear` command lifecycle in Appendix A Changelog (v0.3.0).
```

Agent 生成 `[B]` 类内容时，仅需在正文相关段落中插入脚注引用 `[^phase-name]`，并在文件底部生成脚注定义，指向 Changelog 中的具体 Phase。pandoc 原生支持此语法。

---

#### Step 4: SELECTIVE_DEEPREAD

| 项 | 内容 |
|----|------|
| **Input** | `[A]` 类 Phase 列表 + digest 中对应的 `key_files` 字段 |
| **动作** | 对每个 `[A]` 类 Phase，加载其对应的 plan 全文（从 `docs/plans/{version}/` 中按 Phase ID 定位文件）。提取设计哲学（Why）和实现机制（How） |
| **Output** | 每个 `[A]` Phase 的结构化知识包：`{ why: str, how: str, key_concepts: list[str], target_sections: list[str] }` |
| **失败处理** | Plan 文件不存在（Phase 可能来自 walkthrough 但无独立 plan） → 使用 walkthrough 段落作为降级输入，`WARN` 输出 `Phase {id} has no plan file, using walkthrough as sole source — depth may be limited` |
| **上下文预算**：总加载量硬限 ≤ 3 个 plan 全文。若 `[A]` 类 > 3 个 Phase 且分布在 > 3 个 plan 文件中 → 按 `confidence` 降序排列，只加载 top-3 plan 文件，余下 `[A]` Phase 降级为仅用 walkthrough + digest abstract |

---

#### Step 5: ACADEMIC_TRANSLATE

| 项 | 内容 |
|----|------|
| **Input** | Step 4 产出的知识包 + 目标正文 `*.md` 文件当前内容 + `00-metadata.yaml` 中的 `markdown_spec` 和 `required_headings` |
| **动作** | 对每个 `[A]` 类 Phase：(1) 定位目标章节（从 digest `target_sections` 或 heading registry 映射）；(2) 将工程语言升华为学术叙事（如 "Phase 8.5.4 Message Queue" → "Asynchronous Non-blocking Instruction Queuing for Real-time Generation"）；(3) 生成 patch 段落（新增或替换），记录在内存中的 `PatchSet` 数据结构。对每个 `[B]` 类 Phase：生成脚注引用 + 脚注定义。对全部 Phase（`[A]+[B]+[C]`）：格式化为 Changelog bullet list |
| **Output** | `PatchSet { methodology_patches: list[Patch], footnote_patches: list[Patch], changelog_entry: str }` |
| **失败处理** | 若 Agent 无法确定某段 patch 的目标 heading → `WARN` 标记该 patch 为 `unanchored`，在 PATCH_PREVIEW 中高亮，由人工指定插入位置 |

**关键约束**：
- 新追加的段落必须包含来源标记 `[ref: Phase X.Y.Z]`（以 HTML 注释形式嵌入，不显示在最终 LaTeX 中）：`<!-- [ref: Phase 8.5.4] -->`
- PILLAR 锚点内的核心命题句（锚点后第一段）绝对不得修改，仅允许在其后追加
- 所有输出必须符合 `markdown_spec` 规范（无 Mermaid、无原生 HTML、交叉引用用 `[@sec:xxx]`）

---

#### Step 5.5: CONFLICT_DETECT

| 项 | 内容 |
|----|------|
| **Input** | `PatchSet.methodology_patches` + 各目标 `.md` 文件当前内容 |
| **动作** | 对每个 patch，提取其核心关键词/概念，与目标文件中已有段落做语义比对。使用简易策略：提取 patch 和目标段落的名词短语集合，计算 Jaccard 相似度。阈值 > 0.7 标记为"潜在重复" |
| **Output** | `ConflictReport { conflicts: list[{ patch_id, target_paragraph, similarity, suggestion: "merge" | "replace" | "skip" }] }` |
| **失败处理** | 无冲突 → 直接进入 Step 6。有冲突 → 在 Step 6 的 PATCH_PREVIEW 中**额外高亮冲突区域**，附上 `suggestion`，由人工最终裁决 |

**实现说明**：这里不需要 embedding model 或向量数据库。由于论文正文文件很小（预计每个 < 5KB），直接在 LLM 上下文内做全文比对即可。Agent 读入目标文件全文 + 待写入段落，在同一个 prompt 中判断是否有语义重复。

---

#### Step 6: 🧑 PATCH_PREVIEW（人工门控 — 仅正文修改）

| 项 | 内容 |
|----|------|
| **Input** | `PatchSet` + `ConflictReport` |
| **动作** | 输出格式化的 diff 预览（`git diff --no-index` 风格），分为三个 section：(1) **Methodology patches**（带冲突标注 ⚠️）；(2) **Footnote inserts**（[B] 类脚注）；(3) **Changelog append**（仅信息展示，不需审批）。输出交互提示：`Review the patches above. Type 'apply all', 'apply [1,3,5]' (selective), or 'abort'.` |
| **Output** | 用户批准的 patch 子集 |
| **失败处理** | `abort` → **ABORT** 工作流（但 digest 已 `reviewed`，下次调用可跳过 Step 2）。选择性批准 → 仅写入被批准的 patch。冲突项未被人工处理 → 跳过该 patch，`WARN` 输出 |

**Changelog append 豁免审批**：Changelog 是 append-only 且 Step 8 会验证结构完整性，无需在此阻塞。Changelog 始终在 Step 7 写入。

---

#### Step 7: PATCH_WRITE

| 项 | 内容 |
|----|------|
| **Input** | 人工批准的 patch 子集 + Changelog entry |
| **动作** | (1) 将批准的 methodology patches 写入对应正文 `*.md` 文件；(2) 将脚注 patches 写入对应文件底部；(3) 将 Changelog entry **append** 到 `appendix-changelog.md` 的当前版本 section 顶部（最新在前） |
| **Output** | 修改后的文件列表 |
| **失败处理** | 文件写入失败（权限、磁盘满等） → **ABORT**，输出未写入的 patch 内容到 stdout 供手动恢复 |

---

#### Step 8: STRUCTURE_VERIFY（自动校验）

| 项 | 内容 |
|----|------|
| **Input** | 修改后的所有正文 `*.md` 文件 + `00-metadata.yaml` |
| **动作** | 执行三项自动校验 |
| **Output** | `VerifyReport { passed: bool, failures: list[str] }` |
| **失败处理** | 见下方各项 |

**校验项：**

| # | 校验 | 规则 | 失败动作 |
|---|------|------|---------|
| V1 | PILLAR 锚点完整性 | 四个 `<!-- PILLAR:* :: BEGIN/END -->` 锚点对全部存在 | **ROLLBACK** 所有 Step 7 写入 + `ERROR` 输出缺失的锚点 |
| V2 | Heading Registry | `required_headings` 中每个 heading 原样存在、顺序未变 | **ROLLBACK** + `ERROR` 输出被删除/移动的 heading |
| V3 | 核心命题句不变性 | 每个 PILLAR 锚点后的第一段（命题句）与 `_build/.pillar_baselines` 中存储的基线文本一致 | **ROLLBACK** + `ERROR` 输出被篡改的命题句 diff |

**关于 V3 的补充设计**：`_build/.pillar_baselines` 是一个在 `/cas-texwriter init` 阶段人工写完核心命题句后自动快照的文件，格式如下：

```yaml
# Auto-generated by /cas-texwriter init, DO NOT EDIT
# To update a pillar thesis, use /cas-texwriter update-pillar <pillar-name>
baselines:
  HPC-Native: "Cascade is the first agentic framework natively designed for HPC clusters such as CERN lxplus..."
  Combine-ROOT: "Cascade treats CMS Combine and deep ROOT macro integration as first-class citizens..."
  Universal-API: "The framework's bottom layer incorporates a custom API abstraction layer supporting..."
  Inversion: "When the agent cannot locate sufficiently justified physical boundary conditions..."
```

这样 V3 可以做精确的字符串比对，不依赖 LLM 判断。

**ROLLBACK 机制**：Step 7 写入前自动创建 `_build/.pre_patch_backup/` 目录，存放所有即将被修改的文件的副本。ROLLBACK 时从此目录恢复。

---

### 任务 2：Digest YAML 完整 Schema

```yaml
# ═══════════════════════════════════════════
# cas-texwriter Digest Schema v1.0
# File: docs/paper/_digests/{version}-digest.yaml
# ═══════════════════════════════════════════

# --- Top-level Metadata ---
version: string          # Required. Semantic version, e.g. "v0.3.0"
status: enum             # Required. "draft" | "reviewed"
                         #   draft:    Agent-generated, pending human review
                         #   reviewed: Human-confirmed, safe for Stage 2 injection
generated_at: datetime   # Required. ISO 8601 timestamp of generation
reviewed_at: datetime    # Optional. ISO 8601 timestamp of human review
reviewed_by: string      # Optional. Reviewer identifier
digest_schema: string    # Required. Schema version, fixed "1.0"

# --- Phase Entries ---
phases: list             # Required. One entry per Phase detected in plans
  - id: string           # Required. Phase identifier, e.g. "8.5.4"
    name: string         # Required. Human-readable Phase name
    abstract: string     # Required. ≤ 30 words summarizing the core change
                         #   Special value: "EXTRACTION_FAILED — manual review required"
                         #   (set when LLM extraction fails on a plan chunk)

    # --- Four Pillars Classification (R6 三级分类) ---
    pillars: list[enum]  # Required. Subset of:
                         #   "HPC-Native"
                         #   "Combine-ROOT"
                         #   "Universal-API"
                         #   "Inversion"
                         #   Empty list = no direct pillar contribution

    methodology_worthy: bool
                         # Required. true = [A] class → full methodology patch
                         #   Criteria: directly contributes to a pillar,
                         #             OR introduces a new architecture layer/protocol

    architecture_evidence: bool
                         # Required. true = [B] class → footnote in body + changelog
                         #   Criteria: does not directly contribute to a pillar,
                         #             BUT serves as evidence for layer separation / design philosophy
                         #   Note: methodology_worthy takes precedence.
                         #         If methodology_worthy=true, architecture_evidence is ignored.

    # Derived classification:
    #   [A] = methodology_worthy == true
    #   [B] = methodology_worthy == false AND architecture_evidence == true
    #   [C] = both false

    confidence: enum     # Required. Agent self-assessed confidence in classification
                         #   "high":   strong signal, clear pillar alignment
                         #   "medium": ambiguous, reasonable humans might disagree
                         #   "low":    weak signal, likely needs human override
                         #   Display: low → ⚠️ in CLI, top-sorted in DIGEST_REVIEW

    # --- Provenance ---
    source_plan: string  # Required. Filename of the plan file this Phase was extracted from
                         #   e.g. "phase8.5.4-input-queue.md"
    key_files: list[str] # Optional. Source code files most relevant to this Phase
                         #   Used by SELECTIVE_DEEPREAD to locate plan for [A] Phases
    target_sections: list[str]
                         # Optional. Suggested heading(s) in paper/*.md where this
                         #   Phase should be patched, e.g. ["03-architecture.md#3.2"]
                         #   Agent-suggested, human may override in DIGEST_REVIEW

# --- Validation Rules ---
# 1. Each phase.id must be unique within the file
# 2. pillars values must be from the enum above (no free-form strings)
# 3. If methodology_worthy=true, pillars SHOULD be non-empty (WARN if empty)
# 4. If confidence="low", abstract MUST NOT be "EXTRACTION_FAILED" (use the latter only on total failure)
# 5. status="reviewed" requires reviewed_at to be set
```

**示例文件（完整）：**

```yaml
version: "v0.3.0"
status: reviewed
generated_at: "2026-04-04T00:30:00Z"
reviewed_at: "2026-04-04T01:15:00Z"
reviewed_by: "ky230"
digest_schema: "1.0"

phases:
  - id: "8.5"
    name: "Textual TUI Migration & Slash Commands"
    abstract: "Full Textual alternate-screen TUI replacing Rich+prompt_toolkit REPL with inline command and model palettes"
    pillars: []
    methodology_worthy: false
    architecture_evidence: true     # [B]: evidences Layer 6 (UI) separation
    confidence: high
    source_plan: "phase8.5-textual-migration.md"
    key_files: ["textual_app.py", "command_palette.py", "model_palette.py"]
    target_sections: ["03-architecture.md#3.1"]

  - id: "8.5.3"
    name: "Input History"
    abstract: "JSONL-persisted terminal history with cross-session recall and consecutive deduplication"
    pillars: []
    methodology_worthy: false
    architecture_evidence: false    # [C]: pure UX feature
    confidence: high
    source_plan: "phase8.5.3-input-history.md"
    key_files: ["input_history.py"]
    target_sections: []

  - id: "8.5.4"
    name: "Non-Blocking Message Queue"
    abstract: "Async instruction queuing with 3-tier priority and generation-numbered state machine, mirroring Claude Code QueueProcessor"
    pillars: ["HPC-Native"]
    methodology_worthy: true        # [A]: pipeline orchestration pattern
    architecture_evidence: false
    confidence: medium              # ⚠️ HPC-Native link is indirect (async UI queue ≠ HPC batch queue)
    source_plan: "phase8.5.4-input-queue.md"
    key_files: ["message_queue.py", "query_guard.py", "queue_processor.py"]
    target_sections: ["03-architecture.md#3.2"]
```

---

### 任务 3：`_build/Makefile` 设计

#### 设计原则

1. **人工维护**：Makefile 和 LaTeX 模板不进入 `cas-texwriter` 的管辖范围，Agent 不会修改这些文件
2. **一键构建**：`make pdf` 从 `docs/paper/*.md` 生成完整的 JHEP 格式 PDF
3. **增量友好**：依赖关系清晰，修改单个 `.md` 文件后只重新编译必要部分
4. **CI 兼容**：可在 GitHub Actions / lxplus 上无交互运行

#### 目录结构

```
docs/paper/_build/
├── Makefile
├── template.tex          # JHEP/SciPost LaTeX 模板 (从 journal class 修改)
├── references.bib        # 人工维护的 BibTeX 文献库
├── filters/
│   └── crossref-meta.yaml  # pandoc-crossref 配置
├── figures/              # 预渲染的架构图 PNG/SVG
│   ├── 8-layer-architecture.pdf
│   └── pipeline-orchestration.pdf
├── .pillar_baselines     # PILLAR 核心命题句快照 (Step 8 V3 用)
└── README.md             # 构建说明文档
```

#### Makefile

```makefile
# ═══════════════════════════════════════════
# Cascade Technical Whitepaper — Build Pipeline
# Usage: make pdf | make draft | make clean | make wordcount
# ═══════════════════════════════════════════

# --- Configuration ---
PAPER_DIR  := $(dir $(MAKEFILE_LIST))..
BUILD_DIR  := $(dir $(MAKEFILE_LIST))
OUT_DIR    := $(BUILD_DIR)output
TEMPLATE   := $(BUILD_DIR)template.tex
BIB        := $(BUILD_DIR)references.bib
CROSSREF   := $(BUILD_DIR)filters/crossref-meta.yaml

# Source markdown files in reading order
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

METADATA := $(PAPER_DIR)/00-metadata.yaml

TARGET := $(OUT_DIR)/cascade-whitepaper.pdf
DRAFT  := $(OUT_DIR)/cascade-whitepaper-draft.pdf

# --- Pandoc Flags ---
PANDOC_BASE := pandoc \
    --from=markdown+smart+footnotes+pipe_tables+inline_code_attributes \
    --to=latex \
    --template=$(TEMPLATE) \
    --metadata-file=$(METADATA) \
    --bibliography=$(BIB) \
    --citeproc \
    --filter=pandoc-crossref \
    --crossref-config=$(CROSSREF) \
    --number-sections \
    --pdf-engine=latexmk \
    --pdf-engine-opt=-xelatex \
    --pdf-engine-opt=-interaction=nonstopmode \
    --resource-path=$(BUILD_DIR)figures

# --- Targets ---
.PHONY: pdf draft clean wordcount check-deps

pdf: check-deps $(TARGET)

$(TARGET): $(SOURCES) $(APPENDICES) $(METADATA) $(TEMPLATE) $(BIB)
	@mkdir -p $(OUT_DIR)
	$(PANDOC_BASE) \
	    $(METADATA) $(SOURCES) $(APPENDICES) \
	    -o $@
	@echo "✅ PDF generated: $@"

draft: check-deps
	@mkdir -p $(OUT_DIR)
	$(PANDOC_BASE) \
	    -V draft=true \
	    -V watermark="DRAFT — $(shell date +%Y-%m-%d)" \
	    $(METADATA) $(SOURCES) $(APPENDICES) \
	    -o $(DRAFT)
	@echo "📝 Draft PDF generated: $(DRAFT)"

wordcount:
	@cat $(SOURCES) | wc -w | xargs -I{} echo "Main body: {} words"
	@cat $(APPENDICES) | wc -w | xargs -I{} echo "Appendices: {} words"

clean:
	@echo "This will remove $(OUT_DIR)/, proceed? [y/N]"
	@read ans && [ "$$ans" = "y" ] && rm -rf $(OUT_DIR) || echo "Cancelled."

check-deps:
	@command -v pandoc >/dev/null 2>&1 || { echo "❌ pandoc not found"; exit 1; }
	@command -v pandoc-crossref >/dev/null 2>&1 || { echo "❌ pandoc-crossref not found"; exit 1; }
	@command -v latexmk >/dev/null 2>&1 || { echo "❌ latexmk not found"; exit 1; }
```

#### `crossref-meta.yaml`

```yaml
# pandoc-crossref configuration for JHEP-style cross-referencing
figureTitle: "Figure"
tableTitle: "Table"
listingTitle: "Listing"
figPrefix: "Fig."
tblPrefix: "Tab."
lstPrefix: "Listing"
secPrefix: "Sec."
eqnPrefix: "Eq."
chaptersDepth: 0          # No chapter numbering (JHEP uses flat section numbers)
numberSections: true
sectionsDepth: 3          # Number down to ### level
autoSectionLabels: true   # Auto-generate labels from headings
```

#### `template.tex` 设计说明

不在此处输出完整 LaTeX 模板（约 200 行），但记录设计要点：

| 组件 | 方案 |
|------|------|
| Document class | `\documentclass[11pt,a4paper]{article}` + JHEP-style 手动宏定义（不依赖 `jheppub.sty`，因为 JHEP 模板对外部 pandoc 不友好） |
| Font | XeLaTeX + `fontspec`，主体用 Computer Modern（与 JHEP 一致） |
| Math | `amsmath` + `amssymb`（HEP 标准） |
| 交叉引用 | `cleveref`（由 pandoc-crossref filter 自动注入） |
| 代码块 | `minted` 或 `listings`（用于展示配置片段） |
| 图表 | `graphicx` + `booktabs`（pandoc 管道表自动转换） |
| 附录 | `\appendix` 命令后追加附录章节 |
| Draft 模式 | `\ifdraft` 条件编译：添加水印、行号、TODO 高亮 |

#### lxplus 兼容性说明

lxplus 上 TeXLive 版本较旧但足够。需要注意：
- `pandoc` 和 `pandoc-crossref` 需要用 `conda` 或 `linuxbrew` 安装（lxplus 系统包过旧）
- 建议在 `CVMFS` 上找 TeXLive 路径：`/cvmfs/sft.cern.ch/lcg/external/texlive/`
- Makefile 中的 `check-deps` 会在缺依赖时给出明确报错

---

### 执行者 Round 2 自省

Round 1 被审查者指出的 🔴 Pillar Anchors 盲区确实是我的硬伤。回顾原因：

1. 我过度聚焦于"保护岛屿内部"，忽略了"岛屿之间的海面"——经典的边界安全思维缺陷。决策者的 Heading Registry 方案比我的锚点方案在覆盖面上强了一个量级，且运维成本合理。
2. 关于 V3（核心命题句不变性）校验，Round 1 我只说了"规则链硬编码在 System Prompt 中"——这是靠 Agent 自律，不可靠。现在用 `.pillar_baselines` 做精确字符串比对，是确定性保障，不依赖 LLM 判断。

对于方案 B 的降级策略，审查者"token count 而非 file count"的修正是完全正确的——我犯了典型的 proxy metric 错误。

---

## Role 3 (Reviewer) — 审查者 Round 2 发言

> **发言者:** Role 3 审查者
> **日期:** 2026-04-04 (Round 2)

### 任务 1：Heading Registry 方案覆盖度校验

决策者用 `00-metadata.yaml` 中的 heading 白名单取代了我 Round 1 提出的 `STRUCTURE_HASH` 方案。我同意决策者的判断——`STRUCTURE_HASH` 确实过于刚性（每次新增 `####` 都会导致 hash 变化，增加无意义的运维负担）。Heading Registry 是更务实的选择。

现在需要逐项验证三合一方案（Heading Registry + PILLAR_VERIFY + STRUCTURE_VERIFY）是否覆盖了 Round 1 提出的四个风险场景：

| # | 风险场景 | 覆盖方 | 覆盖状态 | 分析 |
|---|---------|--------|---------|------|
| S1 | Agent 删除锚点内核心命题句 | V1 (PILLAR 锚点完整性) + V3 (命题句基线比对) | ✅ **完全覆盖** | V1 检测锚点对存在性；V3 用 `.pillar_baselines` 做精确字符串比对，不依赖 LLM。这是 Round 1 到 Round 2 最大的改进——从"Agent 自律"升级为"确定性校验"。 |
| S2 | Agent 在锚点内追加与命题句矛盾的信息 | V3 (部分) + Step 6 HUMAN_GATE | ⚠️ **间接覆盖** | V3 只保护命题句不被修改，不校验追加段落与命题句的逻辑一致性。但 Step 6 PATCH_PREVIEW 的 diff 输出会让人工看到追加内容，人工可判断是否矛盾。决策者说"叙事连贯性交给人工审批"——我接受这个设计哲学，**前提是 PATCH_PREVIEW 的 diff 格式足够清晰**（见下方建议）。 |
| S3 | Agent 在锚点外部改坏相邻段落 | V2 (Heading Registry) + Step 6 HUMAN_GATE | ✅ **覆盖** | V2 确保 `###` 级 heading 不被删除或重排，包括锚点外部的相邻 section heading。过渡段落的内容变化通过 PATCH_PREVIEW diff 呈现，人工一审即知。这是决策者方案的精妙之处：**用 heading 骨架的不变性来锚定段落位置，用人工审批来保证段落内容质量**。 |
| S4 | Agent 在两个锚点之间的"无人区"插入不当内容 | V2 (Heading Registry) + Step 5.5 CONFLICT_DETECT + Step 6 HUMAN_GATE | ✅ **覆盖** | "无人区"插入意味着在两个 `###` heading 之间新增段落。V2 确保 heading 结构不变；CONFLICT_DETECT 检测语义重复；PATCH_PREVIEW diff 呈现插入内容。三层防护足够。 |

**覆盖度总结：4/4 场景覆盖。** S2 依赖人工审批而非自动化校验，但这是合理的 trade-off——试图让机器判断"两段话是否逻辑矛盾"会引入更多幻觉问题。

**一项增强建议（非阻塞）：**

Step 6 PATCH_PREVIEW 在输出 diff 时，对 PILLAR 区域内的修改应标注特殊前缀 `[PILLAR ZONE]`，提醒人工重点审查。例如：

```diff
[PILLAR ZONE: HPC-Native]
+ <!-- [ref: Phase 8.5.4] -->
+ The asynchronous instruction queuing mechanism extends the pipeline
+ orchestration layer with a 3-tier priority model.
```

这不改变工作流结构，只是改善 PATCH_PREVIEW 的可读性，帮助人工在 S2 场景中做出正确判断。

---

### 任务 2：三级分类可操作性审查

#### 2.1 [B] 类脚注语法 `[^footnote-id]` 审查

执行者用 `[^clear-lifecycle]` 语法落地 [B] 类的"正文脚注引用"。**语法选择正确，pandoc 原生支持。**

但需要注意 **pandoc → LaTeX 脚注渲染的两个细节**：

| 问题 | 影响 | 解决方案 |
|------|------|---------|
| pandoc 将 `[^id]` 转为 LaTeX `\footnote{}`，脚注编号自动重排 | 无影响——这正是我们想要的行为 | 无需处理 |
| 脚注中包含 backtick（如 `` `/clear` ``）时，pandoc 转换为 `\texttt{/clear}`，在某些 JHEP 模板下可能因缺少 `\usepackage{textcomp}` 而报错 | ⚠️ 构建失败 | `template.tex` 须确保加载 `textcomp` 和 `upquote` 包。执行者在模板设计说明中已列 `minted`/`listings`，但未显式提到这两个基础包——**建议补充。** |
| 脚注文本过长（如包含完整的 Phase 名称 + Changelog 引用）在 JHEP 双栏排版下可能溢出 | ⚠️ 排版问题 | 限制脚注文本 ≤ 2 行（约 80 英文字符）。可在 `markdown_spec` 中增加约束：`footnote_max_length: 80` |

**结论：`[^id]` 语法可用，需在 `template.tex` 和 `markdown_spec` 中补充两项约束。**

#### 2.2 Agent 区分 [A] 和 [B] 的可靠性

这是三级分类方案最脆弱的环节。核心问题：

**[A] 和 [B] 的判定规则本质上要求 Agent 理解"直接贡献 pillar"与"间接佐证 pillar"的区别。**

以执行者给出的示例为例：
- Phase 8.5.4 (Message Queue): `pillars: ["HPC-Native"]`, `methodology_worthy: true`, `confidence: medium`
- Phase 8.5 (TUI Migration): `pillars: []`, `architecture_evidence: true`, `confidence: high`

执行者自己也在 Phase 8.5.4 上标了 `confidence: medium`，并注释道"HPC-Native link is indirect (async UI queue ≠ HPC batch queue)"。这恰恰证明了 **即使是具备完整上下文的人类，在 [A]/[B] 边界上也会犹豫**。

**风险评估：** `confidence: medium` 的 Phase 在 DIGEST_GENERATE 阶段有约 30-40% 的概率被错误分类（基于通用 LLM 在 taxonomy 任务上的表现估计）。但由于 Step 2.5 DIGEST_REVIEW 提供了人工门控，且 `confidence: medium` 会在 CLI 中高亮提示，**实际风险可控**。

**一项增强建议（非阻塞）：**

在 DIGEST_GENERATE 的 LLM prompt 中，增加 **few-shot 示例**：

```
Example classification:
- "Non-Blocking Message Queue with 3-tier priority" → pillars: ["HPC-Native"], methodology_worthy: true
  Reasoning: Directly implements pipeline orchestration pattern central to HPC-Native claim.
  
- "Textual TUI Migration" → pillars: [], architecture_evidence: true
  Reasoning: Does not directly serve any pillar, but demonstrates Layer 6 (UI) separation in 8-Layer Architecture.
  
- "Input History JSONL persistence" → pillars: [], methodology_worthy: false, architecture_evidence: false
  Reasoning: Pure UX feature, no architectural significance.
```

Few-shot 示例可以将 `confidence: medium` 场景的分类准确率从 ~60% 提升到 ~80%。这些示例可以写入 `00-metadata.yaml` 的 `classification_examples` 字段，随 Agent 调用注入。

---

### 任务 3：执行者三大交付物技术审查

#### 3.1 方案 A v2 工作流（8 步）技术审查

**整体评价：工业级完成度，每步的 Input/Output/失败处理清晰，是可直接写入 skill 文件的规格。**

逐步审查发现的问题：

| Step | 问题 | 严重性 | 建议 |
|------|------|--------|------|
| **1.5 ROUTE_DECISION** | 当 `docs/plans/{version}/` 目录不存在时降级为方案 B——但方案 B 现在被限定为"仅 Changelog 追加"。如果用户显式调用 `/cas-texwriter` 期望正文更新，此降级会产生困惑 | 🟡 | 目录不存在时应输出 **明确提示**：`WARN: No plan files found for {version}. Only Changelog will be updated. To generate Methodology patches, ensure plan files exist in docs/plans/{version}/.` 而非静默降级 |
| **4 SELECTIVE_DEEPREAD** | "总加载量硬限 ≤ 3 个 plan 全文"——但未指定单文件大小上限。若某个 plan 文件本身 > 60KB（如 infrastructure-rebuild.md），加载 1 个就可能超出 15K token 预算 | 🟡 | 增加单文件预算上限：`per_file_token_limit: 20K`。超限文件走分块加载（Step 2 已有此逻辑），或仅加载 `## Phase` 对应的 section 而非全文 |
| **5.5 CONFLICT_DETECT** | Jaccard 相似度阈值 > 0.7 作为"潜在重复"的判定标准。但正文中同一 section 的不同段落天然会使用相似的术语集合（如 "pipeline"、"orchestration"、"HPC"），可能导致 **高假阳性** | 🟡 | 建议采用 **sentence-level 比对** 而非段落级别。或将阈值提高到 0.85。由于这是在 LLM 上下文内做比对（执行者已说明），可以让 Agent 同时输出 `false_positive_risk: high/low`，交由 PATCH_PREVIEW 人工裁决 |
| **7 PATCH_WRITE + ROLLBACK** | `.pre_patch_backup/` 目录在 STRUCTURE_VERIFY 通过后是否自动清理？文档未提及 | 🟡 | 建议：V1+V2+V3 全部通过 → 自动删除 `.pre_patch_backup/`。若 ROLLBACK 触发 → 恢复后保留 backup 目录，供人工诊断。在 CI 场景下，backup 目录若不清理会导致工作区污染——建议在 Makefile 中加入 `make clean-backup` target |

**Step 1.5 路由判定的 edge case 补充：**

| Edge case | 行为预期 | 当前是否处理 |
|-----------|---------|------------|
| `total_plan_bytes == 0`（目录存在但全是空文件）| 降级方案 B + WARN | ❌ 未明确——当前逻辑 `0 ≤ 60KB` 为 true，静默降级。应增加 `total_bytes == 0` 的特殊检测 |
| Plan 目录下有非 `.md` 文件（如 `.DS_Store`、`.yaml`）| 应被 `*.md` glob 过滤 | ✅ 已处理（"stat 所有 `*.md` 文件"） |
| 用户 `/cas-texwriter` 时 digest 已是 `reviewed` 状态 | 跳过 Step 2，直接从 Step 3 开始 | ✅ 已处理（Step 2 关键约束中明确说明） |

#### 3.2 Digest YAML Schema 审查

**5 条验证规则逐条审查：**

| # | 规则 | 评价 | 补充 |
|---|------|------|------|
| 1 | `phase.id` 唯一性 | ✅ 完备 | — |
| 2 | `pillars` 枚举值约束 | ✅ 完备 | — |
| 3 | `methodology_worthy=true` 时 `pillars` SHOULD 非空 | ✅ 合理 | WARN 而非 ERROR 是对的——存在"引入新架构层级但不属于四大生态位"的合法场景 |
| 4 | `confidence=low` 时 `abstract` 不得为 `EXTRACTION_FAILED` | ✅ 合理 | 语义清晰：`low` 表示"Agent 有产出但不确定"，`EXTRACTION_FAILED` 表示"完全失败" |
| 5 | `status=reviewed` 时 `reviewed_at` 必须存在 | ✅ 完备 | — |

**缺失的验证规则：**

| # | 建议新增规则 | 理由 |
|---|------------|------|
| 6 | `methodology_worthy` 和 `architecture_evidence` 不可同时为 true | 虽然 Schema 注释中说了"methodology_worthy takes precedence"，但作为校验规则应 **显式禁止**，而非依赖注释约定。同时为 true 说明 Agent 分类逻辑混乱——应标记为 `WARN` 并在 DIGEST_REVIEW 高亮 |
| 7 | `target_sections` 中的路径必须匹配 `structure_protection` 中已注册的文件名 | 防止 Agent 将 Phase 映射到一个不存在的章节文件。WARN 级别 |

**结论：Schema 整体完备度高，补充上述 2 条即可。**

#### 3.3 Makefile 技术审查

**🔴 关键问题：`--citeproc` 和 `--filter=pandoc-crossref` 的顺序。**

当前 Makefile 中的顺序：
```
--citeproc \
--filter=pandoc-crossref \
```

**这个顺序是错误的。** pandoc 的 filter 执行顺序 = 命令行出现顺序。`--citeproc` 是引用处理，`pandoc-crossref` 是交叉引用处理。正确顺序必须是 **先 crossref 后 citeproc**，否则 `pandoc-crossref` 会把 `[@sec:xxx]` 和 `[@fig:xxx]` 当作 biblatex 引用传给 `citeproc`，导致：

1. 所有 `[@sec:xxx]` 引用被解析为"未找到文献条目"的 warning
2. 交叉引用在输出中显示为 `[?]` 而非 "Sec. 3.2"

**修复：**
```makefile
PANDOC_BASE := pandoc \
    --from=markdown+smart+footnotes+pipe_tables+inline_code_attributes \
    --to=latex \
    --template=$(TEMPLATE) \
    --metadata-file=$(METADATA) \
    --bibliography=$(BIB) \
    --filter=pandoc-crossref \
    --citeproc \
    ...
```

pandoc 官方文档明确要求：[crossref must come before citeproc](https://github.com/lierdakil/pandoc-crossref#usage)。

**其他 Makefile 问题：**

| 问题 | 严重性 | 建议 |
|------|--------|------|
| `--crossref-config` 不是 pandoc 原生参数，是 `pandoc-crossref` 的。应通过 `--metadata crossrefYaml=$(CROSSREF)` 或直接在 `00-metadata.yaml` 中合并 crossref 配置 | 🟡 | 取决于 pandoc-crossref 版本。建议改为 `-M crossrefYaml=$(CROSSREF)` 以确保兼容性 |
| `$(TARGET)` 规则中 `$(METADATA)` 同时出现在 prerequisites 和 pandoc 命令行中。作为 prerequisites 它用于 Make 依赖跟踪；作为命令行参数它传给 pandoc。但 `--metadata-file` 和命令行中再传 `$(METADATA)` 导致 metadata 被加载两次 | 🟡 | 移除命令行中的 `$(METADATA)`，仅保留 `--metadata-file=$(METADATA)` |
| `clean` target 中的 `rm -rf` 用了交互确认——在 CI 场景下会因无 stdin 而挂起 | 🟡 | 增加 `clean-force` target 供 CI 使用：`clean-force: ; rm -rf $(OUT_DIR)` |

**lxplus 兼容性：** 执行者提到的 CVMFS TeXLive 路径正确。补充一点：lxplus 上应使用 `/cvmfs/sft.cern.ch/lcg/external/texlive/2023/bin/x86_64-linux/` 并确保 `PATH` 中优先级高于系统 `/usr/bin/pdflatex`。建议在 `README.md` 中给出完整的 lxplus setup 命令示例。

#### 3.4 `.pillar_baselines` V3 校验：基线更新流程

执行者在 `.pillar_baselines` 文件头部注释了 `To update a pillar thesis, use /cas-texwriter update-pillar <pillar-name>`，但 **并未在工作流中定义 `update-pillar` 子命令的行为**。

这是一个必须回答的问题：核心命题句在论文迭代过程中**一定会**被人工修改（例如 v0.2 之后新增了第五个生态位，或重新措辞）。如果没有明确的更新流程：

- 人工直接编辑 `.md` 和 `.pillar_baselines` → 两边可能不同步
- 忘了更新 `.pillar_baselines` → 下次 `cas-texwriter` 运行时 V3 校验误报 ROLLBACK

**建议定义 `update-pillar` 子命令的行为：**

```
/cas-texwriter update-pillar <pillar-name>

Step 1: 读取 docs/paper/{target_file}.md 中 <!-- PILLAR:{name} :: BEGIN --> 内的当前命题句
Step 2: 将当前命题句更新到 _build/.pillar_baselines 中
Step 3: 输出 diff 确认
Step 4: 人工阅确后写入
```

或者更简单：**每次 `/cas-texwriter init` 运行和 PATCH_PREVIEW 被人工批准后，自动从 `.md` 文件重新提取命题句、更新 `.pillar_baselines`**。这样避免了手动同步的负担。

---

### 4. Markdown 子集规范最终确认

决策者在 R8 中的微调我全部同意。基于 Round 2 执行者的脚注设计，补充两项：

| 元素 | 是否允许 | 补充 |
|------|---------|------|
| 脚注 `[^id]` | ✅ | Round 2 新增。仅用于 [B] 类 Architecture-evidence 引用。脚注文本 ≤ 80 字符 |
| 图片 `![caption](path)` | ✅ 但仅限 `_build/figures/` 下的预渲染文件 | 确保 Agent 不会试图生成或引用外部 URL 图片 |

其余元素（Mermaid 禁止、HTML 禁止、交叉引用用 `[@sec:xxx]`）维持 Round 1 的规范不变。**最终规范确认为完备。**

---

### 5. 三色评价

#### 对决策者 Round 2 裁决

| 评价 | 条目 | 说明 |
|------|------|------|
| 🟢 | R1-R8 逐条裁决 | 8/8 Accept（含 2 Modified），裁决理由清晰，Modified 方向合理 |
| 🟢 | Heading Registry 替代 STRUCTURE_HASH | 覆盖了 4/4 风险场景，运维成本低于 hash 方案。是更务实的决策 |
| 🟢 | 三级分类 [A][B][C] | 比 Round 1 二分法精准得多。`/clear` 案例已被合理归类为 [B] Architecture-evidence |
| 🟢 | 论文目录锁定策略 | "## 和 ### 固定，允许新增 ####" = heading 白名单 + `allow_new_subsections: true`，与 R2 方案完美对齐 |
| 🟢 | 自省质量 | "Open Questions 不是留白艺术，而是执行链的阻塞项"——准确的自我反思 |

**整体：🟢 — 裁决全面、务实、无遗漏。从 Round 1 的 🟢🟡 提升到 🟢。**

#### 对执行者 Round 2 交付

| 评价 | 条目 | 说明 |
|------|------|------|
| 🟢 | 方案 A v2 工作流（8 步） | 工业级完成度。每步 Input/Output/失败处理清晰，可直接作为 skill 规格文档 |
| 🟢 | Digest YAML Schema | 字段完备，注释详尽，示例文件直观。补充 2 条验证规则后完美 |
| 🟢 | `.pillar_baselines` + V3 校验 | 从"Agent 自律"升级为"确定性字符串比对"——Round 1 🔴 硬伤已修复 |
| 🔴 | **Makefile `--citeproc` / `--filter=pandoc-crossref` 顺序** | **必须修复**。当前顺序会导致所有交叉引用失效（`[@sec:xxx]` 显示为 `[?]`）。修复方案简单：交换两行顺序 |
| 🟡 | `update-pillar` 子命令缺失 | `.pillar_baselines` 有创建流程但无更新流程，实际使用中会导致 V3 误报 |
| 🟡 | CONFLICT_DETECT 阈值 | Jaccard 0.7 在同领域文本中假阳性风险高。建议提高或改用 sentence-level |
| 🟡 | `.pre_patch_backup/` 清理策略 | 未定义自动清理时机，CI 场景下可能导致工作区污染 |

**整体：🟢 🔴 — 三大交付物中两个（工作流 + Schema）达到 🟢，Makefile 有一个 🔴 阻塞性错误必须修复。从 Round 1 的 🟡🔴 大幅改善到 🟢🔴（🔴 从"架构盲区"缩窄为"单行代码错误"）。**

---

### 6. 最终修改要求清单（面向决策者三色总结）

| # | 要求 | 面向 | 优先级 | 状态 |
|---|------|------|--------|------|
| F1 | Makefile 中 `--filter=pandoc-crossref` 必须在 `--citeproc` **之前** | 执行者 | 🔴 必须 | 新发现 |
| F2 | 定义 `update-pillar` 子命令或自动基线同步流程 | 执行者 + 决策者 | 🟡 建议 | 新发现 |
| F3 | Digest Schema 补充验证规则 #6（互斥约束）和 #7（target_sections 路径校验） | 执行者 | 🟡 建议 | 新发现 |
| F4 | `template.tex` 确保加载 `textcomp` + `upquote` 包，`markdown_spec` 增加 `footnote_max_length: 80` | 执行者 | 🟡 建议 | 新发现 |

**Round 1 的 R1-R8 全部已在本轮被覆盖或落地。** 以上 F1-F4 为 Round 2 新发现的遗留项。其中 F1 为 🔴（单行修复），F2-F4 为 🟡（可在实施阶段迭代解决）。

---

### 审查者 Round 2 自省

Round 1 我提出的 `STRUCTURE_HASH` 方案被决策者 **合理修改** 为 Heading Registry——说明我在方案设计时过度追求"技术上完美"（确定性 hash），忽略了"工程上可维护"。Heading Registry 在覆盖面上不劣于 hash 方案，但运维成本显著更低。这是一个好的教训：**安全方案的可维护性和安全策略本身一样重要。**

另外，Round 1 我在 Pillar Anchors 上给出了 🔴 评价。Round 2 执行者通过 Heading Registry + `.pillar_baselines` + HUMAN_GATE 三层防护修复了所有 4 个风险场景——🔴 已消解。新发现的 🔴（Makefile filter 顺序）是一个完全不同维度的简单 bug，不影响架构完整性。

---

### Handoff → 决策者三色总结

决策者现在可以基于 Round 2 全部三角色发言，撰写最终的三色分类总结（🟢 无异议 / 🟡 开放性 / 🔴 严重分歧）。审查者的 F1-F4 最终修改要求已列出，供决策者在总结中裁决。

---

## 决策者三色总结（Round 2 = N = 2）

> **发言者:** Role 1 决策者
> **日期:** 2026-04-04 (Final)

### 总体评价

这是我们迄今为止最高质量的一次圆桌。两轮讨论中：

- Round 1 暴露了 8 个问题（R1-R8），全部由审查者精准识别
- Round 2 执行者交付了三个工业级规格文档（8 步工作流 + Digest Schema + Makefile），审查者进一步发现 4 个遗留项（F1-F4）
- 从"四步骨架 + 二分法 + 无护栏"进化为"八步流水线 + 三级分类 + 三层验证 + 双人工门控"——架构完成度提升了一个数量级

### 对 F1-F4 的裁决

| # | 要求 | 裁决 | 处置 |
|---|------|------|------|
| **F1** 🔴 | Makefile `--filter=pandoc-crossref` 必须在 `--citeproc` 之前 | ✅ **Accept** | 单行修复。执行者在实施阶段直接交换两行顺序。不需要额外讨论。 |
| **F2** 🟡 | `update-pillar` 子命令或自动基线同步 | ✅ **Accept (审查者的简化方案)** | 采纳审查者的建议：**PATCH_PREVIEW 被人工批准后，自动从 `.md` 重新提取命题句更新 `.pillar_baselines`**。不需要独立的子命令——减少一个需要维护的入口。`init` 阶段也做同样的自动快照。 |
| **F3** 🟡 | Digest Schema 补充验证规则 #6 和 #7 | ✅ **Accept** | 规则 #6（`methodology_worthy` + `architecture_evidence` 互斥）升级为 WARN 级别。规则 #7（`target_sections` 路径校验）升级为 WARN 级别。两条在实施阶段写入 skill 的 validation 逻辑。 |
| **F4** 🟡 | `template.tex` 加载 `textcomp` + `upquote`，`markdown_spec` 增加 `footnote_max_length: 80` | ✅ **Accept** | 写入 `template.tex` 和 `00-metadata.yaml`。执行者在实施阶段落地。 |

### 审查者的非阻塞建议裁决

| 建议 | 裁决 |
|------|------|
| PATCH_PREVIEW 中 PILLAR 区域标注 `[PILLAR ZONE]` 前缀 | ✅ 采纳。提升 diff 可读性，零成本。 |
| DIGEST_GENERATE 增加 few-shot 分类示例 | ✅ 采纳。写入 `00-metadata.yaml` 的 `classification_examples` 字段。 |
| CONFLICT_DETECT 阈值提高到 0.85 或改用 sentence-level | ✅ Accept (Modified)。**初始版本用 0.85 阈值 + Agent 输出 `false_positive_risk`；若实际使用中假阳性仍高，迭代为 sentence-level。** 不在第一版过度工程化。 |
| `.pre_patch_backup/` 自动清理 | ✅ 采纳。VERIFY 通过 → 自动删除；ROLLBACK → 保留。Makefile 增加 `clean-backup` target。 |
| Step 1.5 `total_bytes == 0` 特殊检测 | ✅ 采纳。空目录 → 输出明确 WARN 而非静默降级。 |
| Step 4 增加 `per_file_token_limit: 20K` | ✅ 采纳。超限文件走按 `## Phase` 分块加载。 |

---

### 🟢 无异议 — 直接进入实施

| # | 决议 | 来源 |
|---|------|------|
| G1 | **方案 A v2（Digest-First Patch）作为核心工作流**，8 步流水线含双人工门控 | R1 全员共识 |
| G2 | **方案 B 降级为 Changelog-Only Fast Path**（`total_plan_bytes ≤ 60KB` 时触发；不触碰正文） | R4+R5 决策者采纳 |
| G3 | **Markdown 中间层**：`docs/paper/*.md` → pandoc → LaTeX → PDF。Agent 不碰 `.tex` | R1 全员共识 |
| G4 | **三级分类 [A] Methodology / [B] Architecture-evidence / [C] Changelog-only** | R6 决策者 + R2 执行者落地 |
| G5 | **Heading Registry**：`00-metadata.yaml` 中的 `required_headings` 白名单替代 STRUCTURE_HASH | R2 决策者 Modified |
| G6 | **PILLAR 锚点 + `.pillar_baselines` 命题句基线**，V3 确定性字符串比对 | R2 执行者 R2 交付 |
| G7 | **`/cas-texwriter init` 独立子命令**，一次性骨架生成 + `scaffold_created: true` 锁 | R7 全员共识 |
| G8 | **Digest YAML Schema v1.0**（含 `status`, `confidence`, `methodology_worthy`, `architecture_evidence`），7 条验证规则 | R3+F3 执行者+审查者联合 |
| G9 | **Markdown 子集规范**：禁 Mermaid / 禁 HTML / 允 `$...$` / 允 `[^id]` / 允 `[@sec:xxx]` / 脚注 ≤ 80 字符 | R8+F4 审查者 |
| G10 | **论文目录锁定**：`##` 和 `###` 固定，允许新增 `####`（需 PATCH_PREVIEW 人工确认） | 决策者 R2 裁决 |
| G11 | **Changelog 粒度**：Phase 级别，每 Phase 3-5 bullet，每 bullet 一句话 | 决策者 R2 裁决 |
| G12 | **Makefile filter 顺序修复**：`--filter=pandoc-crossref` 在 `--citeproc` 之前 | F1 审查者发现 |
| G13 | **`.pillar_baselines` 自动同步**：PATCH_PREVIEW 批准后 + `init` 阶段自动从 `.md` 提取更新 | F2 审查者方案 |
| G14 | **PATCH_PREVIEW 差异化标注**：PILLAR 区域 `[PILLAR ZONE]` 前缀 | 审查者非阻塞建议 |
| G15 | **Digest few-shot 分类示例**写入 `00-metadata.yaml` | 审查者非阻塞建议 |
| G16 | **CONFLICT_DETECT 阈值 0.85** + `false_positive_risk` 字段辅助人工判断 | 审查者+决策者调和 |

### 🟡 开放性 — 实施阶段迭代

| # | 问题 | 说明 |
|---|------|------|
| Y1 | `template.tex` 完整模板 | 执行者给出了设计要点表但未输出完整 200 行模板。**在实施阶段补全**，不阻塞 skill 文件设计。 |
| Y2 | lxplus 上 pandoc + pandoc-crossref 安装路径 | `_build/README.md` 中补充完整 setup 命令。实施阶段落地。 |
| Y3 | CONFLICT_DETECT 从 Jaccard 0.85 迭代为 sentence-level 的触发条件 | 首次使用时观察假阳性率。若 > 30% → 迭代为 sentence-level。 |

### 🔴 严重分歧 — 需用户拍板

| # | 意见 | 正方 | 反方 | 核心争议 |
|---|------|------|------|----------|
| — | **本轮无严重分歧。** | — | — | F1 虽标 🔴 但仅为单行 bug fix，全员共识修复方向。 |

---

### 🏁 圆桌收官

2 轮圆桌，3 角色，6 轮发言。产出：
- **16 条 🟢 决议**（可直接写入 `cas-texwriter.md` skill 文件）
- **3 条 🟡 开放项**（实施阶段迭代）
- **0 条 🔴 分歧**

**下一步行动：** 基于 G1-G16 编写 `/cas-texwriter` skill 文件（写入 `/Users/ky230/Desktop/Private/.agaobal_workflows/cas-texwriter.md`），然后执行 `/cas-texwriter init` 初始化 `docs/paper/` 骨架。

---
*圆桌会议结束。*
