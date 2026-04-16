from cascade.commands.base import BaseCommand, CommandContext
import json
import os
from datetime import datetime


class ExportCommand(BaseCommand):
    """Export conversation to file.

    Reference: claude-code src/commands/export/export.tsx
    Claude Code impl: 91 lines, supports txt export with ExportDialog,
    auto-generated filenames from first prompt, sanitizeFilename().
    Cascade impl: JSON export with auto-generated filenames.
    """
    name = "export"
    description = "Export conversation to file"
    category = "Session"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        messages = ctx.engine.messages
        if not messages:
            await ctx.output_rich("[dim]No messages to export.[/dim]")
            return

        if args.strip():
            filepath = args.strip()
        else:
            # Auto-generate filename (ref: Claude Code's formatTimestamp)
            ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
            # Extract first prompt summary (ref: extractFirstPrompt)
            first_user = next(
                (m for m in messages if m.get("role") == "user"), None
            )
            suffix = ""
            if first_user:
                content = str(first_user.get("content", ""))[:50]
                # Sanitize (ref: sanitizeFilename)
                suffix = "".join(
                    c if c.isalnum() or c in " -" else ""
                    for c in content
                ).strip().replace(" ", "-")[:30]
            filename = f"{ts}-{suffix}.json" if suffix else f"conversation-{ts}.json"
            filepath = os.path.join(os.getcwd(), filename)

        # Ensure .json extension
        base, ext = os.path.splitext(filepath)
        if ext.lower() != ".json":
            filepath = base + ".json"

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(messages, f, indent=2, ensure_ascii=False)
            msg_count = len(messages)
            await ctx.output_rich(
                f"[#00d7af]Exported {msg_count} messages to {filepath}[/#00d7af]"
            )
        except OSError as e:
            await ctx.output_rich(f"[red]Export failed: {e}[/red]")
