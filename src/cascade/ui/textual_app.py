"""Cascade TUI — Textual full-screen application.

Replaces the old Rich+prompt_toolkit CascadeRepl with a proper
alternate-screen Textual App that handles:
  - Infinite scrollback via VerticalScroll
  - No resize artifacts (Textual manages alternate buffer)
  - Text selection + copy via CopyableTextArea + pyperclip
  - Message queue for non-blocking input during generation
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from cascade.ui.message_queue import MessageQueueManager, QueuedCommand
from cascade.ui.query_guard import QueryGuard
from cascade.ui.queue_processor import process_queue_if_ready

logger = logging.getLogger(__name__)

from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Horizontal, Vertical
from textual.widgets import Footer, Static, Input, Label
from cascade.ui.widgets import PromptInput
from cascade.ui.model_palette import ModelPalette
from textual.binding import Binding
from textual import on, events

from cascade.engine.query import QueryEngine, QueryEngineConfig
from cascade.state.store import Store
from cascade.tools.registry import ToolRegistry
from cascade.permissions.engine import PermissionEngine, PermissionMode
from cascade.tools.bash_tool import BashTool
from cascade.tools.file_tools import FileReadTool, FileWriteTool
from cascade.tools.search_tools import GrepTool, GlobTool
from cascade.bootstrap.system_prompt import build_system_prompt
from cascade.commands import CommandRouter, CommandContext
from cascade.ui.widgets import CopyableTextArea, SpinnerWidget, CopyableStatic, QueuePreview
from cascade.ui.command_palette import CommandPalette
from cascade.ui.styles import CASCADE_TCSS
from cascade.ui.banner import VERSION, ASCII_ART, _LOGO, _L, _R


class CascadeApp(App):
    """Cascade full-screen TUI."""

    CSS = CASCADE_TCSS
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("escape", "cancel_or_focus", "Cancel / Focus input", show=False),
        Binding("ctrl+c", "quit", "Quit", show=False, priority=True),
        Binding("ctrl+y", "copy_last_reply", "Copy last reply", show=False),
        Binding("ctrl+l", "clear_chat", "Clear chat", show=False),
    ]

    # Commands that execute immediately even during generation (bypass queue)
    IMMEDIATE_COMMANDS = frozenset({"/model", "/help", "/config", "/clear", "/status"})

    def __init__(self, client, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self._message_count = 0
        self._last_reply = ""
        self._spinner: Optional[SpinnerWidget] = None
        self._permission_future: Optional[asyncio.Future] = None

        # ── Message Queue & Query Guard (replaces old _generating bool) ──
        self._input_queue = MessageQueueManager()
        self._query_guard = QueryGuard()

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
        """Globally intercept keys: palette nav + type-anywhere.

        Note: Enter is handled exclusively by PromptInput._on_key.
        This handler only manages palette navigation (↑↓/Tab/Esc).
        """
        # ── Palette navigation (when visible) ──
        try:
            palette = self.query_one("#cmd-palette", CommandPalette)
            if palette.display:
                if event.key in ("up", "down", "tab", "escape"):
                    event.stop()
                    event.prevent_default()

                    if event.key == "up":
                        palette.move_up()
                        return
                    elif event.key == "down":
                        palette.move_down()
                        return
                    elif event.key == "tab":
                        if not palette._matches:
                            return
                        trigger = palette._matches[palette._highlight]["trigger"]
                        palette.display = False
                        inp = self.query_one("#prompt-input", PromptInput)
                        inp.text = trigger + " "
                        inp.action_cursor_line_end()
                        inp.focus()
                        return
                    elif event.key == "escape":
                        palette.display = False
                        return
        except Exception:
            pass

        # ── Model palette navigation (when visible) ──
        try:
            model_palette = self.query_one("#model-palette", ModelPalette)
            if model_palette.display:
                if event.key in ("up", "down", "escape"):
                    event.stop()
                    event.prevent_default()

                    if event.key == "up":
                        model_palette.move_up()
                        return
                    elif event.key == "down":
                        model_palette.move_down()
                        return
                    elif event.key == "escape":
                        model_palette.cancel()
                        return
        except Exception:
            pass

        # ── Type-anywhere: forward printable keys to input ──
        if event.is_printable:
            try:
                inp = self.query_one("#prompt-input", PromptInput)
                if not inp.has_focus:
                    inp.focus()
                    inp.insert(event.character)
                    inp.action_cursor_line_end()
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
                QueuePreview(id="queue-preview"),
                Horizontal(
                    Static("[bold #5fd7ff]❯[/bold #5fd7ff] ", id="prompt-label"),
                    PromptInput(id="prompt-input"),
                    Label("Cascade standby. Enter prompt or /command...", id="prompt-placeholder"),
                    id="prompt-container",
                ),
                CommandPalette(router=self.router, id="cmd-palette"),
                ModelPalette(id="model-palette"),
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
        self.query_one("#prompt-input", PromptInput).focus()

    # ── Input handling ────────────────────────────────────────

    @on(events.Click, "#prompt-placeholder")
    def on_placeholder_click(self, event: events.Click) -> None:
        """Forward clicks on the placeholder strictly to the input field."""
        self.query_one("#prompt-input").focus()
        event.stop()

    @on(PromptInput.Changed)
    def on_input_changed(self, event: PromptInput.Changed) -> None:
        """Show/hide command palette based on input content, and manage placeholder."""
        try:
            value = event.text_area.text if hasattr(event, "text_area") else getattr(event, "value", "")
            # Toggle placeholder visibility
            placeholder = self.query_one("#prompt-placeholder")
            placeholder.display = len(value) == 0

            palette = self.query_one("#cmd-palette", CommandPalette)
            if value.startswith("/") and " " not in value:
                palette.filter(value.strip())
                container = self.query_one("#chat-history", VerticalScroll)
                container.scroll_end(animate=False)
            else:
                palette.display = False
        except Exception:
            pass

    @on(CommandPalette.Selected)
    def handle_command_palette_selected(self, event: CommandPalette.Selected) -> None:
        """Fill input with selected command from palette and execute immediately."""
        inp = self.query_one("#prompt-input", PromptInput)
        palette = self.query_one("#cmd-palette", CommandPalette)
        palette.display = False
        inp.text = event.trigger
        inp.post_message(PromptInput.Submitted(inp, event.trigger))

    @on(PromptInput.Submitted)
    async def on_input_submitted(self, event: PromptInput.Submitted) -> None:
        """Handle Enter in the input box.

        Three-tier dispatch (mirrors Claude Code handlePromptSubmit.ts):
          1. Permission gate (y/n during tool approval)
          2. Immediate commands bypass queue entirely
          3. If generating → enqueue
          4. Normal execution (idle state)
        """
        user_text = event.value.strip()
        if not user_text:
            return

        # ── Permission gate: if waiting for y/n, resolve the future ──
        if self._permission_future and not self._permission_future.done():
            input_widget = self.query_one("#prompt-input", PromptInput)
            input_widget.text = ""
            approved = (user_text.lower() == "y")
            self._permission_future.set_result(approved)
            if approved:
                await self.append_rich_message("[green]✓ Approved[/green]")
            else:
                await self.append_rich_message("[red]✗ Denied[/red]")
            return

        input_widget = self.query_one("#prompt-input", PromptInput)

        # ── Step 1: Immediate commands bypass queue entirely ──
        if user_text.startswith("/"):
            cmd_name = user_text.split()[0]
            if cmd_name in self.IMMEDIATE_COMMANDS and self._query_guard.is_active:
                input_widget.add_to_history(user_text)
                input_widget.text = ""
                await self._execute_immediate_command(user_text)
                return

        # ── Step 2: If generating, enqueue ──
        if self._query_guard.is_active:
            cmd = QueuedCommand(
                value=user_text,
                mode="slash" if user_text.startswith("/") else "prompt",
                priority="next",
            )
            self._input_queue.enqueue(cmd)
            input_widget.add_to_history(user_text)
            input_widget.text = ""
            self._update_queue_preview()
            logger.debug("Enqueued: %s", user_text[:80])
            return

        # ── Step 3: Normal execution (idle state) ──
        # Reserve dispatching state to prevent race conditions
        # between submission and _run_generation's try_start().
        if not self._query_guard.reserve():
            # Shouldn't happen (we checked is_active above), but guard anyway
            logger.warning("on_input_submitted: reserve() failed unexpectedly")
            return

        input_widget.add_to_history(user_text)
        input_widget.text = ""

        # Hide palette on submit
        try:
            self.query_one("#cmd-palette", CommandPalette).display = False
        except Exception:
            pass

        try:
            await self._execute_prompt(user_text)
        finally:
            # cancel_reservation is a no-op if try_start() already moved to running
            self._query_guard.cancel_reservation()

    async def _execute_immediate_command(self, user_text: str) -> None:
        """Execute an immediate command that bypasses the queue.

        These commands run even during generation (e.g. /model, /help, /clear).
        """
        # Hide palette
        try:
            self.query_one("#cmd-palette", CommandPalette).display = False
        except Exception:
            pass

        await self.append_user_message(user_text)
        cmd_ctx = CommandContext(
            engine=self.engine,
            repl=self,
        )
        handled = await self.router.dispatch(user_text, cmd_ctx)
        if not handled:
            await self.append_system_message(
                f"Unknown command: {user_text.split()[0]}. Type /help for available commands."
            )

    async def _execute_prompt(self, user_text: str) -> None:
        """Execute a single direct submission (slash or prompt).

        Handles the full flow: slash routing → API generation.
        """
        # ── Slash command routing ──
        if user_text.startswith("/"):
            await self.append_user_message(user_text)
            cmd_ctx = CommandContext(
                engine=self.engine,
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
        self.run_worker(self._run_generation(user_text), exclusive=True)

    async def _execute_queued_input(self, commands: list[QueuedCommand]) -> None:
        """Execute dequeued commands (called by queue processor).

        The processor guarantees:
          - Slash commands arrive one at a time
          - Non-slash prompts arrive as a batch (same mode)
        So we don't need to mix slash/non-slash handling here.
        """
        if not commands:
            return

        # Check if the first command is a slash command (processor sends these individually)
        if MessageQueueManager.is_slash_command(commands[0]):
            # _execute_prompt renders the user message internally, no pre-render needed
            await self._execute_prompt(commands[0].value)
            return

        # Non-slash batch: render all user messages, then single generation
        for cmd in commands:
            await self.append_user_message(cmd.value)

        combined = "\n\n".join(c.value for c in commands)
        self.run_worker(self._run_generation(combined), exclusive=True)

    # ── AI Generation with streaming ─────────────────────────

    async def _run_generation(self, user_text: str) -> None:
        """Submit to QueryEngine with streaming callbacks.

        Uses QueryGuard state machine to prevent race conditions.
        On completion, checks the queue for pending commands.
        """
        generation = self._query_guard.try_start()
        if generation is None:
            logger.warning("_run_generation: QueryGuard already running, skipping")
            return

        container = self.query_one("#chat-history", VerticalScroll)
        target = self.query_one("#input-section", Vertical)
        self._message_count += 1
        msg_id = self._message_count
        # Prompt stays visible during generation (non-blocking input for queue)
        self._set_prompt_generating(True)

        try:
            # AI label
            ai_label = Static("✦ Cascade", classes="ai-label")
            await container.mount(ai_label, before=target)

            # Spinner
            await self._show_spinner("Generating")
            container.scroll_end(animate=False)

            tokens: list[str] = []

            def on_token(t: str) -> None:
                tokens.append(t)

            async def on_tool_start(name: str, args: dict) -> None:
                await self._handle_tool_start(name, args)

            async def on_tool_end(name: str, tool_result) -> None:
                await self._handle_tool_end(name, tool_result)

            async def ask_user(prompt_msg: str) -> bool:
                """Show permission prompt and wait for user y/n input."""
                await self._remove_spinner()

                loop = asyncio.get_event_loop()
                self._permission_future = loop.create_future()

                await self.append_rich_message(
                    f"[bold yellow]⚠️ Permission Request[/bold yellow]\n"
                    f"[dim]{prompt_msg}[/dim]\n"
                    f"[bold]Enter [green]y[/green] to approve, anything else to deny:[/bold]"
                )
                # Prompt is already visible; just ensure focus for y/n input
                self._set_prompt_generating(False)  # Show ❯ for permission input
                self.query_one("#prompt-input", PromptInput).focus()
                try:
                    result = await self._permission_future
                finally:
                    self._permission_future = None
                    # Restore generating indicator and resume spinner
                    self._set_prompt_generating(True)
                    await self._show_spinner("Generating")
                return result

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
                return

            # ── Render response BEFORE transitioning guard state ──
            await self._remove_spinner()

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

            # ── QueryGuard lifecycle: transition back to idle + check queue ──
            if self._query_guard.end(generation):
                self._update_queue_preview()
                process_queue_if_ready(
                    self._input_queue,
                    self._execute_queued_input,
                )

        finally:
            # Safety net: ALWAYS restore prompt label and release guard,
            # even if rendering crashes or worker is cancelled.
            if self._query_guard.is_running:
                self._query_guard.force_end()
            self._set_prompt_generating(False)
            self.query_one("#prompt-input", PromptInput).focus()
            self._scroll_chat_end()

    async def _handle_tool_start(self, name: str, args: dict) -> None:
        """Async callback for tool start — await UI updates."""
        await self._remove_spinner()
        args_preview = str(args)
        if len(args_preview) > 200:
            args_preview = args_preview[:200] + "..."
        await self.append_tool_message(f"⚙ {name}", args_preview, css_class="tool-msg")
        await self._show_spinner("Executing")

    async def _handle_tool_end(self, name: str, tool_result) -> None:
        """Async callback for tool end — await UI updates."""
        await self._remove_spinner()
        output = tool_result.output if hasattr(tool_result, 'output') else str(tool_result)
        is_error = tool_result.is_error if hasattr(tool_result, 'is_error') else False
        display = output[:500] + "\n..." if len(output) > 500 else output
        label = f"✗ Error: {name}" if is_error else f"✓ Result: {name}"
        css_class = "tool-msg-error" if is_error else "tool-msg"
        await self.append_tool_message(label, display, css_class=css_class)
        # Only show spinner if the tool succeeded (more rounds expected).
        if not is_error:
            await self._show_spinner("Generating")

    # ── Spinner management ────────────────────────────────────

    async def _show_spinner(self, message: str = "Thinking") -> None:
        """Mount a spinner widget before the input section."""
        await self._remove_spinner()  # Prevent orphan spinners
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

        container = self.query_one("#chat-history", VerticalScroll)
        target = self.query_one("#input-section", Vertical)
        self._message_count += 1
        
        formatted_text = "[#5fd7ff]❯[/] " + text
        msg = CopyableStatic(formatted_text, id=f"user-msg-{self._message_count}", classes="user-msg-box")
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
        self.query_one("#prompt-input", PromptInput).focus()

    async def append_rich_message(self, markup: str) -> None:
        """Add a Rich-markup message as a Static widget (supports colors/emoji)."""
        container = self.query_one("#chat-history", VerticalScroll)
        target = self.query_one("#input-section", Vertical)
        msg = CopyableStatic(markup, classes="rich-msg system-msg")
        await container.mount(msg, before=target)
        container.scroll_end(animate=False)
        self.query_one("#prompt-input", PromptInput).focus()

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

    # ── Queue preview helper ────────────────────────────────

    def _update_queue_preview(self) -> None:
        """Update the persistent queue preview widget."""
        try:
            preview = self.query_one("#queue-preview", QueuePreview)
            preview.force_refresh()
        except Exception:
            # Fallback: use notify if widget not found
            if self._input_queue.has_commands:
                count = self._input_queue.length
                self.notify(f"📥 {count} queued message{'s' if count > 1 else ''}", timeout=2.0)

    # ── Actions ───────────────────────────────────────────────

    def _set_prompt_generating(self, generating: bool) -> None:
        """Toggle prompt visual indicator between idle (❯) and generating (⏳).

        The prompt container is ALWAYS visible — users can type during
        generation and their input will be queued automatically.
        """
        try:
            label = self.query_one("#prompt-label", Static)
            if generating:
                label.update("[bold #ffd700]⏳[/bold #ffd700] ")
            else:
                label.update("[bold #5fd7ff]❯[/bold #5fd7ff] ")
        except Exception:
            pass

    def _show_prompt(self) -> None:
        """Ensure prompt is visible, focused, and scrolled to bottom.

        Used after ESC cancel and other state transitions where
        we need to guarantee prompt accessibility.
        """
        container = self.query_one("#prompt-container", Horizontal)
        container.display = True
        inp = self.query_one("#prompt-input", PromptInput)
        inp.disabled = False

        def _do_focus():
            inp.focus()
            self._scroll_chat_end()
        self.call_after_refresh(_do_focus)

    def _scroll_chat_end(self) -> None:
        """Scroll chat history to bottom (called after layout refresh)."""
        self.query_one("#chat-history", VerticalScroll).scroll_end(animate=False)

    def action_cancel_or_focus(self) -> None:
        """ESC handler with layered priority. Mirrors Claude Code's useCancelRequest.

        Priority 1: Cancel active generation (abort)
        Priority 2: Pop queue into input for editing (idle + queue non-empty)
        Priority 3: Focus input (fallback)
        """
        # Priority 1: Cancel active generation
        if self._query_guard.is_running:
            self._query_guard.force_end()
            # NOTE: Queue is intentionally NOT cleared here.
            # Per Claude Code spec, clearCommandQueue() only fires on killAgents
            # (double-ESC), not on a single ESC cancel.
            self._update_queue_preview()
            self.notify("⛔ Generation cancelled", timeout=2.0)
            asyncio.ensure_future(self._remove_spinner())
            self._show_prompt()
            return

        # Priority 2: Pop queue into input for editing (idle + queue non-empty)
        if self._input_queue.has_commands:
            inp = self.query_one("#prompt-input", PromptInput)
            result = self._input_queue.pop_all_editable(
                inp.text,
                len(inp.text),
            )
            if result:
                inp.text = result.text
                inp.action_cursor_line_end()
                self._update_queue_preview()
                self.notify("📝 Queue popped to input for editing", timeout=2.0)
                return

        # Priority 3: Fallback — just focus input
        self.query_one("#prompt-input", PromptInput).focus()
        self.call_after_refresh(self._scroll_chat_end)

    def action_clear_chat(self) -> None:
        """Ctrl+L: Clear chat history, keep banner and input section."""
        container = self.query_one("#chat-history", VerticalScroll)
        preserved_ids = {"input-section", "banner", "status-bar", "help-text"}
        for child in list(container.children):
            if child.id not in preserved_ids:
                child.remove()

    def action_copy_last_reply(self) -> None:
        """Ctrl+Y: Copy the last AI reply to clipboard."""
        if not self._last_reply:
            self.notify("ℹ Nothing to copy")
            return
            
        try:
            import pyperclip
            pyperclip.copy(self._last_reply)
            self.notify(f"✅ Copied {len(self._last_reply)} chars")
        except Exception:
            self.copy_to_clipboard(self._last_reply)
            self.notify("✅ Copied (OSC52)")

    def update_footer(self) -> None:
        """Update the footer text (e.g. after switching models)."""
        try:
            footer = self.query_one("#footer-bar", Static)
            footer.update(self._build_footer_markup())
            self.log("Footer updated")
        except Exception as e:
            self.log(f"Failed to update footer: {e}")

    def show_model_palette(self) -> None:
        """Show the inline model picker palette below the input."""
        palette = self.query_one("#model-palette", ModelPalette)
        palette.populate(
            current_provider=self.engine.client.provider,
            current_model=self.engine.client.model_name,
        )
        # Scroll to bottom so palette is visible
        container = self.query_one("#chat-history", VerticalScroll)
        container.scroll_end(animate=False)



    @on(ModelPalette.Selected)
    def handle_model_selected(self, event: ModelPalette.Selected) -> None:
        """Apply model switch from the inline palette."""
        from cascade.services.api_client import ModelClient
        self.engine.client = ModelClient(provider=event.provider, model_name=event.model_id)
        self.update_footer()
        self.notify(f"✅ Switched to {event.display_name}")
        self.query_one("#prompt-input", PromptInput).focus()
