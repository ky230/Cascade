import pytest
from unittest.mock import MagicMock
from cascade.ui.renderer import MessageRenderer

def test_renderer_assistant_print():
    mock_console = MagicMock()
    renderer = MessageRenderer(mock_console)
    renderer.render_assistant("Hello **bold**")
    
    # Assert console.print called at least once (header + markdown)
    assert mock_console.print.call_count >= 2

def test_renderer_tool_print():
    mock_console = MagicMock()
    renderer = MessageRenderer(mock_console)
    renderer.render_tool_result("bash", "result_string")
    assert mock_console.print.call_count >= 1
