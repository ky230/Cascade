from cascade.commands.base import BaseCommand, CommandContext


class BtwCommand(BaseCommand):
    """Inject a quick aside into the conversation.

    Reference: claude-code src/commands/btw/btw.tsx (243 lines)
    Claude Code impl: renders <BtwSideQuestion> JSX component that
    forks a side question to the LLM via runSideQuestion() with
    cache-safe params. Shows Markdown response in ScrollBox with
    Spinner animation. Supports keyboard scrolling and dismiss
    (Esc/Enter/Space). Tracks btwUseCount in global config.
    Cascade impl: simplified — injects the aside as a user message
    into engine.messages context. Does NOT trigger a separate LLM
    call (no side question fork system). The aside provides context
    for the next model turn.
    """
    name = "btw"
    description = "Inject a quick aside into the conversation"
    category = "UI"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        if not args.strip():
            await ctx.output_rich(
                "[dim]Usage: /btw <your note to the model>[/dim]"
            )
            return
        note = f"[User aside]: {args.strip()}"
        ctx.engine.messages.append({"role": "user", "content": note})
        await ctx.output_rich(
            f"[dim italic]Noted: {args.strip()}[/dim italic]"
        )
