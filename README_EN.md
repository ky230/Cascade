


https://github.com/user-attachments/assets/780a505e-a97a-4c7f-896f-e62b8f76f626


<p align="center">
  <strong>LLM-Powered Workflow Orchestration for High-Energy Physics</strong>
</p>

<p align="center">
  <a href="README.md">🇨🇳 中文</a> · <a href="README_EN.md">🇬🇧 English</a>
</p>

---

## What is Cascade?

**Cascade** is a Python CLI agent framework built for experimental High-Energy Physics (HEP), following modern harness engineering patterns. It combines LLM planning with HPC cluster execution (e.g., CERN lxplus) to automate physics analysis pipelines.

### Core Design

- 🔗 **Pipeline Orchestration** — Sequential stages with intra-stage parallelism (tmux)
- 🔧 **Tool Wrapper** — Unified interfaces for `MadGraph`, `ROOT`, `Combine`, etc.
- 📝 **Generator** — Template-based config cards and Condor submission scripts
- ✅ **Reviewer** — Automated cross-section, cutflow, and GoF quality checks
- ❓ **Inversion** — Actively queries the physicist when critical parameters are missing
- 🤖 **Multi-Model** — 11 providers, 46+ models via custom API abstraction layer

### Target Environment

Runs directly on HPC clusters. Clone and go. Primary support for **CERN lxplus** (Condor + GPU).

## Quick Start

```bash
git clone https://github.com/ky230/Cascade.git
cd Cascade
pip install -e .
cascade --help
```

> Current version: v0.3.0

---

## 🔧 Model Maintenance Guide

Cascade's model configuration is spread across **4 files**. Check each one when adding models.

### File Checklist

| # | File | Purpose | When to modify |
|---|------|---------|---------------|
| 1 | `src/cascade/commands/model/model.py` | `PROVIDER_CATALOG` — model list, display names, pricing. Read by `/model` command and Ctrl+K picker | **Always** |
| 2 | `src/cascade/services/api_config.py` | `get_litellm_kwargs()` — provider → API base/key/model prefix mapping | **New provider only** |
| 3 | `src/cascade/commands/rules/context.py` | `_CONTEXT_OVERRIDES` — manual context window overrides for models LiteLLM doesn't know | **LiteLLM-unsupported models** |
| 4 | `.env.example` | API key environment variable template | **New provider only** |

### Scenario A: Add a new model to an existing provider

> Example: add `glm-6` to the `glm` provider

**Modify 1 file only:**

#### ① `model.py` — PROVIDER_CATALOG

```python
# src/cascade/commands/model/model.py
# Append to the provider's "models" list:
{"id": "glm-6", "label": "GLM-6", "price": "¥X/M in, ¥Y/M out"},
```

#### ② Check context window (optional)

```bash
# Test if LiteLLM recognizes the model
python -c "from litellm import get_model_info; print(get_model_info('openai/glm-6'))"
```

- If LiteLLM **returns** `max_input_tokens` → no changes needed
- If LiteLLM **errors** or returns `None` → add to `_CONTEXT_OVERRIDES` in `context.py`:

```python
# src/cascade/commands/rules/context.py
_CONTEXT_OVERRIDES = {
    ...
    "glm-6": 200_000,  # manually specify context window
}
```

### Scenario B: Add a completely new provider

> Example: add `baidu` (ERNIE)

**Modify 4 files:**

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
# Add to the elif chain:
elif provider == "baidu":
    kwargs["model"] = f"openai/{model_name}"  # OpenAI-compatible API
    kwargs["api_base"] = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1"
    kwargs["api_key"] = os.getenv("BAIDU_API_KEY")
```

#### ③ `.env.example` — Environment variable template

```bash
# Baidu (ERNIE) Configuration
BAIDU_API_KEY=your_baidu_api_key_here
```

#### ④ `context.py` — _CONTEXT_OVERRIDES (if LiteLLM doesn't recognize it)

```python
# src/cascade/commands/rules/context.py
_CONTEXT_OVERRIDES = {
    ...
    "ernie-4.5-turbo": 128_000,
}
```

### Verification Checklist

After adding a model, verify with:

```bash
# 1. Model appears in /model list
cascade
/model

# 2. Can chat normally (API config is correct)
/model baidu:ernie-4.5-turbo
hello

# 3. /context shows correct context window
/context
```

---

## Project Structure

```
Cascade/
├── docs/walkthrough.md      # Development log (Phase 0-9)
├── docs/plans/              # Iteration plan archives
├── src/cascade/             # Core source
│   ├── engine/              # QueryEngine (agentic tool loop)
│   ├── commands/            # 24 slash commands
│   ├── services/            # API client, config
│   ├── tools/               # Bash, File, Grep, Glob tools
│   └── ui/                  # Textual TUI
└── tests/                   # Tests
```

## License

MIT

