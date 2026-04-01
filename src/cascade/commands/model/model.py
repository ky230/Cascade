from cascade.commands.base import BaseCommand, CommandContext
from cascade.services.api_client import ModelClient
from cascade.ui.banner import render_status_bar
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

        # Interactive picker — inline Rich Table + arrow key cbreak mode
        import asyncio
        import sys
        import tty
        import termios
        import select
        from rich.table import Table
        from rich.live import Live
        from rich.console import Group
        import threading

        choices = []
        cursor = 0
        
        for prov_key, prov_info in PROVIDER_CATALOG.items():
            api_key = os.getenv(prov_info["env_key"], "")
            key_status = "[#00d7af]✓[/]" if api_key else "[dim]✗[/]"
            for m in prov_info["models"]:
                is_current = (prov_key == current_provider and m["id"] == current_model)
                if is_current:
                    cursor = len(choices)
                choices.append({
                    "provider_display": f"{prov_info['display']} {key_status}",
                    "model_label": m["label"],
                    "model_id": m["id"],
                    "price": m["price"],
                    "is_current": is_current,
                    "provider_key": prov_key,
                })

        total = len(choices)
        done = asyncio.Event()
        cancelled = False

        def _get_renderable(current_cursor):
            table = Table(
                show_header=True,
                header_style="bold #5fd7ff",
                border_style="#5fd7ff",
                expand=False,
                padding=(0, 2),
            )
            table.add_column("", width=2)  # Pointer column
            table.add_column("Provider", style="#0087ff")
            table.add_column("Model", style="bold")
            table.add_column("Price", style="dim")

            for i, c in enumerate(choices):
                is_selected = (i == current_cursor)
                
                ptr = "[bold #00d7af]❯[/]" if is_selected else ""
                prov_str = f"[bold #00d7af]{c['provider_display']}[/]" if is_selected else c["provider_display"]
                
                marker = " [bold #00d7af]← current[/]" if c["is_current"] else ""
                    
                model_col = f"[bold #5fd7ff]{c['model_label']} [dim]({c['model_id']})[/][/]{marker}" if is_selected else f"{c['model_label']} [dim]({c['model_id']})[/]{marker}"
                price_col = f"[bold #00d7af]{c['price']}[/]" if is_selected else c["price"]

                table.add_row(ptr, prov_str, model_col, price_col)

            header = (
                "[bold #5fd7ff]Select model[/bold #5fd7ff]\n"
                "[dim]Switch between AI models. Applies to this session. Provide custom picks with [bold]/model <prov> <id>[/].\n"
                "Supported providers: DeepSeek, xAI (Grok), Anthropic, Gemini, OpenAI, ZhipuAI, Kimi, and Qwen.\n\n"
                "(↑↓ navigate • Enter confirm • Esc cancel)[/dim]"
            )
            
            return Group(header, table)

        def _read_keys(loop):
            import os
            nonlocal cursor, cancelled
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                while not done.is_set():
                    r, _, _ = select.select([fd], [], [], 0.5)
                    if not r:
                        continue
                        
                    # Use unbuffered OS read to prevent Py sys.stdin buffering issues with select
                    b = os.read(fd, 3)
                    if not b:
                        continue
                        
                    if b == b'\x1b':
                        cancelled = True
                        loop.call_soon_threadsafe(done.set)
                        return
                    elif b in (b'\x1b[A', b'\x1bOA'):  # Up
                        cursor = (cursor - 1) % total
                    elif b in (b'\x1b[B', b'\x1bOB'):  # Down
                        cursor = (cursor + 1) % total
                    elif b in (b'\r', b'\n'):
                        loop.call_soon_threadsafe(done.set)
                        return
                    elif b == b'\x03':  # Ctrl+C
                        cancelled = True
                        loop.call_soon_threadsafe(done.set)
                        return
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)

        loop = asyncio.get_event_loop()
        key_thread = threading.Thread(target=_read_keys, args=(loop,), daemon=True)
        key_thread.start()

        # Render table inline. 
        # When done.is_set(), the table will completely vanish because transient=True
        with Live(_get_renderable(cursor), console=ctx.console, refresh_per_second=15, transient=True) as live:
            while not done.is_set():
                live.update(_get_renderable(cursor))
                await asyncio.sleep(0.05)

        key_thread.join(timeout=0.5)

        if cancelled:
            ctx.console.print("[dim]Cancelled.[/dim]")
            return

        selected_choice = choices[cursor]
        engine.client = ModelClient(provider=selected_choice["provider_key"], model_name=selected_choice["model_id"])


