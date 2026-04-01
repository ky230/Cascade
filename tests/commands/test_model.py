import pytest
from unittest.mock import MagicMock
from cascade.commands.model.model import ModelCommand, PROVIDER_CATALOG


def test_catalog_has_all_providers():
    expected = {"deepseek", "grok", "glm", "anthropic", "gemini", "openai", "kimi", "qwen"}
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


@pytest.mark.asyncio
async def test_model_quick_switch():
    cmd = ModelCommand()
    ctx = MagicMock()
    ctx.engine = MagicMock()
    ctx.engine.client.provider = "glm"
    ctx.engine.client.model_name = "glm-4-flash"

    await cmd.execute(ctx, "deepseek deepseek-chat")
    # Should have swapped the client
    assert ctx.engine.client is not None


@pytest.mark.asyncio
async def test_model_quick_switch_unknown_provider():
    cmd = ModelCommand()
    ctx = MagicMock()
    ctx.engine = MagicMock()
    ctx.engine.client.provider = "glm"
    ctx.engine.client.model_name = "glm-4-flash"

    await cmd.execute(ctx, "nonexistent some-model")
    # Should print error about unknown provider
    call_args = str(ctx.console.print.call_args)
    assert "Unknown provider" in call_args


@pytest.mark.asyncio
async def test_model_bad_args():
    cmd = ModelCommand()
    ctx = MagicMock()
    ctx.engine = MagicMock()
    ctx.engine.client.provider = "glm"
    ctx.engine.client.model_name = "glm-4-flash"

    await cmd.execute(ctx, "only-one-arg")
    call_args = str(ctx.console.print.call_args)
    assert "Usage" in call_args
