from cascade.commands.base import BaseCommand, CommandContext
from cascade.services.api_client import ModelClient
import os


# Provider catalog with display names and known models + pricing
PROVIDER_CATALOG = {
    "deepseek": {
        "display": "DeepSeek",
        "env_key": "DEEPSEEK_API_KEY",
        "models": [
            {"id": "deepseek-chat", "label": "DeepSeek-V3.2", "price": "¥2.00/M in (¥0.20 hit), ¥3.00/M out"},
            {"id": "deepseek-reasoner", "label": "DeepSeek-V3.2 (Reasoner)", "price": "¥2.00/M in (¥0.20 hit), ¥3.00/M out"},
        ],
    },
    "gemini": {
        "display": "Google Gemini",
        "env_key": "GEMINI_API_KEY",
        "models": [
            {"id": "gemini-3.1-pro-preview", "label": "Gemini 3.1 Pro Preview", "price": "≤200K: $2/M in, $12/M out; >200K: $4/M in, $18/M out; Paid account -50% extra"},
            {"id": "gemini-3.1-pro-preview-customtools", "label": "Gemini 3.1 Pro (Tools)", "price": "≤200K: $2/M in, $12/M out; >200K: $4/M in, $18/M out; Paid account -50% extra"},
            {"id": "gemini-3.1-flash-lite-preview", "label": "Gemini 3.1 Flash Lite Preview", "price": "Free account: free (limited); Paid account: $0.125/M in, $0.75/M out"},
            {"id": "gemini-3.1-flash-image-preview", "label": "Gemini 3.1 Flash Image 🎨", "price": "Paid account only: ~$0.076/image (4K)"},
            {"id": "gemini-3-pro-preview", "label": "Gemini 3 Pro Preview", "price": "≤200K: $2/M in, $12/M out; >200K: $4/M in, $18/M out; Paid account -50% extra"},
            {"id": "gemini-3-flash-preview", "label": "Gemini 3 Flash Preview", "price": "$0.50/M in, $3.00/M out; Paid account -50% extra"},
            {"id": "gemini-2.5-pro", "label": "Gemini 2.5 Pro", "price": "≤200K: $1.25/M in, $10/M out; >200K: $2.50/M in, $15/M out; Paid account -50% extra"},
            {"id": "gemini-2.5-flash", "label": "Gemini 2.5 Flash", "price": "$0.30/M in, $2.50/M out; Paid account -50% extra"},
        ],
    },
    "grok": {
        "display": "xAI (Grok)",
        "env_key": "XAI_API_KEY",
        "models": [
            {"id": "grok-4.20-0309-reasoning", "label": "Grok 4.20 (Reasoning)", "price": "$2.00/M in, $6.00/M out"},
            {"id": "grok-4.20-0309-non-reasoning", "label": "Grok 4.20 (Fast)", "price": "$2.00/M in, $6.00/M out"},
            {"id": "grok-4.20-multi-agent-0309", "label": "Grok 4.20 (Multi-Agent)", "price": "$2.00/M in, $6.00/M out"},
            {"id": "grok-4-1-fast-reasoning", "label": "Grok 4.1 Fast (Reasoning)", "price": "$0.20/M in, $0.50/M out"},
            {"id": "grok-4-1-fast-non-reasoning", "label": "Grok 4.1 Fast", "price": "$0.20/M in, $0.50/M out"},
            {"id": "grok-imagine-image-pro", "label": "Grok Image Pro 🎨", "price": "$0.07 / image"},
        ],
    },
    "kimi": {
        "display": "Moonshot (Kimi)",
        "env_key": "MOONSHOT_API_KEY",
        "models": [
            {"id": "kimi-k2.5", "label": "Kimi K2.5", "price": "¥4.00/M in, ¥21.00/M out"},
            {"id": "moonshot-v1-128k", "label": "Kimi 128K", "price": "¥10.00/M in, ¥30.00/M out"},
            {"id": "moonshot-v1-128k-vision-preview", "label": "Kimi 128K Vision", "price": "¥10.00/M in, ¥30.00/M out"},
        ],
    },
    "glm": {
        "display": "ZhipuAI (GLM)",
        "env_key": "GLM_API_KEY",
        "models": [
            {"id": "glm-5.1", "label": "GLM-5.1", "price": "Need GLM Coding Plan"},
            {"id": "glm-5-turbo", "label": "GLM-5 Turbo", "price": "¥5/M in, ¥22/M out; >32K: ¥7/M in, ¥26/M out"},
            {"id": "glm-5", "label": "GLM-5", "price": "¥4/M in, ¥18/M out; >32K: ¥6/M in, ¥22/M out"},
            {"id": "glm-4.7", "label": "GLM-4.7", "price": "¥2/M in, ¥8/M out; >32K: ¥4/M in, ¥16/M out"},
            {"id": "glm-4.6", "label": "GLM-4.6", "price": "¥2/M in, ¥8/M out"},
            {"id": "glm-4.5", "label": "GLM-4.5", "price": "¥2/M in, ¥8/M out"},
            {"id": "glm-4.5-air", "label": "GLM-4.5 Air", "price": "¥0.80/M in, ¥2/M out"},
            {"id": "glm-4-flash", "label": "GLM-4 Flash", "price": "Free"},
        ],
    },
    "minimax": {
        "display": "MiniMax",
        "env_key": "MINIMAX_API_KEY",
        "models": [
            {"id": "MiniMax-M2.7", "label": "MiniMax M2.7", "price": "$0.30/M in, $1.20/M out"},
            {"id": "MiniMax-M2.7-highspeed", "label": "MiniMax M2.7 HS", "price": "$0.60/M in, $2.40/M out"},
            {"id": "MiniMax-M2.5", "label": "MiniMax M2.5", "price": "$0.30/M in, $1.20/M out"},
            {"id": "MiniMax-M2.5-highspeed", "label": "MiniMax M2.5 HS", "price": "$0.60/M in, $2.40/M out"},
        ],
    },
    "qwen": {
        "display": "Alibaba Qwen",
        "env_key": "DASHSCOPE_API_KEY",
        "models": [
            {"id": "qwen3.5-flash", "label": "Qwen 3.5 Flash", "price": "¥0.20/M in, ¥0.80/M out"},
            {"id": "qwen3.5-plus", "label": "Qwen 3.5 Plus", "price": "¥0.80/M in, ¥2.00/M out"},
            {"id": "qwen3-coder-plus", "label": "Qwen3 Coder Plus", "price": "~¥0.80/M in, ~¥2.00/M out"},
        ],
    },
    "anthropic": {
        "display": "Anthropic",
        "env_key": "ANTHROPIC_API_KEY",
        "models": [
            {"id": "claude-opus-4-6", "label": "Opus 4.6", "price": "$5/M in, $25/M out"},
            {"id": "claude-sonnet-4-6", "label": "Sonnet 4.6", "price": "$3/M in, $15/M out"},
            {"id": "claude-haiku-4-5-20251001", "label": "Haiku 4.5", "price": "$1/M in, $5/M out"},
        ],
    },
    "openai": {
        "display": "OpenAI",
        "env_key": "OPENAI_API_KEY",
        "models": [
            {"id": "gpt-5.4", "label": "GPT-5.4", "price": "$2.50/M in, $15/M out"},
            {"id": "gpt-5.4-pro", "label": "GPT-5.4 Pro", "price": "$30/M in, $180/M out"},
            {"id": "gpt-5.4-mini", "label": "GPT-5.4 Mini", "price": "$0.75/M in, $4.50/M out"},
            {"id": "gpt-5.4-nano", "label": "GPT-5.4 Nano", "price": "$0.20/M in, $1.25/M out"},
        ],
    },
}


class ModelCommand(BaseCommand):
    name = "model"
    description = "Switch model (interactive picker with pricing)"
    category = "Model"

    async def execute(self, ctx: CommandContext, args: str) -> None:
        engine = ctx.engine
        current_provider = engine.client.provider
        current_model = engine.client.model_name

        # Build numbered choices list
        choices = []
        for prov_key, prov_info in PROVIDER_CATALOG.items():
            api_key = os.getenv(prov_info["env_key"], "")
            key_status = "✓" if api_key else "✗"
            for m in prov_info["models"]:
                is_current = (prov_key == current_provider and m["id"] == current_model)
                choices.append({
                    "provider_display": prov_info["display"],
                    "key_status": key_status,
                    "model_label": m["label"],
                    "model_id": m["id"],
                    "price": m["price"],
                    "is_current": is_current,
                    "provider_key": prov_key,
                })

        # Quick switch: /model deepseek deepseek-chat
        if args.strip():
            parts = args.strip().split()

            # Numbered selection: /model 3
            if len(parts) == 1 and parts[0].isdigit():
                idx = int(parts[0]) - 1
                if 0 <= idx < len(choices):
                    sel = choices[idx]
                    engine.client = ModelClient(provider=sel["provider_key"], model_name=sel["model_id"])
                    if hasattr(ctx.repl, 'update_header'):
                        ctx.repl.update_header()
                    if hasattr(ctx.repl, 'update_footer'):
                        ctx.repl.update_footer()
                    await ctx.output_rich(
                        f"[#00d7af]✓ Switched to {sel['provider_display']} / {sel['model_label']} ({sel['model_id']})[/#00d7af]"
                    )
                    return
                else:
                    await ctx.output_rich(f"[red]Invalid number: {parts[0]}. Valid range: 1-{len(choices)}[/red]")
                    return

            # Provider + model: /model deepseek deepseek-chat
            if len(parts) == 2:
                new_provider, new_model = parts
                if new_provider in PROVIDER_CATALOG:
                    engine.client = ModelClient(provider=new_provider, model_name=new_model)
                    if hasattr(ctx.repl, 'update_header'):
                        ctx.repl.update_header()
                    if hasattr(ctx.repl, 'update_footer'):
                        ctx.repl.update_footer()
                    await ctx.output_rich(f"[#00d7af]✓ Switched to {new_provider} / {new_model}[/#00d7af]")
                    return
                else:
                    await ctx.output_rich(
                        f"[red]Unknown provider: {new_provider}[/red]\n"
                        f"[dim]Available: {', '.join(PROVIDER_CATALOG.keys())}[/dim]"
                    )
                    return

            await ctx.output_rich("[dim]Usage: /model [number] or /model <provider> <model_id>[/dim]")
            return

        # Delegate to the Textual app which uses callback-based push_screen
        if hasattr(ctx.repl, 'open_model_picker'):
            ctx.repl.open_model_picker(engine, current_provider, current_model)
        else:
            await ctx.output("Model picker not available in this mode.")



