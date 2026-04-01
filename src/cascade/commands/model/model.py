from cascade.commands.base import BaseCommand, CommandContext
from cascade.services.api_client import ModelClient
from cascade.ui.banner import render_status_bar
from rich.table import Table
from rich.prompt import Prompt
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
    "grok": {
        "display": "xAI (Grok)",
        "env_key": "XAI_API_KEY",
        "models": [
            {"id": "grok-4.20-0309-reasoning", "label": "Grok 4.20 (Reasoning)", "price": "$2.00/M in, $6.00/M out"},
            {"id": "grok-4.20-0309-non-reasoning", "label": "Grok 4.20 (Fast)", "price": "$2.00/M in, $6.00/M out"},
            {"id": "grok-4.20-multi-agent-0309", "label": "Grok 4.20 (Multi-Agent)", "price": "$2.00/M in, $6.00/M out"},
            {"id": "grok-4-1-fast-reasoning", "label": "Grok 4.1 Fast (Reasoning)", "price": "$0.20/M in, $0.50/M out"},
            {"id": "grok-4-1-fast-non-reasoning", "label": "Grok 4.1 Fast", "price": "$0.20/M in, $0.50/M out"},
            {"id": "grok-imagine-image-pro", "label": "Grok Image Pro", "price": "$0.07 / image"},
        ],
    },
    "glm": {
        "display": "ZhipuAI (GLM)",
        "env_key": "GLM_API_KEY",
        "models": [
            {"id": "glm-4-flash", "label": "GLM-4 Flash", "price": "Free"},
            {"id": "glm-4.6", "label": "GLM-4.6", "price": "$0.07/M"},
        ],
    },
    "anthropic": {
        "display": "Anthropic",
        "env_key": "ANTHROPIC_API_KEY",
        "models": [
            {"id": "claude-sonnet-4-20250514", "label": "Sonnet 4", "price": "$3/M in, $15/M out"},
            {"id": "claude-opus-4-20250514", "label": "Opus 4", "price": "$15/M in, $75/M out"},
        ],
    },
    "gemini": {
        "display": "Google Gemini",
        "env_key": "GEMINI_API_KEY",
        "models": [
            {"id": "gemini-2.5-flash", "label": "Gemini 2.5 Flash", "price": "$0.15/M in"},
            {"id": "gemini-2.5-pro", "label": "Gemini 2.5 Pro", "price": "$1.25/M in, $10/M out"},
        ],
    },
    "openai": {
        "display": "OpenAI",
        "env_key": "OPENAI_API_KEY",
        "models": [
            {"id": "gpt-4o", "label": "GPT-4o", "price": "$2.50/M in, $10/M out"},
            {"id": "gpt-4o-mini", "label": "GPT-4o Mini", "price": "$0.15/M in, $0.60/M out"},
            {"id": "o3-mini", "label": "o3-mini", "price": "$1.10/M in, $4.40/M out"},
        ],
    },
    "kimi": {
        "display": "Moonshot (Kimi)",
        "env_key": "MOONSHOT_API_KEY",
        "models": [
            {"id": "moonshot-v1-auto", "label": "Kimi Auto", "price": "CN pricing"},
        ],
    },
    "qwen": {
        "display": "Alibaba Qwen",
        "env_key": "DASHSCOPE_API_KEY",
        "models": [
            {"id": "qwen-plus", "label": "Qwen Plus", "price": "CN pricing"},
            {"id": "qwen-turbo", "label": "Qwen Turbo", "price": "CN pricing"},
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

        # Quick switch: /model deepseek deepseek-chat
        if args.strip():
            parts = args.strip().split()
            if len(parts) == 2:
                new_provider, new_model = parts
                if new_provider in PROVIDER_CATALOG:
                    engine.client = ModelClient(provider=new_provider, model_name=new_model)
                    return
                else:
                    ctx.console.print(
                        f"[red]Unknown provider: {new_provider}[/red]\n"
                        f"[dim]Available: {', '.join(PROVIDER_CATALOG.keys())}[/dim]"
                    )
                    return
            ctx.console.print("[dim]Usage: /model <provider> <model> or just /model for picker[/dim]")
            return

        # Interactive picker
        table = Table(
            title="[bold #5fd7ff]Switch Model[/bold #5fd7ff]",
            show_header=True,
            header_style="bold",
            border_style="#5fd7ff",
            expand=False,
        )
        table.add_column("#", style="bold #00d7af", width=4)
        table.add_column("Provider", style="#0087ff")
        table.add_column("Model", style="bold")
        table.add_column("Price", style="dim")

        choices = []
        idx = 1
        for prov_key, prov_info in PROVIDER_CATALOG.items():
            api_key = os.getenv(prov_info["env_key"], "")
            key_status = "[green]✓[/green]" if api_key else "[red]✗[/red]"
            for m in prov_info["models"]:
                is_current = (prov_key == current_provider and m["id"] == current_model)
                marker = " [bold yellow]<< current[/bold yellow]" if is_current else ""
                table.add_row(
                    str(idx),
                    f"{prov_info['display']} {key_status}",
                    f"{m['label']} ({m['id']}){marker}",
                    m["price"],
                )
                choices.append((prov_key, m["id"]))
                idx += 1

        ctx.console.print(table)

        # Prompt for selection
        selection = Prompt.ask(
            "[#5fd7ff]Select number (or Enter to cancel)[/#5fd7ff]",
            console=ctx.console,
            default="",
        )

        if not selection.strip():
            ctx.console.print("[dim]Cancelled.[/dim]")
            return

        try:
            choice_idx = int(selection) - 1
            if 0 <= choice_idx < len(choices):
                new_provider, new_model = choices[choice_idx]
                engine.client = ModelClient(provider=new_provider, model_name=new_model)
            else:
                ctx.console.print("[red]Invalid selection.[/red]")
        except ValueError:
            ctx.console.print("[red]Enter a number.[/red]")
