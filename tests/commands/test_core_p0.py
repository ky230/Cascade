import pytest
from unittest.mock import MagicMock
from cascade.commands.core.help import HelpCommand
from cascade.commands.core.exit import ExitCommand
from cascade.commands.core.clear import ClearCommand
from cascade.commands.router import CommandRouter


@pytest.fixture
def ctx():
    """Minimal mock context for P0 command tests."""
    mock = MagicMock()
    mock.console = MagicMock()
    mock.engine = MagicMock()
    mock.engine.messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"},
    ]
    mock.repl = MagicMock()
    mock.repl.router = CommandRouter()
    mock.repl.router.register(HelpCommand())
    mock.repl.router.register(ExitCommand())
    mock.repl.router.register(ClearCommand())
    return mock


@pytest.mark.asyncio
async def test_help_runs_without_error(ctx):
    cmd = HelpCommand()
    await cmd.execute(ctx, "")
    ctx.console.print.assert_called()


@pytest.mark.asyncio
async def test_help_shows_registered_commands(ctx):
    """Help should call console.print with content that includes command names."""
    cmd = HelpCommand()
    await cmd.execute(ctx, "")
    # At least the table + tip = 2 print calls
    assert ctx.console.print.call_count >= 2


@pytest.mark.asyncio
async def test_exit_raises_system_exit(ctx):
    cmd = ExitCommand()
    with pytest.raises(SystemExit):
        await cmd.execute(ctx, "")
    ctx.console.print.assert_called()


@pytest.mark.asyncio
async def test_clear_keeps_system_prompt(ctx):
    cmd = ClearCommand()
    await cmd.execute(ctx, "")
    assert len(ctx.engine.messages) == 1
    assert ctx.engine.messages[0]["role"] == "system"


@pytest.mark.asyncio
async def test_clear_empty_history(ctx):
    ctx.engine.messages = []
    cmd = ClearCommand()
    await cmd.execute(ctx, "")
    assert len(ctx.engine.messages) == 0


@pytest.mark.asyncio
async def test_clear_no_system_prompt(ctx):
    ctx.engine.messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"},
    ]
    cmd = ClearCommand()
    await cmd.execute(ctx, "")
    assert len(ctx.engine.messages) == 0
