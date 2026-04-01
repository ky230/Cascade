"""Cascade TUI — Textual full-screen application.

Replaces the old Rich+prompt_toolkit CascadeRepl with a proper
alternate-screen Textual App that handles:
  - Infinite scrollback via VerticalScroll
  - No resize artifacts (Textual manages alternate buffer)
  - Text selection + copy via CopyableTextArea + pyperclip
"""
from __future__ import annotations

import asyncio
import os
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Static, Input
from textual.binding import Binding

from cascade.engine.query import QueryEngine, QueryEngineConfig
from cascade.state.store import Store
from cascade.tools.registry import ToolRegistry
from cascade.permissions.engine import PermissionEngine, PermissionMode
from cascade.tools.bash_tool import BashTool
from cascade.tools.file_tools import FileReadTool, FileWriteTool
from cascade.tools.search_tools import GrepTool, GlobTool
from cascade.bootstrap.system_prompt import build_system_prompt
from cascade.commands import CommandRouter, CommandContext
from cascade.ui.widgets import CopyableTextArea, SpinnerWidget
from cascade.ui.styles import CASCADE_TCSS
from cascade.ui.banner import VERSION, ASCII_ART


class CascadeApp(App):
    """Cascade full-screen TUI."""

    CSS = CASCADE_TCSS
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("escape", "focus_input", "输入框", show=False),
    ]

    def __init__(self, client, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self._message_count = 0
        self._last_reply = ""
        self._spinner: Optional[SpinnerWidget] = None
        self._generating = False

        # ── Core engine (mirrors old CascadeRepl) ──
        self.store = Store()
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

        # ── Command Router ──
        self.router = CommandRouter()
        from cascade.commands.core.help import HelpCommand
        from cascade.commands.core.exit import ExitCommand
        from cascade.commands.core.clear import ClearCommand
        from cascade.commands.model.model import ModelCommand
        self.router.register(HelpCommand())
        self.router.register(ExitCommand())
        self.router.register(ClearCommand())
        self.router.register(ModelCommand())

    # ── Layout ────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        provider = self.engine.client.provider
        model = self.engine.client.model_name
        cwd = os.getcwd()
        home = os.path.expanduser("~")
        cwd_short = "~" + cwd[len(home):] if cwd.startswith(home) else cwd

        yield Static(
            f"  [bold #5fd7ff]✦ Cascade[/bold #5fd7ff] [dim]v{VERSION}[/dim]"
            f"  [dim]│[/dim]  [#0087ff]{provider}[/#0087ff]"
            f" [dim]──[/dim] [#00d7af]{model}[/#00d7af]"
            f"  [dim]│[/dim]  [dim]📂 {cwd_short}[/dim]",
            id="header-bar",
        )

        yield VerticalScroll(
            CopyableTextArea(
                self._build_welcome_text(),
                id="welcome-area",
                classes="message-area ai-msg",
            ),
            id="chat-history",
        )

        yield Input(
            placeholder="❯ 输入消息 (鼠标拖选→c 复制 | /help 查看命令)",
            id="prompt-input",
        )
        yield Footer()

    def _build_welcome_text(self) -> str:
        """Generate welcome banner as plain text for TextArea."""
        lines = []
        for line in ASCII_ART:
            # Strip Rich markup — TextArea is plain text only
            import re
            clean = re.sub(r'\[.*?\]', '', line) if '[' in line else line
            lines.append(clean)
        lines.append("")
        lines.append(f"  ⚛  HEP Agentic Orchestrator v{VERSION}")
        lines.append(f"  Provider: {self.engine.client.provider}")
        lines.append(f"  Model:    {self.engine.client.model_name}")
        lines.append("")
        lines.append("  操作指南:")
        lines.append("  ─────────")
        lines.append("  • 鼠标拖选 → 按 c      复制选中文本")
        lines.append("  • 滚轮 / PgUp/PgDn     翻阅历史")
        lines.append("  • /help                查看所有命令")
        lines.append("")
        return "\n".join(lines)

    def on_mount(self) -> None:
        self.query_one("#prompt-input", Input).focus()

    # ── Input handling ────────────────────────────────────────

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter in the input box."""
        user_text = event.value.strip()
        if not user_text:
            return
        if self._generating:
            self.notify("正在生成中，请稍候...", title="⏳")
            return

        input_widget = self.query_one("#prompt-input", Input)
        input_widget.value = ""

        # ── Slash command routing ──
        if user_text.startswith("/"):
            cmd_ctx = CommandContext(
                console=None,
                engine=self.engine,
                session=None,
                repl=self,
            )
            handled = await self.router.dispatch(user_text, cmd_ctx)
            if handled:
                return
            else:
                await self.append_system_message(
                    f"Unknown command: {user_text.split()[0]}. Type /help for available commands."
                )
                return

        # Legacy exit
        if user_text.lower() in ["exit", "quit"]:
            self.exit()
            return

        # ── Render user message ──
        await self.append_user_message(user_text)

        # ── AI generation ──
        await self._run_generation(user_text)

    # ── AI Generation with streaming ─────────────────────────

    async def _run_generation(self, user_text: str) -> None:
        """Submit to QueryEngine with streaming callbacks."""
        container = self.query_one("#chat-history", VerticalScroll)
        self._message_count += 1
        msg_id = self._message_count
        self._generating = True

        # AI label
        ai_label = Static("  ✦ Cascade", classes="ai-label")
        await container.mount(ai_label)

        # Spinner
        await self._show_spinner("Generating")
        container.scroll_end(animate=False)

        tokens: list[str] = []

        def on_token(t: str) -> None:
            tokens.append(t)

        def on_tool_start(name: str, args: dict) -> None:
            self.call_from_thread(self._handle_tool_start, name, args)

        def on_tool_end(name: str, tool_result) -> None:
            self.call_from_thread(self._handle_tool_end, name, tool_result)

        async def ask_user(prompt_msg: str) -> bool:
            # TODO: Implement modal dialog for permission prompts
            # For now, auto-approve (matches old behavior with AUTO mode)
            return True

        try:
            result = await self.engine.submit(
                user_text,
                on_token=on_token,
                on_tool_start=on_tool_start,
                on_tool_end=on_tool_end,
                ask_user=ask_user,
            )
        except Exception as e:
            await self._remove_spinner()
            await self.append_system_message(f"Error: {e}")
            self._generating = False
            self.query_one("#prompt-input", Input).focus()
            return

        # Remove spinner
        await self._remove_spinner()

        # Render final AI response
        final_text = "".join(tokens) if tokens else (result.output or "")
        self._last_reply = final_text

        if final_text.strip():
            ai_area = CopyableTextArea(
                final_text,
                id=f"ai-msg-{msg_id}",
                classes="message-area ai-msg",
            )
            await container.mount(ai_area)

        container.scroll_end(animate=False)
        self._generating = False
        self.query_one("#prompt-input", Input).focus()

    def _handle_tool_start(self, name: str, args: dict) -> None:
        """Sync callback for tool start — schedules async UI update."""
        async def _do():
            await self._remove_spinner()
            args_preview = str(args)
            if len(args_preview) > 200:
                args_preview = args_preview[:200] + "..."
            await self.append_tool_message(f"⚙ {name}", args_preview, css_class="tool-msg")
            await self._show_spinner("Executing")
        asyncio.ensure_future(_do())

    def _handle_tool_end(self, name: str, tool_result) -> None:
        """Sync callback for tool end — schedules async UI update."""
        async def _do():
            await self._remove_spinner()
            output = tool_result.output if hasattr(tool_result, 'output') else str(tool_result)
            is_error = tool_result.is_error if hasattr(tool_result, 'is_error') else False
            display = output[:500] + "\n..." if len(output) > 500 else output
            label = f"✗ Error: {name}" if is_error else f"✓ Result: {name}"
            css_class = "tool-msg-error" if is_error else "tool-msg"
            await self.append_tool_message(label, display, css_class=css_class)
            await self._show_spinner("Generating")
        asyncio.ensure_future(_do())

    # ── Spinner management ────────────────────────────────────

    async def _show_spinner(self, message: str = "Thinking") -> None:
        """Mount a spinner widget in the chat history."""
        container = self.query_one("#chat-history", VerticalScroll)
        self._spinner = SpinnerWidget(message, classes="spinner")
        await container.mount(self._spinner)
        container.scroll_end(animate=False)

    async def _remove_spinner(self) -> None:
        """Remove current spinner widget if present."""
        if self._spinner is not None:
            try:
                self._spinner.stop()
                if self._spinner.is_mounted:
                    await self._spinner.remove()
            except Exception:
                pass
            self._spinner = None

    # ── Message helpers ───────────────────────────────────────

    async def append_user_message(self, text: str) -> None:
        """Add a user message bubble to the chat history."""
        container = self.query_one("#chat-history", VerticalScroll)
        self._message_count += 1
        await container.mount(
            Static("  ❯ User", classes="user-label"),
        )
        await container.mount(
            CopyableTextArea(
                text,
                id=f"user-msg-{self._message_count}",
                classes="message-area user-msg",
            ),
        )
        container.scroll_end(animate=False)

    async def append_system_message(self, text: str) -> None:
        """Add a system/info message to the chat history."""
        container = self.query_one("#chat-history", VerticalScroll)
        await container.mount(
            CopyableTextArea(text, classes="message-area system-msg"),
        )
        container.scroll_end(animate=False)
        self.query_one("#prompt-input", Input).focus()

    async def append_tool_message(
        self, label: str, content: str, css_class: str = "tool-msg"
    ) -> None:
        """Add a tool execution message to the chat history."""
        container = self.query_one("#chat-history", VerticalScroll)
        await container.mount(
            Static(f"  {label}", classes="tool-label"),
        )
        await container.mount(
            CopyableTextArea(content, classes=f"message-area {css_class}"),
        )
        container.scroll_end(animate=False)

    def update_header(self) -> None:
        """Refresh header after model switch."""
        header = self.query_one("#header-bar", Static)
        provider = self.engine.client.provider
        model = self.engine.client.model_name
        cwd = os.getcwd()
        home = os.path.expanduser("~")
        cwd_short = "~" + cwd[len(home):] if cwd.startswith(home) else cwd
        header.update(
            f"  [bold #5fd7ff]✦ Cascade[/bold #5fd7ff] [dim]v{VERSION}[/dim]"
            f"  [dim]│[/dim]  [#0087ff]{provider}[/#0087ff]"
            f" [dim]──[/dim] [#00d7af]{model}[/#00d7af]"
            f"  [dim]│[/dim]  [dim]📂 {cwd_short}[/dim]"
        )

    # ── Actions ───────────────────────────────────────────────

    def action_focus_input(self) -> None:
        """Escape: Focus the input box."""
        self.query_one("#prompt-input", Input).focus()
