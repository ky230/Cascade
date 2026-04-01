import asyncio
import sys
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style as PTKStyle
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
from cascade.commands import CommandRouter, CommandContext

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

        # Configure Continuation for Multiline
        def prompt_continuation(width, line_number, is_soft_wrap):
            return HTML("<style fg='#5fd7ff' bold='true'>│  </style>")

        self.prompt_continuation = prompt_continuation

        # --- Slash Command Router ---
        self.router = CommandRouter()

        # --- Register P0 commands ---
        from cascade.commands.core.help import HelpCommand
        from cascade.commands.core.exit import ExitCommand
        from cascade.commands.core.clear import ClearCommand
        self.router.register(HelpCommand())
        self.router.register(ExitCommand())
        self.router.register(ClearCommand())

        # --- Register Model commands ---
        from cascade.commands.model.model import ModelCommand
        self.router.register(ModelCommand())

        # Cascade theme for completion dropdown + toolbar
        _ptk_style = PTKStyle.from_dict({
            # Completion menu body
            'completion-menu':                'bg:#1a1a2e',
            'completion-menu.completion':      'bg:#1a1a2e #c0c0c0',
            'completion-menu.completion.current': 'bg:#0087ff #ffffff bold',
            # Meta (description) column
            'completion-menu.meta.completion':          'bg:#1a1a2e #5fd7ff',
            'completion-menu.meta.completion.current':  'bg:#0087ff #ffffff',
            # Scrollbar
            'scrollbar.background':           'bg:#1a1a2e',
            'scrollbar.button':               'bg:#005fff',
            # Bottom toolbar
            'bottom-toolbar':                 'bg:default noreverse',
            'bottom-toolbar.text':            'bg:default noreverse',
        })

        self.session = PromptSession(
            key_bindings=kb,
            completer=self.router.get_completer(),
            complete_while_typing=True,
            erase_when_done=True,
            style=_ptk_style,
        )

        
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
        
        self.engine = QueryEngine(
            client, QueryEngineConfig(),
            registry=self.registry,
            permissions=self.permissions,
        )
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
                    prompt_ui = HTML("\n<style fg='#5fd7ff' bold='true'>❯</style> ")

                    def _toolbar():
                        import shutil
                        prov = self.engine.client.provider
                        mdl = self.engine.client.model_name
                        
                        return HTML(
                            f"<style fg='#777777'>model</style> <style fg='#0087ff'>{prov}</style> <style fg='#555555'>──</style> <style fg='#00d7af'>{mdl}</style> "
                        )

                    user_input = await self.session.prompt_async(
                        prompt_ui,
                        prompt_continuation=self.prompt_continuation,
                        bottom_toolbar=_toolbar,
                    )
                    
                if not user_input.strip():
                    continue

                # --- Slash command routing ---
                if user_input.strip().startswith('/'):
                    cmd_ctx = CommandContext(
                        console=self.console,
                        engine=self.engine,
                        session=self.session,
                        repl=self,
                    )
                    handled = await self.router.dispatch(user_input, cmd_ctx)
                    if handled:
                        continue
                    else:
                        self.console.print(
                            f"[dim]Unknown command: {user_input.strip().split()[0]}. "
                            f"Type /help for available commands.[/dim]"
                        )
                        continue

                # --- Legacy plain-text exit ---
                if user_input.strip().lower() in ['exit', 'quit']:
                    break

                # The prompt is gone. Render exact input into a gorgeous closed Panel box
                from rich.panel import Panel
                user_panel = Panel(
                    user_input,
                    border_style="#5fd7ff",
                    expand=False,
                    title="User",
                    title_align="left"
                )
                self.console.print(user_panel)

                self.console.print()
                self.console.print("[bold #5fd7ff]✦ Cascade[/bold #5fd7ff]")
                self.console.print()
                
                # Setup Spinner
                spinner = Spinner(message="Generating")
                spinner.start()
                
                tokens = []
                live = None
                
                def on_token(t):
                    nonlocal live, spinner
                    if spinner and spinner._task is not None:
                        spinner.stop()
                        
                    if live is None:
                        live = Live("", console=self.console, refresh_per_second=15)
                        live.start()
                    
                    tokens.append(t)
                    from rich.markdown import Markdown
                    live.update(Markdown("".join(tokens)))

                def handle_tool_start(name, args):
                    nonlocal live, spinner
                    if live is not None:
                        live.stop()
                        live = None
                    if spinner and spinner._task is not None:
                        spinner.stop()
                    self.renderer.render_tool_start(name, args)

                def handle_tool_end(name, tool_result):
                    nonlocal spinner
                    if spinner and spinner._task is not None:
                        spinner.stop()
                        
                    self.renderer.render_tool_end(name, tool_result.output, tool_result.is_error)
                    
                    spinner = Spinner(message="Generating")
                    spinner.start()

                async def ask_user_callback(prompt_msg: str) -> bool:
                    nonlocal live, spinner
                    if live is not None:
                        live.stop()
                    if spinner and spinner._task is not None:
                        spinner.stop()
                    
                    self.console.print()
                    ans = await self.session.prompt_async(
                        HTML(f"<style fg='#ff5f00' bold='true'>⚠️  {prompt_msg}</style> ")
                    )
                    
                    spinner = Spinner(message="Generating")
                    spinner.start()
                    
                    return ans.strip().lower() in ['y', 'yes']

                try:
                    result = await self.engine.submit(
                        user_input, 
                        on_token=on_token,
                        on_tool_start=handle_tool_start,
                        on_tool_end=handle_tool_end,
                        ask_user=ask_user_callback
                    )
                finally:
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
