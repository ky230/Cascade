import os
from cascade.bootstrap.setup import detect_environment


# CASCADE.md search paths (mirrors Claude Code's CLAUDE.md hierarchy)
# Reference: claude-code src/utils/claudemd.ts getMemoryFiles()
CASCADE_MD_PATHS = [
    ("project", lambda: os.path.join(os.getcwd(), "CASCADE.md")),
    ("project", lambda: os.path.join(os.getcwd(), ".cascade", "CASCADE.md")),
    ("user",    lambda: os.path.expanduser("~/.cascade/CASCADE.md")),
    ("global",  lambda: os.path.expanduser("~/.config/cascade/CASCADE.md")),
]


def get_cascade_md_files() -> list[dict]:
    """Discover all CASCADE.md files at project/user/global levels.

    Reference: claude-code src/utils/claudemd.ts getMemoryFiles()
    Returns list of {"type": str, "path": str, "content": str}.
    """
    found = []
    for level, path_fn in CASCADE_MD_PATHS:
        path = path_fn()
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                if content.strip():
                    found.append({"type": level, "path": path, "content": content})
            except OSError:
                pass
    return found


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
    # Load CASCADE.md rules into system prompt
    cascade_files = get_cascade_md_files()
    for cf in cascade_files:
        base += f"\n\n# Rules ({cf['type']}: {cf['path']})\n{cf['content']}"

    if custom_prompt:
        base += f"\n\nAdditional Instructions:\n{custom_prompt}"
    return base
