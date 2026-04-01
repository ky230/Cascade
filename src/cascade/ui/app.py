import asyncio
import sys
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import HTML
from rich.console import Console
from rich.live import Live

from cascade.engine.query import QueryEngine, QueryEngineConfig
from cascade.state.store import Store
from cascade.state.app_state import AppState
from cascade.tools.registry import ToolRegistry
from cascade.permissions.engine import PermissionEngine, PermissionMode
from cascade.tools.bash_tool import BashTool
from cascade.tools.file_tools import FileReadTool, FileWriteTool
from cascade.tools.search_tools import GrepTool, GlobTool
from cascade.ui.renderer import MessageRenderer
from cascade.ui.banner import render_banner_rich
from cascade.bootstrap.system_prompt import build_system_prompt
from cascade.ui.spinner import Spinner

class CascadeRepl:
    def __init__(self, client):
        self.console = Console()
        self.renderer = MessageRenderer(self.console)
        
        # Configure KeyBindings
        kb = KeyBindings()
        
        @kb.add('c-n')
        def _(event):
            event.current_buffer.insert_text('\n')
            
        @kb.add('enter')
        def _(event):
            b = event.current_buffer
            if not b.text.strip():
                # Ignore empty enter
                pass
            else:
                b.validate_and_handle()

        self.session = PromptSession(key_bindings=kb)
        
        # Initialize Core Components
        self.store = Store()
        
        # Initialize Tools & Permissions
        self.registry = ToolRegistry()
        self.registry.register(BashTool())
        self.registry.register(FileReadTool())
        self.registry.register(FileWriteTool())
        self.registry.register(GrepTool())
        self.registry.register(GlobTool())
        
        self.permissions = PermissionEngine(mode=PermissionMode.AUTO)
        
        # Initialize Engine
        self.engine = QueryEngine(client, QueryEngineConfig())
        self.engine.set_system_prompt(build_system_prompt())

    async def run(self):
        banner = render_banner_rich(
            provider=self.engine.client.provider,
            model=self.engine.client.model_name
        )
        self.console.print(banner)
        self.console.print("[dim]Type 'exit' or 'quit' to close. Ctrl+N for newline.[/dim]\n")
        
        while True:
            try:
                with patch_stdout():
                    user_input = await self.session.prompt_async(HTML("\n<style fg='#5fd7ff' bold='true'>❯</style> "))
                    
                if not user_input.strip():
                    continue
                if user_input.strip().lower() in ['exit', 'quit']:
                    break

                self.console.print()
                self.console.print("[bold #5fd7ff]✦ Cascade[/bold #5fd7ff]")
                self.console.print()
                
                # Setup Spinner
                spinner = Spinner(message="Generating")
                spinner.start()
                
                tokens = []
                live = None
                
                def on_token(t):
                    nonlocal live
                    if spinner._task is not None:
                        spinner.stop()
                        # Start Live only after spinner stops
                        live = Live("", console=self.console, refresh_per_second=15)
                        live.start()
                    
                    tokens.append(t)
                    if live is not None:
                        from rich.markdown import Markdown
                        live.update(Markdown("".join(tokens)))

                result = await self.engine.submit(user_input, on_token=on_token)
                
                if spinner._task is not None:
                    spinner.stop()
                    
                if live is not None:
                    live.stop()

                self.console.print()

            except (EOFError, KeyboardInterrupt):
                break
            except Exception as e:
                self.console.print(f"[bold red]Error:[/bold red] {e}")

        self.console.print("[dim]Goodbye![/dim]")
