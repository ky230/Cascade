"""Rules file management command.

Reference: claude-code src/commands/memory/memory.tsx (90 lines)
Claude Code impl: type='local-jsx'. Renders JSX MemoryFileSelector
for interactive file picking. Opens selected file in $VISUAL/$EDITOR.
Claude Code name: /memory. Cascade renamed to /rules because
CASCADE.md contains project rules/instructions, not conversation memory.
Cascade impl: Textual OptionList for file selection + TextArea
inline editor (mouse-friendly, no vim/nano required). Hot-reloads
system prompt after save so changes take effect immediately.
"""
import os
from cascade.commands.base import BaseCommand, CommandContext
from cascade.bootstrap.system_prompt import CASCADE_MD_PATHS


class RulesCommand(BaseCommand):
    """Edit CASCADE.md project rules with inline editor.

    Reference: claude-code src/commands/memory/memory.tsx (90 lines)
    Claude Code: JSX MemoryFileSelector → $VISUAL/$EDITOR (vim/nano).
    Cascade: Textual OptionList → TextArea inline editor + hot-reload.
    """
    name = "rules"
    description = "Edit CASCADE.md project rules"
    category = "Rules"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        # Build file list with status
        files = []
        for level, path_fn in CASCADE_MD_PATHS:
            path = path_fn()
            exists = os.path.isfile(path)
            size = os.path.getsize(path) if exists else 0
            files.append({
                "level": level,
                "path": path,
                "exists": exists,
                "size": size,
            })

        # Push the editor screen onto the Textual screen stack
        from cascade.commands.rules.editor_screen import RulesEditorScreen
        await ctx.repl.push_screen(RulesEditorScreen(files, ctx.engine))
