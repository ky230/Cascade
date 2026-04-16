"""Context window usage visualization.

Shows real API token usage data only. No offline estimates.
Before the first API call, all counters are 0.
After each call, displays the last call's token breakdown
and cumulative session totals.
"""
from cascade.commands.base import BaseCommand, CommandContext
from cascade.services.api_config import get_litellm_kwargs


class ContextCommand(BaseCommand):
    """Show context window usage from real API token counters.

    Displays 0 before the first API call. After each call, shows
    the last call's token breakdown and cumulative session totals.
    """
    name = "context"
    description = "Show context window usage"
    category = "Rules"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        model_name = ctx.engine.client.model_name
        provider = ctx.engine.client.provider

        # Resolve LiteLLM model key for max context query
        kwargs = get_litellm_kwargs(provider, model_name)
        litellm_model = kwargs["model"]
        max_tokens = self._get_max_tokens(litellm_model)

        # Read real API usage counters (0 if no API calls yet)
        last_input = getattr(ctx.engine, "last_input_tokens", 0)
        last_output = getattr(ctx.engine, "last_output_tokens", 0)
        session_input = getattr(ctx.engine, "session_input_tokens", 0)
        session_output = getattr(ctx.engine, "session_output_tokens", 0)

        total_tokens = last_input + last_output
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
            "[bold]Context Usage[/bold]\n",
            f"  Model: [bold]{model_name}[/bold]",
            f"  Context: {total_tokens:,} / {max_tokens:,} ({pct:.1f}%)",
            f"  {bar}\n",
        ]

        if last_input > 0:
            lines.append(f"  Last call: {last_input:,} in / {last_output:,} out")

        if session_input > 0:
            lines.append(
                f"  Session total: {session_input + session_output:,} tokens "
                f"({session_input:,} in / {session_output:,} out)"
            )

        lines.append(f"\n  Messages: {len(ctx.engine.messages)} total")

        await ctx.output_rich("\n".join(lines))

    # Manual context window overrides for models LiteLLM doesn't know
    _CONTEXT_OVERRIDES: dict[str, int] = {
        # Grok language models: all 2M context
        "grok-4.20-0309-reasoning": 2_000_000,
        "grok-4.20-0309-non-reasoning": 2_000_000,
        "grok-4.20-multi-agent-0309": 2_000_000,
        "grok-4-1-fast-reasoning": 2_000_000,
        "grok-4-1-fast-non-reasoning": 2_000_000,
        # Image generation models: fallback 200K
        "grok-imagine-image-pro": 200_000,
        "gemini-3.1-flash-image-preview": 200_000,
        # Xiaomi MiMo-V2
        "mimo-v2-pro": 1_000_000,
        "mimo-v2-omni": 256_000,
        "mimo-v2-flash": 256_000,
        # Alibaba Qwen: all 1M
        "qwen3.6-plus": 1_000_000,
        "qwen3.5-flash": 1_000_000,
        "qwen3.5-plus": 1_000_000,
        "qwen3-coder-plus": 1_000_000,
        # MiniMax: all 204,800 (input+output combined)
        "MiniMax-M2.7": 204_800,
        "MiniMax-M2.7-highspeed": 204_800,
        "MiniMax-M2.5": 204_800,
        "MiniMax-M2.5-highspeed": 204_800,
        # ZhipuAI GLM: 5.x/4.7/4.6 = 200K; 4.5 and below = 128K (matches fallback)
        "glm-5.1": 200_000,
        "glm-5-turbo": 200_000,
        "glm-5": 200_000,
        "glm-4.7": 200_000,
        "glm-4.6": 200_000,
    }

    def _get_max_tokens(self, litellm_model: str) -> int:
        """Query context window size. Checks manual overrides first,
        then LiteLLM model info, then falls back to 128k."""
        # Strip provider prefix for override lookup (e.g. "xai/grok-4.20..." -> "grok-4.20...")
        bare_model = litellm_model.split("/", 1)[-1] if "/" in litellm_model else litellm_model
        if bare_model in self._CONTEXT_OVERRIDES:
            return self._CONTEXT_OVERRIDES[bare_model]
        try:
            from litellm import get_model_info
            info = get_model_info(litellm_model)
            return info.get("max_input_tokens", 128_000)
        except Exception:
            return 128_000

