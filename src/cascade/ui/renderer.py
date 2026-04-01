from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

class MessageRenderer:
    def __init__(self, console: Console):
        self.console = console

    def render_assistant(self, content: str) -> None:
        self.console.print()
        self.console.print("[bold #5fd7ff]✦ Cascade[/bold #5fd7ff]")
        self.console.print()
        self.console.print(Markdown(content))
        self.console.print()

    def render_tool_start(self, tool_name: str, tool_input: dict) -> None:
        """Show that a tool is about to execute."""
        input_preview = str(tool_input)
        if len(input_preview) > 120:
            input_preview = input_preview[:120] + "..."
        self.console.print(
            Panel(
                f"[dim]{input_preview}[/dim]",
                title=f"⚙ {tool_name}",
                title_align="left",
                border_style="yellow",
                expand=False,
            )
        )

    def render_tool_end(self, tool_name: str, output: str, is_error: bool = False) -> None:
        """Show the result of a tool execution."""
        style = "red" if is_error else "green"
        label = "✗ Error" if is_error else "✓ Result"
        display = output if len(output) <= 500 else output[:500] + "\n..."
        self.console.print(
            Panel(
                display,
                title=f"{label}: {tool_name}",
                title_align="left",
                border_style=style,
                expand=False,
            )
        )
