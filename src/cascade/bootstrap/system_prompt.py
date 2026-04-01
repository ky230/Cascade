from cascade.bootstrap.setup import detect_environment

def build_system_prompt(custom_prompt: str | None = None) -> str:
    env = detect_environment()
    base = f"""You are Cascade, an AI assistant for High-Energy Physics workflows.

Environment:
- Python: {env['python_version']}
- Platform: {env['platform']}
- CWD: {env['cwd']}
- ROOT available: {env['has_root']}
- CMSSW available: {env['has_cmssw']}
- HTCondor available: {env['has_condor']}
- Host: {env['hostname']}

You have access to tools for file operations, shell commands, and HEP-specific tasks.
Always explain what you plan to do before executing tools.
"""
    if custom_prompt:
        base += f"\n\nAdditional Instructions:\n{custom_prompt}"
    return base
