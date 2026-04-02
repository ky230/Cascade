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
from textual.containers import VerticalScroll, Horizontal, Vertical
from textual.widgets import Footer, Static, Input
from textual.binding import Binding
from textual import on

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
from cascade.ui.command_palette import CommandPalette
from cascade.ui.styles import CASCADE_TCSS
from cascade.ui.banner import VERSION, ASCII_ART, _LOGO, _L, _R


class CascadeApp(App):
    """Cascade full-screen TUI."""

    CSS = CASCADE_TCSS
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("escape", "focus_input", "输入框", show=False),
        Binding("ctrl+q", "quit", "退出", show=False),
        Binding("ctrl+y", "copy_last_reply", "复制上条", show=False),
        Binding("ctrl+l", "clear_chat", "清屏", show=False),
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

    def on_key(self, event) -> None:
        """Globally intercept keys: palette nav + type-anywhere."""
        # ── Palette navigation (when visible) ──
        try:
            palette = self.query_one("#cmd-palette", CommandPalette)
            if palette.is_visible:
                if event.key == "up":
                    palette.move_up()
                    event.stop()
                    event.prevent_default()
                    return
                elif event.key == "down":
                    palette.move_down()
                    event.stop()
                    event.prevent_default()
                    return
                elif event.key == "tab":
                    if palette.select_current():
                        event.stop()
                        event.prevent_default()
                        return
                elif event.key == "escape":
                    palette.display = False
                    event.stop()
                    event.prevent_default()
                    return
                elif event.key == "enter":
                    if palette.select_current():
                        event.stop()
                        event.prevent_default()
                        return
        except Exception:
            pass

        # ── Type-anywhere: forward printable keys to input ──
        if event.is_printable:
            try:
                inp = self.query_one("#prompt-input", Input)
                if not inp.has_focus:
                    inp.focus()
                    inp.value += event.character
                    inp.cursor_position = len(inp.value)
                    event.stop()
            except Exception:
                pass

    # ── Layout ────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        # ── Scrollable area: chat history + input ──
        yield VerticalScroll(
            # ── ASCII art banner with gradient colors ──
            Static(self._build_banner_markup(), id="banner"),
            # ── Status bar (model info) ──
            Static(self._build_status_markup(), id="status-bar"),
            Static("Type 'exit' or 'quit' to close. Ctrl+N for newline. Select text and press 'c' to copy.", id="help-text"),
            
            Vertical(
                Horizontal(
                    Static("[bold #5fd7ff]❯[/bold #5fd7ff] ", id="prompt-label"),
                    Input(id="prompt-input"),
                    id="prompt-container",
                ),
                CommandPalette(router=self.router, id="cmd-palette"),
                id="input-section",
            ),
            id="chat-history",
        )

        # ── Bottom footer: model info ──
        yield Static(self._build_footer_markup(), id="footer-bar")

    def _build_banner_markup(self) -> str:
        """Build the ASCII art banner with gradient colors as Rich markup."""
        gradient = ["#005fff", "#0087ff", "#00afff", "#00d7d7", "#00d7af", "#5fd7ff"]
        lines = []
        for i, line in enumerate(ASCII_ART):
            color = gradient[i % len(gradient)]
            lines.append(f"[bold {color}]{line}[/bold {color}]")
        return "\n".join(lines)

    def _build_status_markup(self) -> str:
        """Build the status bar: version + current path."""
        import os
        cwd = os.getcwd()
        home = os.path.expanduser("~")
        cwd_short = "~" + cwd[len(home):] if cwd.startswith(home) else cwd
        return (
            f" [#5fd7ff]⚛[/#5fd7ff]  [dim]HEP Agentic Orchestrator[/dim]"
            f" [#00d7af]v{VERSION}[/#00d7af]"
            f"  [dim]│[/dim]  [#0087ff]📂 {cwd_short}[/#0087ff]"
        )

    def _build_footer_markup(self) -> str:
        """Build the bottom footer: model info."""
        provider = self.engine.client.provider
        model = self.engine.client.model_name
        return (
            f"[#777777]model[/#777777] "
            f"[#0087ff]{provider}[/#0087ff] "
            f"[#555555]──[/#555555] "
            f"[#00d7af]{model}[/#00d7af]"
        )

    def on_mount(self) -> None:
        self.query_one("#prompt-input", Input).focus()

    # ── Input handling ────────────────────────────────────────

    def on_input_changed(self, event: Input.Changed) -> None:
        """Show/hide command palette based on input content."""
        try:
            palette = self.query_one("#cmd-palette", CommandPalette)
            value = event.value.strip()
            if value.startswith("/") and " " not in value:
                palette.filter(value)
                container = self.query_one("#chat-history", VerticalScroll)
                container.scroll_end(animate=False)
            else:
                palette.display = False
        except Exception:
            pass

    @on(CommandPalette.Selected)
    def handle_command_palette_selected(self, event: CommandPalette.Selected) -> None:
        """Fill input with selected command from palette."""
        inp = self.query_one("#prompt-input", Input)
        inp.value = event.trigger + " "
        
        # Hide palette and focus input
        palette = self.query_one("#cmd-palette", CommandPalette)
        palette.display = False
        inp.cursor_position = len(inp.value)
        inp.focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter in the input box."""
        user_text = event.value.strip()
        if not user_text:
            return
        if self._generating:
            self.notify("⏳ 正在生成中，请稍候...")
            return

        input_widget = self.query_one("#prompt-input", Input)
        input_widget.value = ""

        # Hide palette on submit
        try:
            self.query_one("#cmd-palette", CommandPalette).display = False
        except Exception:
            pass

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
        target = self.query_one("#input-section", Vertical)
        self._message_count += 1
        msg_id = self._message_count
        self._generating = True
        self._hide_prompt()

        # AI label
        ai_label = Static("✦ Cascade", classes="ai-label")
        await container.mount(ai_label, before=target)

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
            self._show_prompt()
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
            await container.mount(ai_area, before=target)

        container.scroll_end(animate=False)
        self._generating = False
        self._show_prompt()

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
        """Mount a spinner widget before the input section."""
        container = self.query_one("#chat-history", VerticalScroll)
        target = self.query_one("#input-section", Vertical)
        self._spinner = SpinnerWidget(message, classes="spinner")
        await container.mount(self._spinner, before=target)
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
        from rich.text import Text
        container = self.query_one("#chat-history", VerticalScroll)
        target = self.query_one("#input-section", Vertical)
        self._message_count += 1
        
        msg = Static(Text(text), id=f"user-msg-{self._message_count}", classes="user-msg-box")
        msg.border_title = "User"
        
        await container.mount(msg, before=target)
        container.scroll_end(animate=False)

    async def append_system_message(self, text: str, language: str | None = "markdown") -> None:
        """Add a system/info message to the chat history."""
        container = self.query_one("#chat-history", VerticalScroll)
        target = self.query_one("#input-section", Vertical)
        await container.mount(
            CopyableTextArea(text, language=language, classes="message-area system-msg"), before=target,
        )
        container.scroll_end(animate=False)
        self.query_one("#prompt-input", Input).focus()

    async def append_rich_message(self, markup: str) -> None:
        """Add a Rich-markup message as a Static widget (supports colors/emoji)."""
        container = self.query_one("#chat-history", VerticalScroll)
        target = self.query_one("#input-section", Vertical)
        msg = Static(markup, classes="rich-msg")
        await container.mount(msg, before=target)
        container.scroll_end(animate=False)
        self.query_one("#prompt-input", Input).focus()

    async def append_tool_message(
        self, label: str, content: str, css_class: str = "tool-msg"
    ) -> None:
        """Add a tool execution message to the chat history."""
        container = self.query_one("#chat-history", VerticalScroll)
        target = self.query_one("#input-section", Vertical)
        await container.mount(
            Static(f"  {label}", classes="tool-label"), before=target,
        )
        await container.mount(
            CopyableTextArea(content, classes=f"message-area {css_class}"), before=target,
        )
        container.scroll_end(animate=False)

    def update_header(self) -> None:
        """Refresh status bar after model switch."""
        status = self.query_one("#status-bar", Static)
        status.update(self._build_status_markup())



    # ── Actions ───────────────────────────────────────────────

    def _hide_prompt(self) -> None:
        """Hide the ❯ prompt and input during generation."""
        self.query_one("#prompt-container", Horizontal).display = False

    def _show_prompt(self) -> None:
        """Show the ❯ prompt and input, then focus."""
        self.query_one("#prompt-container", Horizontal).display = True
        self.query_one("#prompt-input", Input).focus()
        # Delay scroll_end until after Textual recalculates layout
        self.call_after_refresh(self._scroll_chat_end)

    def _scroll_chat_end(self) -> None:
        """Scroll chat history to bottom (called after layout refresh)."""
        self.query_one("#chat-history", VerticalScroll).scroll_end(animate=False)

    def action_focus_input(self) -> None:
        """Escape: Focus the input box and scroll to it."""
        self.query_one("#prompt-input", Input).focus()
        self.call_after_refresh(self._scroll_chat_end)

    def action_clear_chat(self) -> None:
        """Ctrl+L: Clear chat history, keep input section."""
        container = self.query_one("#chat-history", VerticalScroll)
        for child in list(container.children):
            if child.id != "input-section":
                child.remove()

    def action_copy_last_reply(self) -> None:
        """Ctrl+Y: Copy the last AI reply to clipboard."""
        if not self._last_reply:
            self.notify("ℹ 没有可复制的内容")
            return
            
        try:
            import pyperclip
            pyperclip.copy(self._last_reply)
            self.notify(f"✅ 已复制 {len(self._last_reply)} 字符")
        except Exception:
            self.copy_to_clipboard(self._last_reply)
            self.notify("✅ 已复制 (OSC52)")

    def update_footer(self) -> None:
        """Update the footer text (e.g. after switching models)."""
        try:
            footer = self.query_one("#footer-bar", Static)
            footer.update(self._build_footer_markup())
            self.log("Footer updated")
        except Exception as e:
            self.log(f"Failed to update footer: {e}")

    def open_model_picker(self, engine, current_provider: str, current_model: str) -> None:
        """Open the model picker modal with a callback (no worker needed)."""
        from cascade.ui.model_picker import ModelPickerScreen
        from cascade.services.api_client import ModelClient

        def _on_result(result: dict | None) -> None:
            if result:
                engine.client = ModelClient(provider=result["provider"], model_name=result["model"])
                self.update_footer()
                self.notify(f"✓ Switched to {result['display']}")
            else:
                self.notify("ℹ Cancelled")
            self.query_one("#prompt-input", Input).focus()

        self.push_screen(ModelPickerScreen(current_provider, current_model), callback=_on_result)
