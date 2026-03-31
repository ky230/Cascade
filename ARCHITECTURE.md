# Cascade: Architecture & Memory Document

> **AI Instruction:** Read this file at the start of every session to establish global context. Update this file whenever core architectural decisions, abstractions, or workflows change.

## 1. Project Overview
**Cascade** is a Python-based agentic CLI framework designed for High-Energy Physics (HEP) workflow orchestration. It connects local LLM planning with remote HPC cluster execution.

## 2. Core Architecture
- **Language**: Python (asyncio-first)
- **Target Environment**: Direct execution on HPC clusters (e.g., CERN `lxplus`, PKU `ab-node05`), leveraging Condor and GPUs.
- **Parallelism Strategy**: `tmux` backend for running decoupled agentic tasks in parallel terminal panes.
- **LLM Integration**: Custom abstraction layer designed to support multiple models (initially GLM-5.1), decoupling the framework from specific API constraints like OpenAI/Anthropic.

## 3. Harness Engineering Patterns
Cascade implements the five core patterns of harness engineering:
1. **Generator**: Creates configuration files, datacards, and submission scripts from templates (e.g., MadGraph generation).
2. **Tool Wrapper**: Standardizes interfaces to legacy HEP CLI tools (`combine`, `ROOT`, `mg5_aMC`).
3. **Pipeline**: Orchestrates sequential dependencies (e.g., Generation -> Simulation -> Analysis -> Stat Inference).
4. **Reviewer**: Analyzes outputs (e.g., GoF test results, cutflow yields) and decides whether to proceed or trigger a fallback.
5. **Inversion**: Pauses execution to actively query the human physicist for missing topological parameters or critical decisions.

## 4. Memory Management Rule
- **Long-term/Global context**: Maintain and update `ARCHITECTURE.md` (this file).
- **Short-term/Task context**: Save atomic implementation plans to `docs/plans/YYYY-MM-DD-<feature>.md`.
- **Changelog**: Use `git log` and descriptive commit messages for precise diff history.
