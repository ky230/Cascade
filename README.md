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
- 🤖 **多模型支持** — 11 家 Provider、46+ 模型，自定义 API 抽象层

### 目标环境

直接在 HPC 集群上运行。`git clone` 即用，优先支持 **CERN lxplus**（Condor + GPU）。

## 快速开始

```bash
git clone https://github.com/ky230/Cascade.git
cd Cascade
pip install -e .
cascade --help
```

> 当前版本: v0.3.0

---

## 🔧 模型维护指南

Cascade 的模型配置分布在 **4 个文件** 中。新增模型时必须逐一检查。

### 文件清单

| # | 文件 | 作用 | 何时需要改 |
|---|------|------|-----------|
| 1 | `src/cascade/commands/model/model.py` | `PROVIDER_CATALOG` — 模型列表、显示名、定价。`/model` 命令和 Ctrl+K 模型选择器都读这里 | **始终** |
| 2 | `src/cascade/services/api_config.py` | `get_litellm_kwargs()` — provider → API base/key/model 前缀映射 | **仅新增 Provider** |
| 3 | `src/cascade/commands/rules/context.py` | `_CONTEXT_OVERRIDES` — LiteLLM 查不到的模型的上下文窗口手动覆盖 | **LiteLLM 不支持的模型** |
| 4 | `.env.example` | API Key 环境变量模板 | **仅新增 Provider** |

### 场景 A：新增已有 Provider 的新模型

> 例：给 `glm` 加一个 `glm-6` 模型

**只改 1 个文件：**

#### ① `model.py` — PROVIDER_CATALOG

```python
# src/cascade/commands/model/model.py
# 在对应 provider 的 "models" 列表中追加：
{"id": "glm-6", "label": "GLM-6", "price": "¥X/M in, ¥Y/M out"},
```

#### ② 检查 context window（可选）

```bash
# 测试 LiteLLM 是否认识这个模型
python -c "from litellm import get_model_info; print(get_model_info('openai/glm-6'))"
```

- 如果 LiteLLM **返回了** `max_input_tokens` → 不用改
- 如果 LiteLLM **报错** 或返回 `None` → 在 `context.py` 的 `_CONTEXT_OVERRIDES` 中添加：

```python
# src/cascade/commands/rules/context.py
_CONTEXT_OVERRIDES = {
    ...
    "glm-6": 200_000,  # 手动指定上下文窗口
}
```

### 场景 B：新增全新 Provider

> 例：新增 `baidu` (文心一言)

**改 4 个文件：**

#### ① `model.py` — PROVIDER_CATALOG

```python
# src/cascade/commands/model/model.py
PROVIDER_CATALOG = {
    ...
    "baidu": {
        "display": "Baidu (ERNIE)",
        "env_key": "BAIDU_API_KEY",
        "models": [
            {"id": "ernie-4.5-turbo", "label": "ERNIE 4.5 Turbo", "price": "¥X/M in, ¥Y/M out"},
        ],
    },
}
```

#### ② `api_config.py` — get_litellm_kwargs()

```python
# src/cascade/services/api_config.py
# 在 elif 链中新增：
elif provider == "baidu":
    kwargs["model"] = f"openai/{model_name}"  # 走 OpenAI 兼容接口
    kwargs["api_base"] = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1"
    kwargs["api_key"] = os.getenv("BAIDU_API_KEY")
```

#### ③ `.env.example` — 环境变量模板

```bash
# Baidu (ERNIE) Configuration
BAIDU_API_KEY=your_baidu_api_key_here
```

#### ④ `context.py` — _CONTEXT_OVERRIDES（如果 LiteLLM 不认识）

```python
# src/cascade/commands/rules/context.py
_CONTEXT_OVERRIDES = {
    ...
    "ernie-4.5-turbo": 128_000,
}
```

### Checklist

新增模型后，用以下命令验证：

```bash
# 1. 模型出现在 /model 列表中
cascade
/model

# 2. 能正常对话（API 配置正确）
/model baidu:ernie-4.5-turbo
hello

# 3. /context 显示正确的上下文窗口
/context
```

---

## 项目结构

```
Cascade/
├── docs/walkthrough.md      # 开发日志 (Phase 0-9)
├── docs/plans/              # 迭代计划存档
├── src/cascade/             # 核心源码
│   ├── engine/              # QueryEngine (agentic tool loop)
│   ├── commands/            # 24 个 slash commands
│   ├── services/            # API client, config
│   ├── tools/               # Bash, File, Grep, Glob tools
│   └── ui/                  # Textual TUI
└── tests/                   # 测试
```

## License

MIT

