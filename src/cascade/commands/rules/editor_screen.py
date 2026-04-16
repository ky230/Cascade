"""Textual Screen for rules file selection and inline editing.

Uses OptionList for file selection and TextArea for mouse-friendly editing.
Hot-reloads system prompt on save via engine.set_system_prompt().
"""
import os
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import OptionList, TextArea, Static
from textual.binding import Binding


class RulesEditorScreen(Screen):
    """Two-phase screen: select file -> edit in TextArea."""

    BINDINGS = [
        Binding("escape", "cancel", "Back / Cancel"),
        Binding("ctrl+s", "save", "Save & Reload"),
    ]

    CSS = """
    RulesEditorScreen {
        background: $surface;
    }
    #rules-title {
        margin: 1 2;
    }
    #file-list {
        height: auto;
        max-height: 12;
        margin: 1 2;
    }
    #editor-area {
        height: 1fr;
        margin: 0 2 1 2;
    }
    #rules-status-bar {
        height: 1;
        dock: bottom;
        background: $accent;
        color: $text;
        padding: 0 2;
    }
    """

    def __init__(self, files: list[dict], engine) -> None:
        super().__init__()
        self.files = files
        self.engine = engine
        self.current_path: str | None = None
        self.editing = False

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold]CASCADE.md Rules[/bold]  Select a file to edit:\n",
            id="rules-title",
        )
        option_list = OptionList(id="file-list")
        for f in self.files:
            status = f"● {f['size']} bytes" if f["exists"] else "○ (create new)"
            option_list.add_option(
                f"[{f['level'].title()}]  {f['path']}  {status}"
            )
        yield option_list
        yield TextArea(
            id="editor-area",
            language="markdown",
            show_line_numbers=True,
        )
        yield Static(
            "↑↓ Select · Enter Edit · Ctrl+S Save · Esc Cancel",
            id="rules-status-bar",
        )

    def on_mount(self) -> None:
        # Hide editor until a file is selected
        self.query_one("#editor-area", TextArea).display = False

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        """User selected a file — load it into TextArea."""
        file_info = self.files[event.option_index]
        self.current_path = file_info["path"]

        # Read or create content
        if file_info["exists"]:
            with open(self.current_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        else:
            # Create parent dirs + default content
            os.makedirs(os.path.dirname(self.current_path), exist_ok=True)
            content = "# CASCADE Rules\n\n<!-- Add project-specific rules here -->\n"

        # Show editor
        editor = self.query_one("#editor-area", TextArea)
        editor.load_text(content)
        editor.display = True
        editor.focus()
        self.editing = True

        # Hide file list
        self.query_one("#file-list", OptionList).display = False
        self.query_one("#rules-title", Static).update(
            f"[bold]Editing:[/bold] {self.current_path}\n"
        )
        self.query_one("#rules-status-bar", Static).update(
            "Ctrl+S Save & Reload · Esc Cancel"
        )

    def action_save(self) -> None:
        """Save file and hot-reload system prompt."""
        if not self.current_path or not self.editing:
            return

        editor = self.query_one("#editor-area", TextArea)
        content = editor.text

        # Write to disk
        os.makedirs(os.path.dirname(self.current_path), exist_ok=True)
        with open(self.current_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Hot-reload system prompt
        from cascade.bootstrap.system_prompt import build_system_prompt
        self.engine.set_system_prompt(build_system_prompt())

        # Return to chat with notification
        self.app.pop_screen()
        self.app.notify(
            f"✓ Saved & reloaded: {self.current_path}",
            title="Rules Updated",
            timeout=5,
        )

    def action_cancel(self) -> None:
        """Cancel editing / go back."""
        if self.editing:
            # Back to file list
            self.editing = False
            self.current_path = None
            self.query_one("#editor-area", TextArea).display = False
            self.query_one("#file-list", OptionList).display = True
            self.query_one("#rules-title", Static).update(
                "[bold]CASCADE.md Rules[/bold]  Select a file to edit:\n"
            )
            self.query_one("#rules-status-bar", Static).update(
                "↑↓ Select · Enter Edit · Ctrl+S Save · Esc Cancel"
            )
        else:
            # Exit screen entirely
            self.app.pop_screen()
