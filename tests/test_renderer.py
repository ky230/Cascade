import pytest
from unittest.mock import MagicMock
from cascade.ui.renderer import MessageRenderer

def test_renderer_assistant_print():
    mock_console = MagicMock()
    renderer = MessageRenderer(mock_console)
    renderer.render_assistant("Hello **bold**")
    
    # Assert console.print called at least once (header + markdown)
    assert mock_console.print.call_count >= 2


def test_render_tool_use():
    """Renderer should format tool invocations."""
    from io import StringIO
    from rich.console import Console
    from cascade.ui.renderer import MessageRenderer

    console = Console(file=StringIO(), force_terminal=True, width=80)
    renderer = MessageRenderer(console)

    # Should not raise
    renderer.render_tool_start("bash", {"command": "ls -la"})
    renderer.render_tool_end("bash", "file1.txt\nfile2.txt")

    output = console.file.getvalue()
    assert "bash" in output.lower()
