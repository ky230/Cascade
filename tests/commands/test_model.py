import pytest
from unittest.mock import MagicMock, AsyncMock
from cascade.commands.base import CommandContext
from cascade.commands.model.model import ModelCommand, PROVIDER_CATALOG


def test_catalog_has_all_providers():
    expected = {"deepseek", "grok", "glm", "anthropic", "gemini", "openai", "kimi", "qwen", "minimax"}
    assert set(PROVIDER_CATALOG.keys()) == expected


def test_each_provider_has_models():
    for prov, info in PROVIDER_CATALOG.items():
        assert len(info["models"]) > 0, f"{prov} has no models"
        assert "env_key" in info
        assert "display" in info


def test_each_model_has_required_fields():
    for prov, info in PROVIDER_CATALOG.items():
        for m in info["models"]:
            assert "id" in m, f"{prov} model missing 'id'"
            assert "label" in m, f"{prov} model missing 'label'"
            assert "price" in m, f"{prov} model missing 'price'"


@pytest.fixture
def model_ctx():
    repl = MagicMock()
    repl.append_system_message = AsyncMock()
    engine = MagicMock()
    engine.client.provider = "glm"
    engine.client.model_name = "glm-4-flash"
    return CommandContext(console=None, engine=engine, session=None, repl=repl)


@pytest.mark.asyncio
async def test_model_quick_switch(model_ctx):
    cmd = ModelCommand()
    await cmd.execute(model_ctx, "deepseek deepseek-chat")
    # Should have swapped the client
    assert model_ctx.engine.client is not None


@pytest.mark.asyncio
async def test_model_quick_switch_unknown_provider(model_ctx):
    cmd = ModelCommand()
    await cmd.execute(model_ctx, "nonexistent some-model")
    output = model_ctx.repl.append_system_message.call_args[0][0]
    assert "Unknown provider" in output


@pytest.mark.asyncio
async def test_model_bad_args(model_ctx):
    cmd = ModelCommand()
    await cmd.execute(model_ctx, "only-one-arg")
    output = model_ctx.repl.append_system_message.call_args[0][0]
    assert "Usage" in output


@pytest.mark.asyncio
async def test_model_numbered_selection(model_ctx):
    cmd = ModelCommand()
    await cmd.execute(model_ctx, "1")
    output = model_ctx.repl.append_system_message.call_args[0][0]
    assert "Switched to" in output


@pytest.mark.asyncio
async def test_model_display_table(model_ctx):
    cmd = ModelCommand()
    await cmd.execute(model_ctx, "")
    output = model_ctx.repl.append_system_message.call_args[0][0]
    assert "Switch Model" in output
    assert "current" in output
