"""Context window usage visualization.

Reference: claude-code src/commands/context/context-noninteractive.ts (326 lines)
Claude Code impl: collectContextData() -> analyzeContextUsage() -> Markdown table.
Precise token counting via microcompactMessages + model tokenizer.
Shows categories: System prompt, Tools, Conversation, Memory, MCP, Skills, Agents.
Cascade impl: STUB. Uses rough char/4 estimation. Missing:
- analyzeContextUsage engine (precise tokenization)
- microcompactMessages (context compression stats)
- MCP tools / Skills / Agents token breakdown
These will be implemented when the full token tracking infrastructure
is built (planned in v0.4.0 Phase 0 Task 8 / long-term plan Phase 2+5).
"""
from cascade.commands.base import BaseCommand, CommandContext


class ContextCommand(BaseCommand):
    """Show context window usage with rough estimation.

    Reference: claude-code src/commands/context/context-noninteractive.ts (326 lines)
    Claude Code: precise tokenization via analyzeContextUsage().
    Cascade: STUB — char/4 estimation until token tracking infra is built.
    """
    name = "context"
    description = "Show context window usage (stub: rough estimates)"
    category = "Rules"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        messages = ctx.engine.messages
        model_name = ctx.engine.client.model_name

        # Categorize message chars (rough estimation)
        user_chars = sum(
            len(str(m.get("content", "")))
            for m in messages if m.get("role") == "user"
        )
        assistant_chars = sum(
            len(str(m.get("content", "")))
            for m in messages if m.get("role") == "assistant"
        )
        system_chars = sum(
            len(str(m.get("content", "")))
            for m in messages if m.get("role") == "system"
        )
        tool_chars = sum(
            len(str(m.get("content", "")))
            for m in messages if m.get("role") == "tool"
        )

        total_chars = user_chars + assistant_chars + system_chars + tool_chars
        total_tokens = total_chars // 4
        max_tokens = self._estimate_max_tokens(model_name)
        pct = min(100.0, (total_tokens / max_tokens * 100)) if max_tokens > 0 else 0

        # Progress bar
        bar_width = 40
        filled = int(bar_width * pct / 100)
        bar_color = "green" if pct < 60 else "yellow" if pct < 85 else "red"
        bar = (
            f"[{bar_color}]{'█' * filled}[/{bar_color}]"
            f"[dim]{'░' * (bar_width - filled)}[/dim]"
        )

        lines = [
            "[bold]Context Usage[/bold]  [dim](stub: rough estimates)[/dim]\n",
            f"  Model: [bold]{model_name}[/bold]",
            f"  Tokens: ~{total_tokens:,} / {max_tokens:,} ({pct:.1f}%)",
            f"  {bar}\n",
            "  [bold]Category Breakdown[/bold]",
            f"    System:    ~{system_chars // 4:,} tokens",
            f"    User:      ~{user_chars // 4:,} tokens",
            f"    Assistant: ~{assistant_chars // 4:,} tokens",
            f"    Tool:      ~{tool_chars // 4:,} tokens",
            f"\n  Messages: {len(messages)} total",
        ]

        await ctx.output_rich("\n".join(lines))

    def _estimate_max_tokens(self, model_name: str) -> int:
        """Rough max context window by model family."""
        name = model_name.lower()
        if "claude" in name:
            return 200_000
        elif "gpt-4o" in name:
            return 128_000
        elif "gpt-4" in name:
            return 128_000
        elif "gemini" in name:
            return 1_000_000
        elif "deepseek" in name:
            return 64_000
        else:
            return 128_000
