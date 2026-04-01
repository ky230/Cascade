"""Cascade REPL — prompt_toolkit based interactive CLI.

Replaces the full-screen Textual app with a REPL architecture
inspired by Claude Code and Gemini CLI, ensuring native terminal
text selection while keeping the rich UI aesthetics.
"""
from __future__ import annotations

import shutil
import time
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

# TODO(phase3): Replace with cascade.engine.query.QueryEngine
# from cascade.core.agent import Agent
from cascade.ui.banner import render_banner_rich


class CascadeRepl:
    """Read-Eval-Print Loop for Cascade."""

    def __init__(self, provider: str, model: str):
        self.provider = provider
        self.model = model
        self.agent = Agent(provider=provider, model_name=model)
        self.console = Console()

    async def _get_input(self) -> str | None:
        """Collect user input using PromptSession (resize-safe)."""
        kb = KeyBindings()

        @kb.add("enter")
        def submit(event):
            buf = event.app.current_buffer
            if buf.text.strip():
                event.app.exit(result=buf.text)

        @kb.add("c-n")
        def newline(event):
            event.app.current_buffer.insert_text("\n")

        @kb.add("c-c")
        def cancel(event):
            event.app.exit(result=None)

        style = Style.from_dict({
            "prompt": "#44aacc",
        })

        session = PromptSession(
            message=FormattedText([("class:prompt", "❯ ")]),
            multiline=True,
            prompt_continuation=lambda width, line_number, wrap_count: "  ",
            key_bindings=kb,
            style=style,
        )

        try:
            return await session.prompt_async()
        except (EOFError, KeyboardInterrupt):
            return None

    async def run(self) -> None:
        """Main interaction loop."""
        self.console.print(render_banner_rich(self.provider, self.model))
        self.console.print()
        self.console.print("[dim]Press Enter to send · Ctrl+N for newline · Ctrl+C to exit[/dim]")
        self.console.print()

        while True:
            try:
                result = await self._get_input()

                if result is None:
                    break

                user_input = result.strip()
                if not user_input:
                    continue

                if user_input.lower() in ("exit", "quit"):
                    break

                # Send message with Spinner + elapsed time
                t0 = time.time()
                response = None

                async def do_chat():
                    nonlocal response
                    response = await self.agent.chat(user_input)

                import asyncio
                task = asyncio.create_task(do_chat())
                spinner = Spinner("dots")
                with Live(spinner, console=self.console, transient=True, refresh_per_second=10) as live:
                    while not task.done():
                        elapsed = time.time() - t0
                        spinner.update(text=f"[italic #44aacc]Generating... {elapsed:.1f}s[/italic #44aacc]")
                        live.refresh()
                        await asyncio.sleep(0.1)
                await task

                self.console.print(f"[bold #5fd7ff]✦ Cascade[/bold #5fd7ff]\n")
                self.console.print(response)
                self.console.print()

            except (KeyboardInterrupt, EOFError):
                break
            except Exception as e:
                self.console.print(f"[bold red]\\[Error][/bold red] {str(e)}\n")
