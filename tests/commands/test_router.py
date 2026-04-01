import pytest
from cascade.commands.base import BaseCommand, CommandContext
from cascade.commands.router import CommandRouter


class FakeCommand(BaseCommand):
    name = "fake"
    description = "A fake command for testing"
    aliases = ["/f"]
    category = "Test"

    async def execute(self, ctx, args):
        ctx._executed = True
        ctx._args = args


@pytest.fixture
def router():
    r = CommandRouter()
    r.register(FakeCommand())
    return r


def test_register_and_lookup(router):
    assert router.get("/fake") is not None
    assert router.get("/f") is not None
    assert router.get("/nonexistent") is None


def test_all_commands_deduped(router):
    cmds = router.all_commands
    assert len(cmds) == 1


def test_completer_is_slash_completer(router):
    from cascade.commands.router import SlashCompleter
    completer = router.get_completer()
    assert isinstance(completer, SlashCompleter)


def test_completer_yields_on_slash(router):
    from prompt_toolkit.document import Document
    completer = router.get_completer()
    # Typing just "/" should show all commands
    doc = Document("/", cursor_position=1)
    completions = list(completer.get_completions(doc, None))
    assert len(completions) >= 1
    texts = [c.text for c in completions]
    assert "/fake" in texts


def test_completer_filters_on_partial(router):
    from prompt_toolkit.document import Document
    completer = router.get_completer()
    # Typing "/fa" should match "/fake"
    doc = Document("/fa", cursor_position=3)
    completions = list(completer.get_completions(doc, None))
    assert len(completions) == 1
    assert completions[0].text == "/fake"


def test_completer_silent_on_normal_text(router):
    from prompt_toolkit.document import Document
    completer = router.get_completer()
    # Normal text should NOT trigger completions
    doc = Document("hello", cursor_position=5)
    completions = list(completer.get_completions(doc, None))
    assert len(completions) == 0


def test_commands_by_category(router):
    groups = router.get_commands_by_category()
    assert "Test" in groups
    assert len(groups["Test"]) == 1


def test_hidden_command_excluded_from_help():
    class HiddenCmd(BaseCommand):
        name = "secret"
        description = "Hidden"
        hidden = True
        category = "Test"
        async def execute(self, ctx, args):
            pass

    router = CommandRouter()
    router.register(HiddenCmd())
    groups = router.get_commands_by_category()
    assert "Test" not in groups  # hidden command should not appear


@pytest.mark.asyncio
async def test_dispatch_known():
    router = CommandRouter()
    router.register(FakeCommand())

    class Ctx:
        pass

    ctx = Ctx()
    handled = await router.dispatch("/fake some args", ctx)
    assert handled is True
    assert ctx._executed is True
    assert ctx._args == "some args"


@pytest.mark.asyncio
async def test_dispatch_alias():
    router = CommandRouter()
    router.register(FakeCommand())

    class Ctx:
        pass

    ctx = Ctx()
    handled = await router.dispatch("/f hello", ctx)
    assert handled is True
    assert ctx._args == "hello"


@pytest.mark.asyncio
async def test_dispatch_unknown():
    router = CommandRouter()
    ctx = object()
    handled = await router.dispatch("/nope", ctx)
    assert handled is False


@pytest.mark.asyncio
async def test_dispatch_no_args():
    router = CommandRouter()
    router.register(FakeCommand())

    class Ctx:
        pass

    ctx = Ctx()
    handled = await router.dispatch("/fake", ctx)
    assert handled is True
    assert ctx._args == ""
