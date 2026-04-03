# Roundtable Skill Design — `cas-roundtable.md`

> **Status:** ✅ Approved for implementation (2026-04-03). Roundtable Round 1 concluded.

**Goal:** Create a generic, project-agnostic roundtable skill that enables structured multi-agent retrospectives. Each role self-reflects and provides constructive feedback to collaborators, producing a discussion document with triaged consensus.

**Output:** `YYYY-MM-DD-<topic>-discussion.md`

**Target Location:** `/Users/ky230/Desktop/Private/.agents/global_workflows/cas-roundtable.md`

**Format Reference:** Antigravity workflow `.md` (YAML frontmatter + description + steps)

---

## 1. Skill Identity

```yaml
---
description: 🪑 圆桌会议 — 多 Agent 结构化回顾。3 角色（决策者/执行者/审查者）各自自省 + 互评，产出三色分类 discussion 文档。适用于计划重构、流程复盘、开放问题讨论。
---
```

**Slash command:** `/cas-roundtable`

---

## 2. Prerequisites (用户已完成)

- 已开好 3 个 Agent 窗口，角色已指定 (1-Decision Maker, 2-Executor, 3-Reviewer)
- 有具体的议题要讨论
- 不依赖任何项目特定的 rules 文件（通用 skill）

---

## 3. Skill 启动流程

### Step 1: 收集输入

Agent 向用户询问两项信息：

**A) 议题类型（选择题）：**

| # | 类型 | 示例 |
|---|------|------|
| 1 | 计划重构 | "上一轮 plan.md 写得不够细，需要优化" |
| 2 | Bug 复盘 | "跑完一轮 3-Agent 循环后发现了问题" |
| 3 | 开放问题 | "讨论一下架构方向 / 规则优化" |
| 4 | 其他 | 自由描述 |

**B) 圆桌轮数 `N`：** 默认 1。决策者每次发言 = 一轮结束。

### Step 2: 创建 Discussion 文档

第一个发言的角色负责：
1. 创建 `docs/plans/YYYY-MM-DD-<topic>-discussion.md`
2. 写好自己的完整发言 section
3. **为其他两个角色预创建空 section 框架**（标题 + 提示语 + 交互媒介提示）

---

## 4. Discussion 文档结构

```markdown
# <议题标题> — 圆桌会议 Discussion

> **议题类型:** <计划重构 / Bug 复盘 / 开放问题 / 其他>
> **圆桌轮数:** N = <用户指定>
> **当前轮:** Round <n> / <N>
> **当前进度:** <角色名> 发言中

---

## Role 3 (Reviewer) — 审查者发言

### 自省
> 从自身角度出发，反思自己在本轮协作中的表现。
> 维度参考（按需展开）：
> - **路径准确性**：handoff prompt 中的文件路径是否正确？有无遗漏 UUID？
> - **分类准确性**：🔴/🟡/🟢 分级是否恰当？有无标重或标轻？
> - **append-only 合规**：是否正确追加 Round N 而非覆盖历史？
> - **测试用例质量**：提供的测试用例是否精确命中了关键场景？
> - **上下文压力**：多轮审查后是否出现信息丢失/记忆衰退？

<审查者填写>

### 对决策者的建议 (via plan.md)
> 站在审查者角度评价 plan.md 的质量。
> 交互媒介：plan.md（审查者通过执行者间接接收）
> 维度参考：
> - **验收标准明确度**：审查者能否直接用 plan 来判断 pass/fail？
> - **意图-结果 gap**：plan 说了“做什么”，但有没有说清“做到什么程度算对”？
> - **约束可审计性**：约束是模糊的散文还是可逐条核对的清单？

<审查者填写>

### 对执行者的建议 (via task.md / walkthrough.md / code_review_report.md)
> 基于实际交互中的 task.md、walkthrough.md 和 review report 来评价。
> 维度参考：
> - **Handoff prompt 信息完整度**：修改文件列表、关键约束、上下文是否齐全？
> - **walkthrough 覆盖度**：每个 task 是否都有记录？还是跳过了简单的？
> - **修复响应质量**：收到 🔴 后，修复是否精准到位，还是引入了新问题？
> - **代码质量**：改动是否干净、最小化，还是附带了不相关变更？

<审查者填写>

---

## Role 2 (Executor) — 执行者发言

### 自省
> 反思自己的执行过程。
> 维度参考：
> - **Plan 可执行性**：读 plan.md 后能否直接开始，还是需要大量推理补全？
> - **Review 可操作性**：review report 的修复要求是否足够精确到可直接 coding？
> - **上下文冷启动**：每次新 round 重入时，理解当前状态花了多少成本？
> - **代码质量自评**：修改是否最小化、是否引入了不必要的变更？

<执行者填写>

### 对决策者的建议 (via plan.md)
> 从执行者视角评价 plan.md。
> 维度参考：
> - **粒度**：每个 task 是否是 2-5 分钟可完成的原子操作？
> - **锚点 vs 行号**：定位方式是函数名+代码片段还是纯行号？
> - **依赖顺序**：task 之间的执行顺序是否合理？
> - **验收条件**：每个 task 是否有明确的“做完了”判断标准？

<执行者填写>

### 对审查者的建议 (via code_review_report.md)
> 基于收到的 review report 质量来评价。
> 维度参考：
> - **问题描述精确度**：🔴/🟡 是否附带了具体行号/函数名/代码片段？
> - **修复要求可执行性**：能否直接按 report 改，还是需要猜意图？
> - **分类合理性**：有没有该标 🟢 的被标成了 🔴？
> - **handoff prompt 质量**：从审查者收到的 fix handoff 是否信息完整？

<执行者填写>

---

## Role 1 (Decision Maker) — 决策者发言

> **发言者:** Role 1 决策者 (conversation `ee4426ae-5df6-46ee-9ff6-1076540dd5a2`)
> **基于经验:** `2026-04-03-cascade-md-split` 计划，作为 Decision Maker 主导规划 + 裁决 12 条提案
> **参考上下文:** 前一个决策者 conversation `d47f28f4` 的完整工作轨迹
> **日期:** 2026-04-03

---

### 自省

**Plan 结构：** 遵循了 Goal → Architecture → Tasks 结构，这一点没问题。但我犯了一个**本质性错误**——我把新 `Cascade.md` 的 §1.5 写成了"加载 `Cascade-workflow.md`"，却漏掉了 §1.6"加载 `Cascade-references.md`"。这意味着 Big Three 参考路径文件虽然创建了，但**永远不会被任何规则触发加载**。这是一条断裂的引用链，直到 Round 3 才被审查者发现。

**这个错误的根因不是粗心，而是缺少系统性自检工具。** 我在 plan 中为 3 个文件各写了完整的 code block（Task 1/2/3），但没有回过头画一张依赖图来验证"每个文件是否都被正确引用"。对于跨文件引用关系，仅靠线性阅读 plan 是不够的。我需要一个 **cross-reference checklist**：

```
Cascade.md §1.5 → loads → Cascade-workflow.md  ✅ 有
Cascade.md §1.6 → loads → Cascade-references.md  ❌ 缺失！
Cascade-workflow.md → supplements → Cascade.md  ✅ 声明了
Cascade-references.md → standalone  ✅ 无依赖
```

如果我在提交 plan 前做了这张表，§1.6 缺失会立刻暴露。**这应该成为所有「文件拆分」类 plan 的标准验证步骤。**

**粒度预判：** 这次做对了。因为是纯文档任务，我直接在 plan 中嵌入了完整的 markdown code block（三个文件的全部内容）。执行者反馈这是"最高效的 plan → execute 路径"，基本是"逐字抄写"。**对于文档类任务，"给出最终产物"比"描述要做什么"好 10 倍。** 这应该成为标准范式——但要注意：这个策略仅适用于内容可以被完全预确定的任务（文档、配置、模板）。对于逻辑密集型代码任务，给出最终产物反而可能限制执行者的灵活性。

**审查友好度：** 这是最大的短板。Proposal 整合表仅标了 "✅ Accept" + "Target File"，**没有逐条验收标准**。审查者被迫在 Round 1 自己构建 per-proposal verification checklist。这本应该是我提供的。执行者也指出了这一点（🟡#3 建议）。回顾 plan 中的 Verification Plan，我只写了 `ls -la` 和 `wc -l`——这是**存在性检查**，不是**正确性检查**。一个文件存在且行数对，不代表内容正确。我应该提供：

| 验证层级 | 示例 | 我实际提供的 |
|---------|------|-------------|
| L1: 存在性 | `ls -la` 确认文件创建 | ✅ 有 |
| L2: 结构性 | `wc -l` 确认行数范围 | ✅ 有 |
| L3: 内容性 | `grep "trigger: manual" Cascade-workflow.md` | ❌ 无 |
| L4: 功能性 | 开新对话，触发 §1.5/§1.6，验证加载 | ❌ 无 |

L3 和 L4 的缺失直接导致 §1.6 bug 在 Round 3 才被发现。

**用户需求还原度：** 忠实还原了用户在圆桌讨论中批准的 12 条提案。staging 策略（写到 `ssH-remote-Workspace/2026-04-03/` 而非直接覆盖 `.agents/rules/`）也是用户提出并确认的。但我漏掉了一个隐含需求：用户期望 **deploy 后能立即正常工作**，而 plan 完全没有覆盖这一点。

**总结：** 我的计划在"内容产出"维度是 **A 级**的（完整 code block、staging 策略、12 条提案全覆盖），但在"系统完整性验证"维度是 **C 级**的（引用链断裂、缺少验收标准、缺少功能性 smoke test）。这两个短板都可以通过简单的 checklist 工具避免——不需要更复杂的规划方法论，只需要在提交前多做一步自检。

---

### 对执行者的建议 (via task.md / walkthrough.md)

**忠实度（A+）：** 执行者严格按照 plan 中的 code block 创建了三个文件，没有擅自偏离或"善意发挥"。在 Round 2/3 的修复中，修改精确对应审查者的 Required Fix 代码块，零多余变更。这恰恰验证了"嵌入完整最终产物"策略的有效性——执行者的工作变成了可靠的变量替换，而非创造性写作。

**Brain 文件连续性（平台限制，非执行者过错）：** Round 3 需要跨 UUID 继承 task.md / walkthrough.md，但 Antigravity 的 UUID 隔离机制阻止了直接写入。执行者被迫在新 brain 下重建完整文件并 carry forward 历史内容。这是一个真实的平台限制。执行者的应对策略（手动重建 + carry forward）是当前条件下的最佳方案，但它破坏了 append-only 的审计连续性。**这个问题无法在 skill 层解决，提交为 🟡 由用户决定缓解策略。**

**Handoff 质量（超出模板要求）：** 执行者在 Round 3 的 handoff 中自发添加了"上一轮审查报告路径"——这实际上补偿了模板的不足。这种基于真实需求的自发补充，恰好说明了当前模板的信息字段不够完整。建议将此字段标准化为 `{ADDITIONAL_CONTEXT}` 可选字段（见 🟡 Y4 讨论）。

**staging vs deployed 路径混淆（可预防）：** 执行者在 Round 3 第一次修复时直接修改了 `.agents/rules/` 下的已部署文件（被用户 cancel），第二次才意识到目标应该是 staging 目录。这部分是 plan 的责任——plan 的 staging 策略声明只在头部出现了一次，在 Task 1/2/3 的具体步骤中，文件路径确实指向了 staging 目录，但 **Round 3 的修复指令来自审查者（而非 plan），审查者没有重申 staging 约束**。建议：在 Cascade-workflow.md 的 W4 规则中增加一条——"如果 plan 声明了 staging 策略，所有修改必须在 staging 路径下进行，即使修复来自审查者而非 plan。"

---

## 决策者总结 (仅当 Round n = N 时填写)

> 决策者在阅读所有角色发言后，进行三色分类汇总。
> 本轮 Round = 1 = N，满足总结条件。

### 🟢 无异议 — 直接采纳

| # | 意见 | 来源 | 实施说明 |
|---|------|------|---------|
| G1 | §4 模板 Role 2 自省维度新增 "Brain 文件连续性" | Role 2, 修改建议 #1 | 在 Role 2 自省维度列表末尾追加该条目 |
| G2 | §4 模板 Role 2 "对审查者的建议" 新增 "正向反馈" 维度 | Role 2, 修改建议 #2 | 在 Role 2 对审查者维度列表追加 |
| G3 | §7 Handoff 模板新增 `**前序角色发言摘要:**` 可选字段 | Role 2, 修改建议 #3 | 在模板底部增加可选 block，标注"多轮时填写" |
| G4 | §4 L9 typo 修正：`.agaobal_workflows` → 正确路径 | Role 2, 修改建议 #4 | 修正为实际 global workflows 路径 |
| G5 | §6 交互媒介表新增：「执行者→审查者」via handoff prompt | Role 2, 修改建议 #5 | 追加表格行 |
| G6 | Plan 应嵌入完整最终产物 code block（文档类任务标准范式） | Role 2 对决策者 ✅ + 决策者自省 | 在 §8.2 与 Writing-plans 的关系中增加说明 |
| G7 | Plan 的 Proposal 整合表应增加 "验收标准" 列 | Role 2 对决策者 🟡#3 + 决策者自省 | 三方共识明确，直接升级为 🟢 |
| G8 | Plan 应声明跨文件依赖图（文件拆分类任务必须） | Role 2 对决策者 🟡#2 + 决策者自省 | 决策者自省中已论证必要性，升级为 🟢 |
| G9 | Plan 的 Verification Plan 应覆盖 L1~L4 四个验证层级 | 决策者自省 | 新增。至少覆盖：存在性→结构性→内容性→功能性 |
| G10 | 审查者追加新 Round 时，在旧 Verdict 下标注"已被取代" | Role 2 对审查者 🟡#2 | 实施成本低，防止用户误读历史 Verdict |

### 🟡 开放性（已由用户最终裁决为 🟢）

| # | 意见 | 用户最终定夺 | 实施说明 |
|---|------|------------|---------|
| Y1 | Plan 需增加 "Post-Deployment Smoke Test" 环节 | **采纳** (方案 C) | 与 Iteration Loop Step 4 合并。要求决策者在 plan 中写好 test cases，用户 Manual CLI Test 时执行。 |
| Y2 | UUID 隔离导致审计链断裂 | **采纳** (方案 A) | 在 handoff 模板中增加可选字段 `**前轮 Brain 文件:**`。不改存储机制，逻辑串联。 |
| Y3 | Review report 🟡 内应做 sub-ranking | **条件采纳** | 在 `cas-roundtable` 中不强求强规，但建议："当同类别问题 ≥3 个时，推荐使用 🟡-High/🟡-Low 排序"。 |
| Y4 | Handoff 模板预留 `{ADDITIONAL_CONTEXT}` | **合并采纳** | 将 G3 和 Y4 统一为 `**补充上下文:**` 模块，容纳摘要和额外情况。 |

### 🔴 严重分歧 — 需用户拍板

| # | 意见 | 正方 | 反方 | 核心争议 |
|---|------|------|------|----------|
| — | 本轮无严重分歧，全项决议达成 | — | — | — |
```

---

## 5. 轮次与流转规则

### 轮次计算
- **一轮** = 流转到决策者发言为止（决策者发言 = 本轮结束）
- `3→2→1` = 1 轮 ✅
- `1→2→3→1` = 1 轮 ✅（决策者发言两次，第二次为总结）
- `2→3→1` = 1 轮 ✅
- 不限制起始角色，但**必须以决策者结束**

### 进度追踪
每次 handoff 时更新文档头部的元数据：

```markdown
> **当前轮:** Round 1 / 1
> **当前进度:** Role 2 (Executor) 发言中
```

### 决策者总结的触发条件
**仅当以下条件均满足时**，决策者才填写三色总结：
1. 当前轮 `n` ≥ 预设轮数 `N`
2. 其他两个角色都已提交发言
3. 决策者自己已完成自省 + 对执行者的建议

---

## 6. 语气与行为约束

### 建设性原则
- ✅ "建议 plan.md 增加锚点代替行号，这样避免行号漂移"
- ❌ "plan.md 写得太差了，行号全是错的"

### 交互媒介原则
每个角色只通过**实际交互过的文件**来评价对方：

| 评价方 → 被评方 | 交互媒介（必须引用） |
|----------------|---------------------|
| 决策者 → 执行者 | task.md, walkthrough.md |
| 执行者 → 决策者 | plan.md |
| 执行者 → 审查者 | code_review_report.md |
| 审查者 → 决策者 | plan.md（间接接收） |
| 审查者 → 执行者 | task.md, walkthrough.md, code_review_report.md |

### 禁止事项
- ❌ 人身攻击或情绪化表述
- ❌ 评价未直接交互的方面（如审查者不应评价决策者的用户沟通方式）
- ❌ 在 discussion 中直接修改代码或规则文件

---

## 7. Handoff Prompt 模板

第一个角色发言完毕后，输出 handoff prompt（plain code block）给下一个角色：

```
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
```

---

## 8. 与上游 Skill 的深度集成

### 8.1 与 Brainstorming 的关系

Roundtable 是 Brainstorming 的**多角色变体**。两者共享同一套核心原则：

| Brainstorming 原则 | Roundtable 映射 |
|-------------------|----------------|
| Explore project context | 每个角色先阅读交互媒介文件（plan/task/walkthrough/report）|
| Ask questions one at a time | 每个角色逐维度自省，再逐维度评价他人 |
| Propose 2-3 approaches | 每条建议附具体改进方案（不只是指出问题）|
| Present design, get approval | 决策者三色汇总 → 用户审批 🟡/🔴 |
| HARD-GATE: no code before approval | **HARD-GATE: 圆桌未完成前，不得修改任何规则/代码文件** |

**关键差异：** Brainstorming 是 1 Agent 与用户对话；Roundtable 是 3 Agent 通过 discussion.md 异步接力。

### 8.2 与 Writing-plans 的关系

Discussion 文档结构借鉴了 Writing-plans 的文档规范：

| Writing-plans 规范 | Discussion 文档映射 |
|-------------------|--------------------|
| 文档头部：Goal + Architecture + Tech Stack | 文档头部：议题类型 + 轮数 + 当前进度 |
| 每个 Task 有精确路径和代码片段 | 每条建议必须引用具体的交互文件和具体问题 |
| Bite-sized granularity (2-5 min) | 每个维度的发言控制在 3-5 句话，不写散文 |
| 保存至 `docs/plans/YYYY-MM-DD-*.md` | 同样保存至 `docs/plans/YYYY-MM-DD-*-discussion.md` |

**终态衍接：** 如果圆桌会议产生的 🟢 action items 需要执行，用户可调用 `/sp-writing-plans` 将其转化为实施计划。

---

## 9. 完整流程图

```text
[用户提出议题 + 指定轮数 N]
      ↓
[任意角色先开始] --> 创建 discussion.md + 填写自己的 section + 搭建其他角色框架
      ↓ (Handoff Prompt)
[下一个角色] --> 阅读已有发言 + 填写自己的 section
      ↓ (Handoff Prompt)
[再下一个角色] --> 阅读已有发言 + 填写自己的 section
      ↓
      |-- (当前角色 ≠ 决策者) → 继续流转
      |-- (当前角色 = 决策者 且 n < N) → n++ → 新一轮
      |-- (当前角色 = 决策者 且 n = N) ↓
      ↓
[决策者三色总结: 🟢无异议  🟡开放  🔴分歧]
      ↓
[交付用户] → 用户对 🟡/🔴 做最终裁决
```

---

## Resolved Decisions

| # | 问题 | 决定 |
|---|------|------|
| 1 | Discussion 文档位置 | 用户自行指定，默认 `docs/plans/` |
| 2 | 多轮累积方式 | Append-only（追加 `### Round 2 自省`，不覆盖） |
| 3 | Skill 文件体量 | 不限制，完整表述优先 |

---

## Role 2 (Executor) — 圆桌发言

> **发言者:** Role 2 执行者 (conversation `9b15a0d8-3618-4176-8079-75875393745c`)
> **基于经验:** `2026-04-03-cascade-md-split` 计划，3 轮 Executor↔Reviewer 协作
> **日期:** 2026-04-03

---

### 自省

**做得好的：**
- 计划中给出了完整的 markdown code block，执行基本是"逐字抄写"，零歧义，零推理补全。这是我经历过的**最高效的 plan → execute 路径**。
- 审查报告的精确度非常高。Round 1/2 的 🟡 都附带了具体行号、原因分析和 Required Fix 代码块，我基本不需要猜意图，直接按修。

**痛点：**

1. **Brain 文件 UUID 隔离墙。** Round 3 时我是一个新的 agent 实例（UUID `9b15a0d8`），但 task.md 和 walkthrough.md 属于前一个执行者（UUID `c7f845fa`）。Antigravity 不允许跨 UUID 写文件，我直接撞了 `files must be written to the correct artifact directory` 错误。最终只能在自己的 brain 下重建完整的 task.md / walkthrough.md，**手动 carry forward 历史内容**。这破坏了 append-only 的审计连续性。

2. **staging 目录 vs 已部署文件的双重追踪。** 用户先 deploy 了 staging → `.agents/rules/`，但 Round 3 修复需要改 staging 而非 deployed。我第一次直接对 `.agents/rules/` 动手（被用户 cancel），第二次才意识到要改 staging。**handoff prompt 里必须明确 staging vs. deployed 的目标路径**，否则执行者会混淆。

3. **Handoff prompt 模板外的附加信息。** 我在生成 Role 2→3 handoff 时，不自觉地添加了"上一轮审查报告路径"——因为审查者需要对照自己 Round 1/2 的历史。但模板里没这个字段。模板应该预留一个 **`{ADDITIONAL_CONTEXT}`** 可选字段。

---

### 对决策者的建议 (via plan.md)

**✅ 做得好的：**
- **Plan 中直接嵌入完整 markdown code block** 是这次最成功的设计决策。三个 Task 各有一个完整代码块，我作为执行者直接"逐字写入"，零歧义。这比"描述做什么"高效 10 倍——**直接告诉了执行者"最终文件长什么样"**。对于纯文档类任务，这应该成为 plan 的标准范式。
- **Staging 策略**（写到 `ssH-remote-Workspace/2026-04-03/` 而非直接覆盖 `.agents/rules/`）是一个深思熟虑的安全决策。避免了"执行者改掉了自己脚下的 always_on 规则"这种自反性灾难。

**🟡 可以改进的：**

1. **Plan 缺少"部署后 smoke test"环节。** 计划的 Verification Plan 只有 `ls -la` 和 `wc -l`——检查文件存在和行数。但 Round 3 的两个 🟡（§1.6 trigger chain 缺失、模板字段不足）都是 **deploy 后才暴露的功能性问题**。建议未来的 plan 增加：

   > **Post-Deployment Smoke Test:**
   > - 开新对话，验证 §1.5 smart init 是否生效
   > - 触发 3-Agent Workflow，确认 handoff 模板变量完整
   > - 提到"对齐 Claude Code"，确认 §1.6 是否触发 references 加载

2. **依赖关系未显式声明。** Task 1/2/3 看起来是独立的（三个文件各写各的），但实际上 **Task 1 的 §1.5 引用了 Task 2 的文件名**（`Cascade-workflow.md`），且 Round 3 暴露了 **Task 1 应该有 §1.6 引用 Task 3 的文件名**（`Cascade-references.md`）。这种跨文件引用关系如果在 plan 中用一张简单的依赖图标注，审查者可能在 Round 1 就能发现 §1.6 缺失：

   ```
   Cascade.md §1.5 → loads → Cascade-workflow.md
   Cascade.md §1.6 → loads → Cascade-references.md  ← 当时缺失
   ```

3. **Plan 的 Proposal 整合表缺少一列："验收标准"。** 每个 Proposal 只标了 "✅ Accept" + "Target File"，没说"怎么判断这个 proposal 被正确整合了"。审查者在 Round 1 report 中自己构建了 per-proposal verification checklist——这本应该是决策者在 plan 里提供的。建议加一列：

   | # | Proposal | Decision | Target File | **验收标准** |
   |---|----------|----------|-------------|-------------|
   | 1A | Hardcoded templates | ✅ Accept | `Cascade-workflow.md` | **3 个 template 各含指定变量，plain code block** |

---

### 对审查者的建议 (via code_review_report.md)

**✅ 做得好的：**
- **Per-task audit 表格**——每个 Task 一张表，每个 Proposal 一行，Status 列一目了然。这是我见过的"最好审计"的 review report 格式。**强烈建议在 roundtable skill 中把这种格式推荐为 best practice。**
- **Round 3 的 🟡 发现质量极高**——`§1.6 trigger chain` 是一个典型的"正确但不完整"问题，纯看代码很难发现，需要从系统整体的角度审视。审查者做到了。
- **Required Fix 直接给出可粘贴的代码块**——执行者完全不需要猜格式，直接 apply。

**🟡 可以改进的：**

1. **Round 3 的两个 🟡 严重程度不同，但都标了 🟡。** `§1.6 trigger chain` 缺失是一个**功能性缺陷**（references 永远不会被加载），而 `Role 3→2 template enrichment` 更像是**便利性改进**（缺少字段但不影响功能）。建议审查者在同一严重级别内再做 **sub-ranking**（如 🟡-High / 🟡-Low），帮决策者优先排序。

2. **Review report 的 "Verdict" 段落出现了两次**（Round 2 末尾一次 "Ready for Deployment 🚀"，Round 3 末尾又一次）。虽然符合 append-only 原则，但用户扫读时容易被第一个 "🚀" 误导以为已完事。建议在追加新 Round 时，在旧 Verdict 下加一行：`> ⚠️ 此 Verdict 已被 Round 3 Review 取代，请见下方。`

---

### 对设计文档的具体修改建议

以下是我建议对本设计文档模板进行的 5 项改进：

**1. §4 模板 → Role 2 自省维度新增：**

> - **Brain 文件连续性**：跨 round / 跨 agent 实例时，task.md 和 walkthrough.md 的历史是否完整继承？有无因 UUID 隔离导致的信息断层？

**2. §4 模板 → Role 2 "对审查者的建议" 维度新增：**

> - **正向反馈**：审查报告中是否有"✅ 做得好"的标注？纯挑刺式 report 会让执行者陷入"只有问题、没有确认"的不确定感。

**3. §7 Handoff 模板新增可选字段（多轮圆桌时减少冷启动成本）：**

```
**前序角色发言摘要:**（多轮时填写）
- Role {Y}: {ONE_LINE_SUMMARY}
- Role {Z}: {ONE_LINE_SUMMARY}
```

**4. §4 L9 typo 修正：**

`.agaobal_workflows` → 应为正确的 global workflows 路径

**5. §6 交互媒介表新增一行：**

| 评价方 → 被评方 | 交互媒介（必须引用） |
|----------------|---------------------|
| 执行者 → 审查者 | handoff prompt 本身（prompt 质量也是交互产物） |
