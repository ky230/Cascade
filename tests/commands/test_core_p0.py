import pytest
from unittest.mock import MagicMock, AsyncMock
from cascade.commands.base import CommandContext
from cascade.commands.core.help import HelpCommand
from cascade.commands.core.exit import ExitCommand
from cascade.commands.core.clear import ClearCommand
from cascade.commands.router import CommandRouter


@pytest.fixture
def ctx():
    """Minimal mock context simulating Textual mode (console=None)."""
    repl = MagicMock()
    repl.router = CommandRouter()
    repl.router.register(HelpCommand())
    repl.router.register(ExitCommand())
    repl.router.register(ClearCommand())
    repl.append_system_message = AsyncMock()
    repl.append_rich_message = AsyncMock()

    engine = MagicMock()
    engine.messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"},
    ]

    return CommandContext(
        console=None,
        engine=engine,
        session=None,
        repl=repl,
    )


@pytest.mark.asyncio
async def test_help_runs_without_error(ctx):
    cmd = HelpCommand()
    await cmd.execute(ctx, "")
    ctx.repl.append_rich_message.assert_called_once()


@pytest.mark.asyncio
async def test_help_output_contains_commands(ctx):
    """Help output should include registered command names."""
    cmd = HelpCommand()
    await cmd.execute(ctx, "")
    output_text = ctx.repl.append_rich_message.call_args[0][0]
    assert "/help" in output_text
    assert "/exit" in output_text
    assert "/clear" in output_text


@pytest.mark.asyncio
async def test_exit_calls_app_exit(ctx):
    """In Textual mode, /exit calls repl.exit() instead of SystemExit."""
    cmd = ExitCommand()
    await cmd.execute(ctx, "")
    ctx.repl.exit.assert_called_once()


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
