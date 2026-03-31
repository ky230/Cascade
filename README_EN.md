<p align="center">
  <img src="assets/cascade-logo.png" alt="Cascade" width="280" />
</p>

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
- 🤖 **Multi-Model** — Custom API abstraction supporting GLM, Kimi, MiniMax, and more

### Target Environment

Runs directly on HPC clusters. Clone and go. Primary support for **CERN lxplus** (Condor + GPU).

## Quick Start

```bash
git clone https://github.com/ky230/Cascade.git
cd Cascade
pip install -e .
cascade --help
```

> ⚠️ Early development stage (v0.1.0-dev)

## License

MIT
