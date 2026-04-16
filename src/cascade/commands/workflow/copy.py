from cascade.commands.base import BaseCommand, CommandContext
import subprocess
import platform
import os
from datetime import datetime


class CopyCommand(BaseCommand):
    """Copy AI response to clipboard.

    Reference: claude-code src/commands/copy/copy.tsx (371 lines)
    Claude Code impl: collectRecentAssistantTexts() extracts up to 20
    assistant messages newest-first. extractCodeBlocks() uses marked.lexer()
    to parse Markdown code blocks. CopyPicker JSX shows interactive selector
    (Full response / individual code blocks / "Always copy full").
    setClipboard() uses OSC 52 terminal protocol. writeToFile() writes
    fallback to /tmp/claude/response.md. Supports /copy N to reach back.
    Cascade impl: simplified — copies full response text via subprocess
    (pbcopy on macOS, xclip on Linux). No code block picker, no OSC 52.
    Retains /copy N parameter and /tmp/cascade/ file fallback.
    """
    name = "copy"
    description = "Copy last AI response to clipboard"
    category = "Workflow"

    COPY_DIR = os.path.join("/tmp", "cascade")

    async def execute(self, ctx: CommandContext, args: str) -> None:
        # Collect assistant messages (ref: collectRecentAssistantTexts)
        assistant_msgs = [
            m for m in ctx.engine.messages
            if m.get("role") == "assistant"
        ]
        if not assistant_msgs:
            await ctx.output_rich("[dim]No assistant message to copy.[/dim]")
            return

        # /copy N — reach back N messages (ref: copy.tsx L341-L355)
        age = 0
        if args.strip():
            try:
                n = int(args.strip())
                if n < 1:
                    raise ValueError
                if n > len(assistant_msgs):
                    await ctx.output_rich(
                        f"[dim]Only {len(assistant_msgs)} assistant "
                        f"messages available.[/dim]"
                    )
                    return
                age = n - 1
            except ValueError:
                await ctx.output_rich(
                    "[dim]Usage: /copy [N] where N is 1 (latest), 2, 3, …[/dim]"
                )
                return

        # Get text from the target message
        msg = assistant_msgs[-(age + 1)]
        text = str(msg.get("content", ""))

        # Copy to clipboard (ref: setClipboard -> OSC 52 in Claude Code)
        copied = self._copy_to_clipboard(text)

        # File fallback (ref: writeToFile -> /tmp/claude/response.md)
        file_path = self._write_fallback(text)

        char_count = len(text)
        line_count = text.count("\n") + 1

        lines = []
        if copied:
            lines.append(
                f"[#00d7af]Copied to clipboard "
                f"({char_count} chars, {line_count} lines)[/#00d7af]"
            )
        if file_path:
            lines.append(f"[dim]Also written to {file_path}[/dim]")
        elif not copied:
            lines.append(
                "[red]Failed to copy — clipboard not available, "
                "no fallback file written.[/red]"
            )
        await ctx.output_rich("\n".join(lines))

    def _copy_to_clipboard(self, text: str) -> bool:
        """Copy text to system clipboard via subprocess."""
        try:
            if platform.system() == "Darwin":
                p = subprocess.run(
                    ["pbcopy"], input=text.encode(), timeout=5
                )
                return p.returncode == 0
            else:  # Linux
                p = subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input=text.encode(), timeout=5
                )
                return p.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _write_fallback(self, text: str) -> str | None:
        """Write to /tmp/cascade/response.md as fallback."""
        try:
            os.makedirs(self.COPY_DIR, exist_ok=True)
            path = os.path.join(self.COPY_DIR, "response.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            return path
        except OSError:
            return None
