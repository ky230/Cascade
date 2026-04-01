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

    def render_tool_use(self, tool_name: str, input_summary: str) -> None:
        self.console.print(Panel(
            f"[dim]{input_summary}[/dim]",
            title=f"[bold yellow]⚡ {tool_name}[/bold yellow]",
            border_style="dim", expand=False,
        ))

    def render_tool_result(self, tool_name: str, output: str, is_error: bool = False) -> None:
        style = "red" if is_error else "green"
        icon = "✗" if is_error else "✓"
        self.console.print(Panel(
            output[:500] + ("..." if len(output) > 500 else ""),
            title=f"[{style}]{icon} {tool_name}[/{style}]",
            border_style="dim", expand=False,
        ))
