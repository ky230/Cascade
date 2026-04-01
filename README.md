<!-- TODO: 用户自行录屏后通过 GitHub 网页端上传 -->


https://github.com/user-attachments/assets/1b2cf25c-f72c-44da-9da9-26d12bad0602



<p align="center">
  <strong>LLM 驱动的高能物理工作流编排框架</strong>
</p>

<p align="center">
  <a href="README.md">🇨🇳 中文</a> · <a href="README_EN.md">🇬🇧 English</a>
</p>

---

## 什么是 Cascade？

**Cascade** 是一套面向实验高能物理 (HEP) 的 Python CLI Agent 框架，基于现代 Harness Engineering 思想构建。它将大语言模型 (LLM) 的规划能力与 HPC 集群（如 CERN lxplus）的算力结合，自动化物理分析流水线。

### 核心设计

- 🔗 **Pipeline 编排** — 阶段串行、阶段内并行（tmux 多窗格）
- 🔧 **Tool Wrapper** — 统一封装 `MadGraph`、`ROOT`、`Combine` 等 HEP 工具
- 📝 **Generator** — 从模板生成配置卡、Condor 提交脚本
- ✅ **Reviewer** — 自动检查截面、cutflow、GoF 等输出质量
- ❓ **Inversion** — 缺少关键参数时主动向物理学家提问
- 🤖 **多模型支持** — 自定义 API 抽象层，支持 GLM、Kimi、MiniMax 等

### 目标环境

直接在 HPC 集群上运行。`git clone` 即用，优先支持 **CERN lxplus**（Condor + GPU）。

## 快速开始

```bash
git clone https://github.com/ky230/Cascade.git
cd Cascade
pip install -e .
cascade --help
```

> ⚠️ 项目处于早期开发阶段 (v0.1.0-dev)

## 项目结构

```
Cascade/
├── ARCHITECTURE.md          # 全局架构文档 (AI 记忆区)
├── docs/plans/              # 迭代计划存档
├── src/cascade/             # 核心源码 (开发中)
│   ├── core/                # Tool / Engine 抽象
│   └── api/                 # LLM 客户端接口
└── tests/                   # 测试
```

## License

MIT
